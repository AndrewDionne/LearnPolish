"""Azure F0 research gates and raw evidence, all mocked and offline."""
import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array

from azure_pilot import run, checked_recording
from benchmark import read_audio_metadata


class AzurePilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.wav = self.root / "sentence-01-original.wav"
        with wave.open(str(self.wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(array("h", [800] * (16000 * 5)).tobytes())
        meta = read_audio_metadata(self.wav)
        self.row = {
            "id": "sentence-01", "audio": self.wav.name,
            "reference": "To jest sprawdzona polska wypowiedź.",
            "speaker_role": "adult_learner",
            "speaker_id": "anonymous-adult",
            "adult_consent_confirmed": True,
            "reference_verified_by_human": True,
            "audio_audited_unclipped": True,
            "provider_upload_approved": True,
            "speed_factor": 1.0,
            "artificially_stretched": False,
            "audio_sha256": meta["audio_sha256"],
            "original_sha256": meta["audio_sha256"],
        }
        self.manifest = self.root / "manifest.json"
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.manifest.write_text(json.dumps([self.row], ensure_ascii=False))

    def test_default_preview_no_credentials_no_import_no_request(self):
        def unexpected(*_):
            raise AssertionError("Preview cannot send to Azure")
        result = run(self.manifest, "sentence-01", assessor=unexpected)
        self.assertEqual(result["planned_requests"], 1)
        self.assertEqual(result["network_requests_performed"], 0)
        self.assertFalse(result["voice_uploaded"])
        self.assertEqual(result["locale"], "pl-PL")
        self.assertFalse((self.root / "private.json").exists())

    def test_one_explicit_consent_checked_request_preserves_raw_response(self):
        observed = []
        def fake(audio, reference, key, region):
            observed.append((audio, reference, key, region))
            return {"status": "ok", "raw_azure_json": {
                "NBest": [{"PronunciationAssessment": {
                    "AccuracyScore": 77, "FluencyScore": 60}}]
            }}
        output = self.root / "azure-raw.json"
        result = run(self.manifest, "sentence-01", send=True,
                     approve_voice_upload=True, confirm_resource_f0=True,
                     confirm_no_paid_billing=True, output=output, key="PRIVATE-KEY",
                     region="westeurope", assessor=fake)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][0], self.wav)
        self.assertEqual(observed[0][2], "PRIVATE-KEY")
        self.assertEqual(result["network_requests_performed"], 1)
        self.assertTrue(result["voice_uploaded"])
        raw = json.loads(output.read_text())
        self.assertEqual(raw["raw_azure_json"]["NBest"][0]["PronunciationAssessment"]["AccuracyScore"], 77)
        self.assertFalse(raw["assessment_is_human_calibrated"])
        self.assertNotIn("PRIVATE-KEY", output.read_text())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(ValueError, "NEW"):
            run(self.manifest, "sentence-01", send=True,
                approve_voice_upload=True, confirm_resource_f0=True,
                confirm_no_paid_billing=True, output=output, key="x", region="westeurope",
                assessor=fake)
        self.assertEqual(len(observed), 1)

    def test_disallows_unverified_free_tier_and_voice_permission(self):
        output = self.root / "unused.json"
        calls = []
        def fake(*args):
            calls.append(args)
        with self.assertRaisesRegex(ValueError, "Live Azure needs"):
            run(self.manifest, "sentence-01", send=True, output=output,
                key="x", region="westeurope", assessor=fake)
        self.assertEqual(calls, [])
        self.assertFalse(output.exists())

    def test_disallows_time_stretched_audio_for_pronunciation(self):
        self.row["artificially_stretched"] = True
        self.row["speed_factor"] = 0.85
        self.save()
        with self.assertRaisesRegex(ValueError, "original 1.0x"):
            checked_recording(self.manifest, "sentence-01")

    def test_rejects_missing_human_and_provider_approval(self):
        self.row["reference_verified_by_human"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "Human"):
            checked_recording(self.manifest, "sentence-01")
        self.row["reference_verified_by_human"] = True
        self.row["provider_upload_approved"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "provider upload"):
            checked_recording(self.manifest, "sentence-01")
        self.row["provider_upload_approved"] = True
        self.row["adult_consent_confirmed"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "consent"):
            checked_recording(self.manifest, "sentence-01")

    def test_rejects_changed_hash_and_over_budget_or_multiple_requests(self):
        self.row["audio_sha256"] = "a" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "Audio changed"):
            checked_recording(self.manifest, "sentence-01")
        self.row["audio_sha256"] = self.row["original_sha256"]
        self.save()
        with self.assertRaisesRegex(ValueError, "EXACTLY one"):
            run(self.manifest, "sentence-01", max_requests=2)
        with self.assertRaisesRegex(ValueError, "hard cap"):
            run(self.manifest, "sentence-01", max_audio_seconds=5.0 - 0.01)

    def test_rejects_wrong_sample_id_and_source_path_escape(self):
        with self.assertRaisesRegex(ValueError, "Exactly one"):
            checked_recording(self.manifest, "unlisted")
        self.row["audio"] = "../other.wav"
        self.save()
        with self.assertRaisesRegex(ValueError, "local manifest-relative"):
            checked_recording(self.manifest, "sentence-01")

    def test_failed_first_provider_request_cleans_new_empty_file(self):
        output = self.root / "failed-azure.json"
        def blocked(*_):
            raise RuntimeError("SDK failed (sanitized)")
        with self.assertRaisesRegex(RuntimeError, "SDK failed"):
            run(self.manifest, "sentence-01", send=True,
                approve_voice_upload=True, confirm_resource_f0=True,
                confirm_no_paid_billing=True, output=output,
                key="x", region="westeurope", assessor=blocked)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
