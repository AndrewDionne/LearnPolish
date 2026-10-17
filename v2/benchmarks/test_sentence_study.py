"""Offline quality, tempo invariants, provenance and no-move tests."""
import json
import pathlib
import tempfile
import unittest
import wave
from array import array

from benchmark import read_audio_metadata
from sentence_study import validate_source, prepare


class SentenceStudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.root.chmod(0o700)
        self.rows = []
        for i in range(8):
            path = self.root / f"sample-{i}.wav"
            with wave.open(str(path), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(array("h", [900] * (16000 * 5)).tobytes())
            self.rows.append({
                "id": f"sentence-{i:02d}", "audio": path.name,
                "reference": "To jest sprawdzona polska wypowiedź.",
                "speaker_id": "adult-A" if i < 4 else "adult-B",
                "speaker_role": "native_control",
                "speaking_style": "natural_normal",
                "source_page": "local-consented:verified-native",
                "source_license": "documented adult permission",
                "reference_verified_by_human": True,
                "audio_audited_unclipped": True,
                "provider_upload_approved": False,
            })
        self.manifest = self.root / "source.json"
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.manifest.write_text(json.dumps(self.rows, ensure_ascii=False))

    def converter(self, source, output, speed):
        metadata = read_audio_metadata(source)
        with wave.open(str(output), "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(16000)
            file.writeframes(array("h", [900] * round(metadata["seconds"] * 16000 / speed)).tobytes())

    def test_verified_8_sentences_generate_locked_original_and_tempo_without_source_moves(self):
        output = self.root / "prepared"
        result = prepare(self.manifest, output, speeds=(0.85, 0.75),
                         converter=self.converter)
        self.assertEqual(result["samples"], 8)
        self.assertEqual(result["speaker_count"], 2)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["source_files_moved"], 0)
        for row in self.rows:
            self.assertTrue((self.root / row["audio"]).exists())
        orig = json.loads((output / "manifest.json").read_text())
        slow = json.loads((output / "tempo-085-manifest.json").read_text())
        slower = json.loads((output / "tempo-075-manifest.json").read_text())
        self.assertEqual(len(orig), 8)
        self.assertTrue(all(not x["artificially_stretched"] for x in orig))
        self.assertTrue(all(x["speed_factor"] == 0.85 for x in slow))
        self.assertTrue(all(x["speed_factor"] == 0.75 for x in slower))
        self.assertEqual(orig[0]["audio_sha256"], slow[0]["original_sha256"])
        self.assertEqual(orig[0]["audio_sha256"], slower[0]["original_sha256"])
        self.assertTrue(all(s["audio_seconds"] > 5 for s in slow))
        self.assertTrue(all(not x["provider_upload_approved"] for x in orig))
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        self.assertEqual((output / "manifest.json").stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(ValueError, "non-existing"):
            prepare(self.manifest, output, converter=self.converter)

    def test_blocks_unverified_spoken_reference_and_clipped(self):
        self.rows[0]["reference_verified_by_human"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "Human transcript"):
            validate_source(self.manifest)
        self.rows[0]["reference_verified_by_human"] = True
        self.rows[0]["audio_audited_unclipped"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "unclipped"):
            validate_source(self.manifest)

    def test_blocks_single_speaker_and_missing_license(self):
        for row in self.rows:
            row["speaker_id"] = "all-one"
        self.save()
        with self.assertRaisesRegex(ValueError, "two speakers"):
            validate_source(self.manifest)
        self.rows[4]["speaker_id"] = "another"
        self.rows[0]["source_license"] = ""
        self.save()
        with self.assertRaisesRegex(ValueError, "license"):
            validate_source(self.manifest)

    def test_blocks_provider_approval_missing_and_reused_wav(self):
        self.rows[0].pop("provider_upload_approved")
        self.save()
        with self.assertRaisesRegex(ValueError, "provider_upload_approved"):
            validate_source(self.manifest)
        self.rows[0]["provider_upload_approved"] = False
        self.rows[1]["audio"] = self.rows[0]["audio"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate audio"):
            validate_source(self.manifest)

    def test_failed_conversion_does_not_create_partial_manifest_or_move_source(self):
        output = self.root / "bad-output"
        def fails(*args):
            raise OSError("ffmpeg died")
        with self.assertRaisesRegex(OSError, "ffmpeg died"):
            prepare(self.manifest, output, converter=fails)
        self.assertFalse(output.exists())
        self.assertTrue((self.root / "sample-0.wav").exists())
        self.assertEqual(list(self.root.glob(".ptp-sentence-stage-*")), [])

    def test_rejects_tempo_1_or_unreviewed_speeds(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            prepare(self.manifest, self.root / "new", speeds=(1.0,), converter=self.converter)
        with self.assertRaisesRegex(ValueError, "unique"):
            prepare(self.manifest, self.root / "new", speeds=(0.85, 0.85), converter=self.converter)

    def test_short_isolated_word_clip_cannot_pass_sentence_study(self):
        self.rows[0]["reference"] = "czapka"
        self.save()
        with self.assertRaisesRegex(ValueError, "at least four"):
            validate_source(self.manifest)


if __name__ == "__main__":
    unittest.main()
