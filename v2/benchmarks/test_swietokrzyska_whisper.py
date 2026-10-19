"""Entirely offline mocked Whisper large-v3/Turbo reuse of the adult Azure evidence."""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave

from swietokrzyska_latency import WORD, ITEM_ID, checked_audio, clean_payload
from swietokrzyska_whisper import preview, run, report, safe_row
from groq_pilot import MODELS


class ŚwiętokrzyskaWhisperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.folder.chmod(0o700)
        self.wav = self.folder / "ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
        with wave.open(str(self.wav), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(array("h", [
                int(4200 * math.sin(i * .12)) for i in range(16000 * 3)
            ]).tobytes())
        self.baseline = self.folder / "azure-compare-01.jsonl"
        metadata = checked_audio(self.wav)
        rows = []
        for i, variant in enumerate(("ordinary", "preconnect"), 1):
            rows.append(clean_payload(variant, i, metadata, {
                "status": "ok", "timing_ms": {
                    "total": 2459.7 if i == 1 else 1923.3,
                    "preconnection": 0.0 if i == 1 else 423.9,
                    "recognition": 2457.4 if i == 1 else 1499.1,
                }, "scores": {
                    "AccuracyScore": 84.0, "FluencyScore": 100.0,
                    "CompletenessScore": 100.0,
                }, "connected_before_recognition": i == 2,
            }))
        self.baseline.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
        self.baseline.chmod(0o600)
        self.before = self.baseline.read_bytes()
        self.result_file = self.folder / "whisper-01.jsonl"
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def groq(self, wav, model, key):
        self.calls.append((wav, model, key))
        return WORD if model == MODELS[0] else "Świętokrzyski"

    def opts(self):
        return dict(send=True, approve_adult_audio_upload=True,
                    confirm_groq_free=True, confirm_no_paid_billing=True,
                    groq_key="PRIVATE-FAKE-GROQ-KEY",
                    output=self.result_file, transcriber=self.groq,
                    clock=lambda: 9.0)

    def test_preview_zero_network_and_existing_azure_baseline(self):
        planned = preview(self.wav, self.baseline)
        self.assertEqual(planned["planned_groq_requests"], 2)
        self.assertEqual(planned["planned_new_azure_requests"], 0)
        self.assertEqual(planned["network_requests_performed"], 0)
        self.assertEqual(planned["estimated_groq_billable_audio_seconds"], 20)
        self.assertEqual(planned["existing_azure_raw_scores_uncalibrated"][0]["scores"]["AccuracyScore"],84)
        self.assertEqual(planned["existing_azure_raw_scores_uncalibrated"][1]["total_sdk_ms"],1923.3)
        self.assertEqual(run(self.wav,self.baseline)["status"],"PREVIEW_ONLY")
        self.assertEqual(self.calls,[])
        self.assertFalse(self.result_file.exists())

    def test_two_groq_models_same_original_wav_no_azure_repeated(self):
        actual=run(self.wav,self.baseline,**self.opts())
        self.assertEqual(actual["status"],"WHISPER_PAIRED_RESULT")
        self.assertEqual(actual["new_azure_requests"],0)
        self.assertEqual(actual["groq_attempts_saved"],2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual([x[1] for x in self.calls],list(MODELS))
        self.assertEqual({x[0] for x in self.calls},{self.wav})
        self.assertEqual([x["exact_word_match"] for x in actual["whisper"]],[True,False])
        self.assertEqual([x["single_word_wer_transcription_only"] for x in actual["whisper"]],[0,1])
        self.assertEqual([x["pronunciation_grade"] for x in actual["whisper"]],[None,None])
        self.assertEqual(self.baseline.read_bytes(),self.before)
        self.assertEqual(self.result_file.stat().st_mode & 0o777,0o600)
        self.assertNotIn("PRIVATE-FAKE-GROQ-KEY",self.result_file.read_text())
        self.assertEqual(report(self.wav,self.baseline,self.result_file),actual)
        with self.assertRaisesRegex(ValueError,"Existing Groq result"):
            run(self.wav,self.baseline,**self.opts())
        self.assertEqual(len(self.calls),2)

    def test_no_upload_without_adult_approval_groq_free_or_key(self):
        for name,value in (
            ("approve_adult_audio_upload",False),("confirm_groq_free",False),
            ("confirm_no_paid_billing",False),("groq_key",""),
            ("groq_key","placeholder…"),("output",None),
        ):
            with self.subTest(case=name):
                options=self.opts()
                options[name]=value
                with self.assertRaises(ValueError):
                    run(self.wav,self.baseline,**options)
                self.assertFalse(self.result_file.exists())
                self.assertEqual(self.calls,[])

    def test_first_provider_error_is_persisted_sanitized_and_no_retry(self):
        calls=[]
        def failed(*args):
            calls.append(1)
            raise RuntimeError("PRIVATE KEY AND RAW PROVIDER RESPONSE")
        options=self.opts(); options["transcriber"]=failed
        result=run(self.wav,self.baseline,**options)
        self.assertEqual(result["status"],"WHISPER_PARTIAL")
        self.assertEqual(result["groq_attempts_saved"],1)
        self.assertEqual(result["whisper"][0]["status"],"error")
        self.assertIsNone(result["whisper"][0]["transcript"])
        self.assertEqual(len(calls),1)
        self.assertNotIn("PRIVATE",self.result_file.read_text())
        self.assertNotIn("RESPONSE",self.result_file.read_text())
        self.assertEqual(self.baseline.read_bytes(),self.before)

    def test_existing_result_or_mismatched_azure_baseline_blocks_before_groq(self):
        self.baseline.write_text(self.baseline.read_text().replace(WORD,"inny wyraz"))
        options=self.opts()
        with self.assertRaises(ValueError):
            run(self.wav,self.baseline,**options)
        self.assertEqual(self.calls,[])
        self.assertFalse(self.result_file.exists())

    def test_tampered_groq_jsonl_rejected_on_offline_review(self):
        run(self.wav,self.baseline,**self.opts())
        rows=[json.loads(x) for x in self.result_file.read_text().splitlines()]
        rows[0]["audio_sha256"]="a"*64
        self.result_file.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
        with self.assertRaisesRegex(ValueError,"Saved Whisper result differs"):
            report(self.wav,self.baseline,self.result_file)
        self.assertEqual(self.calls[0][0],self.wav)

    def test_failed_or_blank_transcript_is_not_assigned_a_grade(self):
        self.assertEqual(safe_row(MODELS[0],1,"a"*64,1250.0,"")["status"],"inconclusive")
        self.assertIsNone(safe_row(MODELS[0],1,"a"*64,1250.0,"")["single_word_wer_transcription_only"])
        with self.assertRaises(ValueError):
            safe_row(MODELS[0],1,"a"*64,float("nan"),WORD)
        with self.assertRaises(ValueError):
            safe_row("other-whisper",1,"a"*64,1500,WORD)


if __name__=="__main__":
    unittest.main()
