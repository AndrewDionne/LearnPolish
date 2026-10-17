"""No-network three-model Polish preliminary pilot: safety, consistency, WER."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array
from benchmark import read_audio_metadata
from three_model_pilot import run, preview, word_error_rate, summarize


class ThreeModelPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.folder.chmod(0o700)
        rows = []
        for ix, volume in [(1, 4000), (2, 5000), (3, 10)]:
            sid = f"fleurs-pl-val-{ix:05d}"
            path = self.folder / (sid + ".wav")
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(array("h", [volume] * 16000 * 6).tobytes())
            meta = read_audio_metadata(path)
            rows.append({
                "id": sid, "audio": path.name,
                "reference": "Ten polski przykład mówi więcej niż jedno słowo.",
                "audio_sha256": meta["audio_sha256"],
                "source_dataset": "google/fleurs", "source_config": "pl_pl",
                "source_split": "validation",
                "source_license": "CC BY 4.0 — Google FLEURS (confirm third-party service use before upload)",
                "provider_upload_approved": False,
                "reference_verified_by_human": False,
                "audio_audited_unclipped": False,
            })
        self.manifest = self.folder / "sentences-source.json"
        self.manifest.write_text(json.dumps(rows))
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def fake_groq(self, audio, model, key):
        self.assertEqual(key, "PRIVATE-GROQ-KEY")
        self.calls.append((audio.name, model))
        if model == "whisper-large-v3":
            return "Ten polski przykład mówi więcej niż jedno słowo."
        return "Ten polski przykład mówi mniej niż jedno słowo."

    def fake_azure(self, audio, reference, key, region):
        self.assertEqual(key, "PRIVATE-AZURE-KEY")
        self.assertEqual(region, "germanywestcentral")
        self.calls.append((audio.name, "azure"))
        return {"status": "ok", "raw_azure_json": {
            "DisplayText": reference,
            "NBest": [{
                "Lexical": reference,
                "PronunciationAssessment": {"AccuracyScore": 89.0, "FluencyScore": 92.0,
                                            "CompletenessScore": 100.0},
                "Words": [{"Word": "Ten", "PronunciationAssessment": {"AccuracyScore": 88}}]
            }]
        }}

    def live_kwargs(self, output):
        return dict(send=True, approve_public_audio_upload=True,
                    confirm_groq_free=True, confirm_azure_f0=True,
                    confirm_no_paid_billing=True, groq_key="PRIVATE-GROQ-KEY",
                    azure_key="PRIVATE-AZURE-KEY", azure_region="germanywestcentral",
                    transcriber=self.fake_groq, assessor=self.fake_azure,
                    output=output)

    def test_preview_uses_best_two_unverified_audio_without_contacting_provider(self):
        clips, preview_report = preview(self.manifest)
        self.assertEqual(len(clips), 2)
        self.assertTrue(all("00003" not in c["id"] for c in clips))
        self.assertEqual(preview_report["planned_calls"], 6)
        self.assertEqual(preview_report["planned_groq_billed_seconds"], 40)
        self.assertEqual(preview_report["planned_azure_audio_seconds"], 12)
        self.assertFalse(preview_report["source_human_verified"])
        self.assertEqual(self.calls, [])
        self.assertFalse((self.folder / "exploratory.jsonl").exists())

    def test_triplet_two_clips_same_hash_and_full_raw_azure(self):
        output = self.folder / "exploratory.jsonl"
        result = run(self.manifest, **self.live_kwargs(output))
        self.assertEqual(result["status"], "EXPLORATORY_COMPLETE")
        self.assertEqual(result["network_calls_performed"], 6)
        self.assertEqual(len(self.calls), 6)
        self.assertEqual([m for _, m in self.calls],
                         ["whisper-large-v3", "whisper-large-v3-turbo", "azure"] * 2)
        rows = [json.loads(x) for x in output.read_text().splitlines()]
        self.assertEqual(len(rows), 6)
        for i in (0, 3):
            self.assertEqual(len({r["audio_sha256"] for r in rows[i:i+3]}), 1)
            self.assertEqual(rows[i]["wer"], 0)
            self.assertGreater(rows[i+1]["wer"], 0)
            self.assertIsNone(rows[i]["pronunciation_grade"])
            self.assertFalse(rows[i]["native_speech_human_verified"])
            self.assertFalse(rows[i+2]["native_speech_human_verified"])
            self.assertEqual(rows[i+2]["raw_azure_json"]["NBest"][0]
                             ["PronunciationAssessment"]["AccuracyScore"], 89.0)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        summary = summarize(output)
        self.assertEqual(summary["completed_model_rows"], 6)
        self.assertEqual(summary["comparison"][2]["azure_scores_uncalibrated"]["AccuracyScore"], 89.0)
        self.assertNotIn("PRIVATE-GROQ-KEY", output.read_text())
        self.assertNotIn("PRIVATE-AZURE-KEY", output.read_text())
        with self.assertRaisesRegex(ValueError, "Output exists"):
            run(self.manifest, **self.live_kwargs(output))

    def test_flags_credentials_sdk_and_budget_gate_before_any_network(self):
        file = self.folder / "blocked.jsonl"
        cases = [
            {"approve_public_audio_upload": False},
            {"confirm_groq_free": False},
            {"confirm_azure_f0": False},
            {"confirm_no_paid_billing": False},
            {"groq_key": ""},
            {"azure_key": ""},
            {"azure_region": "canadaeast"},
        ]
        for change in cases:
            kwargs = self.live_kwargs(file)
            kwargs.update(change)
            with self.assertRaises(ValueError):
                run(self.manifest, **kwargs)
        with self.assertRaisesRegex(ValueError, "budgets"):
            run(self.manifest, max_requests=5)
        with self.assertRaisesRegex(ValueError, "budgets"):
            run(self.manifest, max_groq_billed_seconds=20)
        with self.assertRaisesRegex(ValueError, "budgets"):
            run(self.manifest, max_azure_audio_seconds=5)
        self.assertEqual(self.calls, [])
        self.assertFalse(file.exists())

    def test_single_clip_with_ids_and_stop_on_partial_failure(self):
        output = self.folder / "partial.jsonl"
        kwargs = self.live_kwargs(output)
        calls = []
        def fail_on_second(audio, model, key):
            calls.append(model)
            if len(calls) == 2:
                raise RuntimeError("Groq HTTP 403 without secret")
            return "Ten polski przykład mówi więcej niż jedno słowo."
        kwargs["transcriber"] = fail_on_second
        with self.assertRaisesRegex(RuntimeError, "403"):
            run(self.manifest, **kwargs)
        rows = [json.loads(x) for x in output.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(calls), 2)
        self.assertIn("00001", rows[0]["sample_id"])
        # Other sample and Azure never called; partial JSONL safe to inspect.
        self.assertEqual(self.calls, [])
        new = self.folder / "single.jsonl"
        kwargs = self.live_kwargs(new)
        outcome = run(self.manifest, count=1, sample_ids=("fleurs-pl-val-00002",),
                      max_requests=3, max_groq_billed_seconds=20,
                      max_azure_audio_seconds=10, **kwargs)
        self.assertEqual(outcome["network_calls_performed"], 3)
        self.assertEqual(len(new.read_text().splitlines()), 3)

    def test_rejects_audio_sha_changes_nonpublic_dataset_and_bad_sample_ids(self):
        rows = json.loads(self.manifest.read_text())
        rows[0]["audio_sha256"] = "f" * 64
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "changed"):
            preview(self.manifest)
        rows[0]["audio_sha256"] = read_audio_metadata(self.folder / rows[0]["audio"])["audio_sha256"]
        rows[0]["source_dataset"] = "private-recording"
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "ONLY"):
            preview(self.manifest)
        rows[0]["source_dataset"] = "google/fleurs"
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "exactly"):
            preview(self.manifest, sample_ids=("fleurs-pl-val-00001", "fleurs-pl-val-99999"))
        with self.assertRaisesRegex(ValueError, "ONE or TWO"):
            preview(self.manifest, count=3)

    def test_word_error_rate_never_equates_transcript_with_pronunciation(self):
        self.assertEqual(word_error_rate("Dzień dobry!", "Dzień dobry"), 0)
        self.assertEqual(word_error_rate("Dzień dobry", "Dobry dzień"), 1)
        self.assertEqual(word_error_rate("Cześć", ""), 1)


if __name__ == "__main__":
    unittest.main()
