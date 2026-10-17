"""Offline acoustic level and human microphone-quality review unit tests."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array

from benchmark import read_audio_metadata
from audio_quality_review import inspect_manifest, measure_wav, review_recordings, save_review


class AudioQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.rows = []
        for i, peak in enumerate((30, 4000, 32767)):
            p = self.root / f"clip-{i}.wav"
            with wave.open(str(p), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(array("h", [peak] * 16000).tobytes())
            meta = read_audio_metadata(p)
            self.rows.append({"id": f"native-{i}", "audio": p.name,
                              "audio_sha256": meta["audio_sha256"],
                              "reference_verified_by_human": False,
                              "provider_upload_approved": False})
        self.manifest = self.root / "sentences-source.json"
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.rows))

    def tearDown(self):
        self.tmp.cleanup()

    def test_level_flags_are_acoustic_not_language_judgements(self):
        quiet = measure_wav(self.root / "clip-0.wav")
        normal = measure_wav(self.root / "clip-1.wav")
        clipped = measure_wav(self.root / "clip-2.wav")
        self.assertIn("low_signal_level", quiet["flags"])
        self.assertNotIn("low_signal_level", normal["flags"])
        self.assertIn("possible_clipping", clipped["flags"])
        self.assertEqual(clipped["clipped_sample_percent"], 100.0)
        self.assertAlmostEqual(normal["duration_seconds"], 1.0, places=3)
        self.assertEqual(measure_wav(self.root / "clip-1.wav")["rms_dbfs"],
                         normal["rms_dbfs"])

    def test_review_flags_do_not_enable_native_certification_or_provider_upload(self):
        findings = inspect_manifest(self.manifest)
        self.assertTrue(all(x["native_pronunciation_verified"] is False for x in findings))
        self.assertTrue(all(x["provider_upload_approved"] is False for x in findings))
        replies = iter(("q", "c", "d"))
        played = []
        review_recordings(findings, self.root, reader=lambda _: next(replies),
                          player=lambda p: played.append(p.name))
        self.assertEqual([i["human_audio_quality"] for i in findings],
                         ["too_quiet", "clear", "noisy_or_distorted"])
        self.assertEqual(played, [f"clip-{i}.wav" for i in range(3)])
        result = self.root / "audio-quality-01.json"
        save_review(findings, result)
        report = json.loads(result.read_text())
        self.assertTrue(report["does_not_certify_native_polish"])
        self.assertTrue(report["does_not_approve_provider_upload"])
        self.assertEqual(result.stat().st_mode & 0o777, 0o600)
        self.assertTrue(all(x["native_pronunciation_verified"] is False for x in report["recordings"]))
        self.assertTrue(all(x["provider_upload_approved"] is False for x in report["recordings"]))
        self.assertFalse(any("human_audio_quality" in item for item in json.loads(self.manifest.read_text())))
        with self.assertRaisesRegex(ValueError, "fresh"):
            save_review(findings, result)

    def test_manifest_checksum_tamper_rejected(self):
        self.rows[0]["audio_sha256"] = "f" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "Checksum"):
            inspect_manifest(self.manifest)

    def test_wav_symlink_rejected(self):
        alias = self.root / "alias.wav"
        alias.symlink_to(self.root / "clip-1.wav")
        self.rows[0]["audio"] = "alias.wav"
        self.rows[0]["audio_sha256"] = self.rows[1]["audio_sha256"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Missing or symlinked"):
            inspect_manifest(self.manifest)

    def test_requires_private_root(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "chmod 700"):
            inspect_manifest(self.manifest)


if __name__ == "__main__":
    unittest.main()
