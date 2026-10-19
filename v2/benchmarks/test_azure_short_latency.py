"""Azure short phrase timing harness: entirely offline, mocked provider only."""
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
from azure_short_latency import plan, report, run, SAMPLE_ORDER


def scored(accuracy=100):
    return {"status": "ok", "raw_azure_json": {"NBest": [{
        "Display": "DO-NOT-SAVE-RAW-TRANSCRIPT",
        "PronunciationAssessment": {
            "AccuracyScore": accuracy, "FluencyScore": 92, "CompletenessScore": 100,
        },
    }]}}


class AzureLatencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.folder.chmod(0o700)
        clips = []
        for index, source in enumerate(SOURCES):
            ogg = source["id"] + ".ogg"
            wav_name = source["id"] + ".wav"
            (self.folder / ogg).write_bytes(b"OggS" + b"x" * 1200)
            wav = self.folder / wav_name
            with wave.open(str(wav), "wb") as wavefile:
                wavefile.setnchannels(1)
                wavefile.setsampwidth(2)
                wavefile.setframerate(16000)
                wavefile.writeframes(array("h", [
                    round(4000 * math.sin(i * 0.17))
                    for i in range(16000 + index * 8000)
                ]).tobytes())
            info = read_audio_metadata(wav)
            clips.append({
                "id": source["id"], "text": source["text"],
                "original": ogg, "wav": wav_name,
                "source_url": source["description"],
                "author": source["author"], "license": "Public domain",
                "original_sha256": source["original_sha256"],
                "wav_sha256": info["audio_sha256"],
                "seconds": round(info["seconds"], 3),
            })
        (self.folder / "manifest.json").write_text(json.dumps({
            "status": "public_reference_audio_only", "clips": clips,
        }))
        self.patch_ogg = patch("public_three_model_pilot.validate_ogg",
                               side_effect=[s["original_sha256"] for s in SOURCES] * 30)
        self.patch_ogg.start()
        self.calls = []

    def tearDown(self):
        self.patch_ogg.stop()
        self.tmp.cleanup()

    def params(self, name="latency-new.jsonl"):
        def fake(audio, reference, key, region):
            self.calls.append((audio, reference, key, region))
            return scored()
        return dict(
            folder=self.folder, count=4, send=True,
            approve_public_audio_upload=True,
            confirm_azure_f0=True, confirm_no_paid_billing=True,
            output=self.folder / name, azure_key="TEST-AZURE-NOT-REAL",
            azure_region="germanywestcentral", assessor=fake,
        )

    def test_preview_defaults_to_four_and_zero_calls(self):
        expected = plan(self.folder)
        self.assertEqual(expected["planned_azure_requests"], 4)
        self.assertEqual(expected["planned_groq_requests"], 0)
        self.assertEqual(expected["network_requests_performed"], 0)
        self.assertEqual([x["sample_id"] for x in expected["request_order"]], list(SAMPLE_ORDER))
        self.assertEqual(expected["planned_azure_audio_seconds"], 5.0)
        self.assertEqual(self.calls, [])
        self.assertEqual(run(self.folder)["status"], "PREVIEW_ONLY")
        self.assertEqual(plan(self.folder, count=2)["planned_azure_requests"], 2)
        for n in (0, 1, 3, 5, 10, True):
            with self.assertRaises(ValueError):
                plan(self.folder, count=n)

    def test_four_mocked_measured_calls_report_slow_tail_no_p95(self):
        kw = self.params()
        times = iter([0.0, 1.25, 2.0, 22.4113, 23.0, 25.25, 26.0, 27.4])
        result = run(**kw, clock=lambda: next(times))
        self.assertEqual(result["status"], "AZURE_LATENCY_OBSERVED")
        self.assertEqual(result["network_requests_performed_in_file"], 4)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual([c[0].name for c in self.calls], [
            "greeting-day.wav", "greeting-evening.wav",
            "greeting-day.wav", "greeting-evening.wav",
        ])
        self.assertEqual([c[1] for c in self.calls],
                         ["Dzień dobry", "Dobry wieczór"] * 2)
        performance = result["performance"]
        self.assertEqual(performance["successful_scored_requests"], 4)
        self.assertEqual(performance["attempts_at_or_above_10000ms"], 1)
        self.assertEqual(performance["attempts_at_or_above_20000ms"], 1)
        self.assertEqual(performance["successful_scored_median_ms"], 1825.0)
        self.assertEqual(performance["successful_scored_max_ms"], 20411.3)
        self.assertFalse(performance["all_attempts_under_5000ms"])
        self.assertNotIn("p95", result["performance"])
        self.assertIn("p95", result["decision"])
        self.assertNotIn("DO-NOT-SAVE-RAW-TRANSCRIPT", kw["output"].read_text())
        self.assertNotIn("TEST-AZURE-NOT-REAL", kw["output"].read_text())
        self.assertEqual(kw["output"].stat().st_mode & 0o777, 0o600)
        self.assertEqual(report(self.folder, kw["output"]), result)

    def test_two_inference_requests_only_and_output_must_be_new(self):
        kw = self.params()
        kw["count"] = 2
        result = run(**kw, clock=lambda: 1.0)
        self.assertEqual(result["network_requests_performed_in_file"], 2)
        self.assertEqual(len(self.calls), 2)
        with self.assertRaisesRegex(ValueError, "Output exists"):
            run(**kw)
        self.assertEqual(len(self.calls), 2)

    def test_inconclusive_and_recognized_but_unscored_are_failures_not_zero(self):
        kw = self.params()
        outcomes = [
            scored(),
            {"status":"inconclusive", "reason":"Azure returned NoMatch",
             "azure_result_reason":"NoMatch", "azure_no_match_reason":"NotRecognized"},
            {"status":"ok", "raw_azure_json":{"NBest":[{"Display":"not graded"}]}},
            scored(87),
        ]
        kw["assessor"] = lambda *args: outcomes.pop(0)
        result = run(**kw,clock=lambda: 1.0)
        self.assertEqual([x["status"] for x in result["observations"]],
                         ["ok","inconclusive","unscored","ok"])
        self.assertEqual(result["performance"]["successful_scored_requests"], 2)
        self.assertEqual(result["performance"]["unscored_or_inconclusive_or_failed"],2)
        self.assertIsNone(result["observations"][1]["raw_scores_uncalibrated"])
        self.assertEqual(result["observations"][1]["azure_diagnostic"]["azure_result_reason"],"NoMatch")
        self.assertEqual(result["observations"][3]["raw_scores_uncalibrated"]["AccuracyScore"],87)

    def test_sdk_exception_saved_safely_partial_without_automatic_retry(self):
        kw=self.params()
        calls=[]
        def fake(*params):
            calls.append(params)
            if len(calls)==2:
                raise RuntimeError("PASSWORD-OR-RAW-SDK-ERROR-NOT-FOR-LOG")
            return scored()
        kw["assessor"]=fake
        result=run(**kw,clock=lambda:1.0)
        self.assertEqual(len(calls),2)
        self.assertEqual(result["status"],"AZURE_LATENCY_PARTIAL")
        self.assertEqual(result["network_requests_performed_in_file"],2)
        self.assertEqual(result["observations"][-1]["status"],"error")
        self.assertNotIn("PASSWORD-OR-RAW",kw["output"].read_text())
        self.assertFalse(result["performance"]["all_attempts_under_5000ms"] is None)

    def test_no_provider_call_if_f0_rights_key_region_or_output_invalid(self):
        for key,bad in (
            ("approve_public_audio_upload",False),("confirm_azure_f0",False),
            ("confirm_no_paid_billing",False),("azure_key",""),
            ("azure_key","looks\u2026"),("azure_region","westus"),
            ("output",None),("count",6),
        ):
            kw=self.params()
            kw[key]=bad
            with self.assertRaises(ValueError):
                run(**kw)
            self.assertEqual(self.calls,[])
        self.assertFalse((self.folder/"latency-new.jsonl").exists())

    def test_review_detects_mismatched_fingerprint_and_private_permissions(self):
        kw=self.params()
        result=run(**kw,clock=lambda:1.0)
        self.assertEqual(result["network_requests_performed_in_file"],4)
        original=kw["output"].read_text()
        rows=[json.loads(line) for line in original.splitlines()]
        rows[0]["audio_sha256"]="a"*64
        kw["output"].write_text("\n".join(json.dumps(x) for x in rows)+"\n")
        with self.assertRaisesRegex(ValueError,"mismatched"):
            report(self.folder,kw["output"])
        kw["output"].write_text(original)
        kw["output"].chmod(0o644)
        with self.assertRaisesRegex(ValueError,"owner-private"):
            report(self.folder,kw["output"])
        self.assertEqual(len(self.calls),4)


if __name__ == "__main__":
    unittest.main()
