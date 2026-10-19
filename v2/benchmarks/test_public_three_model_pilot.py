"""Offline six-call public-native comparison tests. Never download, call Groq or Azure."""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from benchmark import read_audio_metadata
from public_polish_audio import SOURCES
from public_three_model_pilot import checked_public_clips, execute, preview, summarize, azure_only, azure_evidence


class PublicThreeModelPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.folder.chmod(0o700)
        clips = []
        for index, source in enumerate(SOURCES):
            ogg_name = source["id"] + ".ogg"
            wav_name = source["id"] + ".wav"
            (self.folder / ogg_name).write_bytes(b"OggS" + b"x" * 1800)
            audio = self.folder / wav_name
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(array("h", [round(4500 * math.sin(i * .14))
                                              for i in range(16000 + index * 8000)]).tobytes())
            meta = read_audio_metadata(audio)
            clips.append({
                "id": source["id"], "text": source["text"],
                "original": ogg_name, "wav": wav_name,
                "source_url": source["description"], "author": source["author"],
                "license": "Public domain",
                "original_sha256": source["original_sha256"],
                "wav_sha256": meta["audio_sha256"],
                "seconds": round(meta["seconds"], 3),
            })
        (self.folder / "manifest.json").write_text(json.dumps({
            "status": "public_reference_audio_only", "clips": clips,
        }))
        self.calls = []
        self.patched = patch("public_three_model_pilot.validate_ogg",
                             side_effect=[s["original_sha256"] for s in SOURCES] * 20)
        self.patched.start()

    def tearDown(self):
        self.patched.stop()
        self.tmp.cleanup()

    def params(self, output):
        def whisper(audio, model, key):
            self.calls.append((audio, model, key))
            return "Dzień dobry" if model == "whisper-large-v3" else "Dzień"
        def azure(audio, reference, key, region):
            self.calls.append((audio, "azure", key))
            self.assertEqual(region, "germanywestcentral")
            return {"status":"ok", "raw_azure_json":{
                "NBest":[{"PronunciationAssessment":{
                    "AccuracyScore":92,"FluencyScore":85,"CompletenessScore":95}}]}}
        return dict(send=True, approve_public_audio_upload=True,
                    confirm_groq_free=True, confirm_azure_f0=True,
                    confirm_no_paid_billing=True,
                    groq_key="FAKE-GROQ", azure_key="FAKE-AZURE",
                    azure_region="germanywestcentral", output=output,
                    transcriber=whisper, assessor=azure)

    def test_preview_exactly_six_calls_no_network(self):
        report = execute(self.folder)
        self.assertEqual(report["status"], "PREVIEW_ONLY")
        self.assertEqual(report["planned_calls"], 6)
        self.assertEqual(report["groq_minimum_billable_audio_seconds_if_charged"], 40)
        self.assertEqual(len(report["clips"]), 2)
        self.assertEqual(report["network_calls_performed"], 0)
        self.assertEqual(self.calls, [])

    def test_two_distinct_pinned_public_wavs_are_identical_per_provider(self):
        output = self.folder / "results-01.jsonl"
        actual = execute(self.folder, **self.params(output))
        self.assertEqual(actual["network_calls_performed"], 6)
        self.assertEqual(len(self.calls), 6)
        rows = [json.loads(x) for x in output.read_text().splitlines()]
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["engine"] for r in rows[0:3]],[
            "groq-whisper-large-v3", "groq-whisper-large-v3-turbo",
            "azure-pl-PL-scripted",
        ])
        for idx in [0,3]:
            one = rows[idx:idx+3]
            self.assertEqual(len({r["audio_sha256"] for r in one}),1)
            self.assertEqual(len({r["reference"] for r in one}),1)
            self.assertTrue(all(r["latency_ms"] >= 0 for r in one))
            self.assertIsNone(one[0]["pronunciation_grade"])
            self.assertIsNone(one[1]["pronunciation_grade"])
            self.assertEqual(one[2]["azure_native"]["scores"]["AccuracyScore"],92)
        self.assertEqual(output.stat().st_mode & 0o777,0o600)
        self.assertEqual(actual["report"]["fit"]["complete_three_engine_triplets"],2)
        self.assertEqual(actual["report"]["fit"]["distinct_audio_samples"],2)
        self.assertEqual(actual["report"]["fit"]["independent_human_labels"],0)
        self.assertEqual(actual["report"]["fit"]["status"],
                         "insufficient_evidence_for_final_model_selection")
        self.assertEqual(len(summarize(output)["evidence"]),6)
        self.assertNotIn("FAKE-AZURE",output.read_text())
        with self.assertRaisesRegex(ValueError, "Output exists"):
            execute(self.folder, **self.params(output))
        self.assertEqual(len(self.calls),6)

    def test_no_audio_uploaded_when_free_tier_or_permission_not_confirmed(self):
        for key, bad in [
            ("approve_public_audio_upload", False),
            ("confirm_groq_free", False), ("confirm_azure_f0", False),
            ("confirm_no_paid_billing", False), ("groq_key", ""),
            ("azure_key", ""), ("azure_region", "westus"),
            ("azure_key", "not-a-key\u2026"),
        ]:
            output=self.folder/"not-created.jsonl"
            kwargs=self.params(output)
            kwargs[key]=bad
            with self.assertRaises(ValueError):
                execute(self.folder, **kwargs)
            self.assertFalse(output.exists())
        self.assertEqual(self.calls, [])

    def test_wrong_reference_or_wav_sha_rejected_without_provider_contact(self):
        p=self.folder/"manifest.json"
        original=json.loads(p.read_text())
        for field,value in [("text","Wrong Polish"),("wav_sha256","a"*64),
                            ("license","Not confirmed")]:
            edited=json.loads(json.dumps(original))
            edited["clips"][0][field]=value
            p.write_text(json.dumps(edited))
            with self.assertRaisesRegex(ValueError, "changed"):
                checked_public_clips(self.folder)
        p.write_text(json.dumps(original))
        self.assertEqual(self.calls, [])

    def test_partial_success_saved_on_failed_second_transcription(self):
        output=self.folder/"partial.jsonl"
        kwargs=self.params(output)
        attempts=0
        def failed_second(audio,model,key):
            nonlocal attempts
            attempts+=1
            if attempts==2: raise RuntimeError("Mock provider error, no retry")
            return "Dzień dobry"
        kwargs["transcriber"]=failed_second
        with self.assertRaisesRegex(RuntimeError, "no retry"):
            execute(self.folder,**kwargs)
        self.assertEqual(attempts,2)
        rows=[json.loads(x) for x in output.read_text().splitlines()]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["engine"],"groq-whisper-large-v3")
        self.assertEqual(self.calls,[])


    def test_existing_file_preserves_its_unknown_azure_cancellation_cause(self):
        legacy = self.folder / "legacy-recording.jsonl"
        row = {
            "sample_id": "greeting-day", "reference": "Dzień dobry",
            "audio_sha256": "a" * 64, "engine": "azure-pl-PL-scripted",
            "status": "inconclusive",
            "azure_native": {"status": "inconclusive", "reason": "Azure canceled speech recognition"},
            "latency_ms": 1328.3,
        }
        legacy.write_text(json.dumps(row) + "\n")
        shown = summarize(legacy)["evidence"][0]
        self.assertEqual(shown["reason"], "Azure canceled speech recognition")
        self.assertIsNone(shown["azure_diagnostic"])
        self.assertIsNone(shown["azure_scores_uncalibrated"])

    def test_azure_only_preview_zero_requests_and_refuses_wrong_clip(self):
        report = azure_only(self.folder, "greeting-day")
        self.assertEqual(report["planned_azure_calls"], 1)
        self.assertEqual(report["planned_groq_calls"], 0)
        self.assertEqual(report["network_calls_performed"], 0)
        self.assertEqual(report["status"], "AZURE_ONLY_PREVIEW")
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(ValueError, "sample-id"):
            azure_only(self.folder, "not-a-greeting")

    def test_azure_only_one_call_returns_safe_sdk_diagnostics_with_no_groq_key(self):
        calls = []
        def assessor(audio, reference, key, region):
            calls.append((audio, reference, region))
            return {
                "status": "inconclusive", "reason": "Azure canceled speech recognition",
                "azure_result_reason": "Canceled",
                "azure_cancellation_reason": "Error",
                "azure_error_code": "ServiceTimeout",
                "error_details": "provider-private-error-message-MUST-NOT-LEAK",
            }
        path = self.folder / "azure-only-01.jsonl"
        result = azure_only(self.folder, "greeting-day", send=True,
                            approve_public_audio_upload=True, confirm_azure_f0=True,
                            confirm_no_paid_billing=True, azure_key="TEST-ONLY",
                            azure_region="germanywestcentral", output=path, assessor=assessor)
        self.assertEqual(result["network_calls_performed"], 1)
        self.assertEqual(result["groq_calls"], 0)
        self.assertEqual(calls, [(self.folder/"greeting-day.wav", "Dzień dobry", "germanywestcentral")])
        self.assertEqual(result["azure_diagnostic"], {
            "azure_result_reason": "Canceled", "azure_cancellation_reason": "Error",
            "azure_error_code": "ServiceTimeout",
        })
        shown = summarize(path)["evidence"][0]
        self.assertEqual(shown["azure_diagnostic"]["azure_error_code"], "ServiceTimeout")
        self.assertIsNone(shown["azure_scores_uncalibrated"])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("provider-private-error-message",path.read_text())
        with self.assertRaisesRegex(ValueError, "Output exists"):
            azure_only(self.folder, "greeting-day", send=True,
                       approve_public_audio_upload=True, confirm_azure_f0=True,
                       confirm_no_paid_billing=True, azure_key="TEST-ONLY",
                       azure_region="germanywestcentral", output=path, assessor=assessor)
        self.assertEqual(len(calls), 1)

    def test_azure_only_refuses_upload_without_approval_and_bad_credentials(self):
        for change in [
            {"approve_public_audio_upload": False},
            {"confirm_azure_f0": False},
            {"confirm_no_paid_billing": False},
            {"azure_key": ""},
            {"azure_key": "TEST-ONLY\u2026"},
            {"azure_region": "wrong-region"},
        ]:
            kwargs = {
                "send": True, "approve_public_audio_upload": True,
                "confirm_azure_f0": True, "confirm_no_paid_billing": True,
                "azure_key": "TEST-ONLY", "azure_region": "germanywestcentral",
                "output": self.folder / "forbidden.jsonl",
                "assessor": lambda *_: self.fail("Azure must NOT be contacted"),
            }
            kwargs.update(change)
            with self.assertRaises(ValueError):
                azure_only(self.folder, "greeting-day", **kwargs)
            self.assertFalse(kwargs["output"].exists())

    def test_bad_sdk_free_text_is_not_serialized_or_displayed(self):
        c={"id":"greeting-day","reference":"Dzień dobry","sha256":"f"*64}
        row=azure_evidence(c, {
            "status":"inconclusive", "reason":"PRIVATE SERVICE STRING",
            "azure_result_reason":"Canceled", "azure_cancellation_reason":"PRIVATE ERROR",
            "azure_error_code":"KEY123INPRIVATEERROR", "error_details":"DO-NOT-COPY",
        },123.4)
        self.assertEqual(row["azure_diagnostic"], {
            "azure_result_reason": "Canceled",
            "azure_cancellation_reason": "Unknown",
            "azure_error_code": "Unknown",
        })
        self.assertEqual(row["azure_native"]["reason"], "Azure result inconclusive")
        self.assertNotIn("PRIVATE",json.dumps(row))
        self.assertNotIn("DO-NOT-COPY",json.dumps(row))

    def test_six_call_runner_now_preserves_cancel_categories(self):
        output=self.folder/"native-six-diagnostic.jsonl"
        args=self.params(output)
        def assessor(*_):
            return {"status":"inconclusive", "reason":"Azure canceled speech recognition",
                    "azure_result_reason":"Canceled", "azure_cancellation_reason":"Error",
                    "azure_error_code":"AuthenticationFailure"}
        args["assessor"]=assessor
        done=execute(self.folder,**args)
        self.assertEqual(done["network_calls_performed"],6)
        rows=[json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual(rows[2]["azure_diagnostic"]["azure_error_code"],"AuthenticationFailure")
        self.assertEqual(rows[5]["azure_diagnostic"]["azure_cancellation_reason"],"Error")
        self.assertEqual(done["report"]["evidence"][2]["azure_diagnostic"]["azure_result_reason"],"Canceled")
        self.assertEqual(done["report"]["fit"]["model_results"]["azure-pl-PL-scripted"]["inconclusive_results"],2)
        self.assertEqual(done["report"]["fit"]["complete_three_engine_triplets"],2)


if __name__ == "__main__":
    unittest.main()
