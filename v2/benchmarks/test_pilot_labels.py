import json
import pathlib
import tempfile
import unittest
import wave
from array import array

from pilot_labels import check_labels, make_template


class PilotLabelTests(unittest.TestCase):
    def make_manifest(self, root: pathlib.Path):
        wav = root / "ptp.wav"
        with wave.open(str(wav), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(array("h", [800] * 16000).tobytes())
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps([
            {"id": "szafa@001", "audio": "ptp.wav", "reference": "szafa"}
        ]), encoding="utf-8")
        return manifest

    def completed(self, row):
        return dict(row, heard_without_reference="szafa", intelligible=True,
                    target_correct=True, capture_quality="clear",
                    sound_error_tags=[], stress_correct=None, reviewer_notes="")

    def test_starts_ungraded_and_accepts_complete_review(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.make_manifest(pathlib.Path(temp))
            row = make_template(manifest)[0]
            self.assertIsNone(row["intelligible"])
            self.assertIsNone(row["sound_error_tags"])
            with self.assertRaisesRegex(ValueError, "flags required"):
                check_labels(manifest, [row])
            counts = check_labels(manifest, [self.completed(row)])
            self.assertEqual(counts["clear"], 1)
            self.assertEqual(counts["intelligible"], 1)
            self.assertEqual(counts["marked_sound_errors"], 0)

    def test_fingerprint_enforces_identical_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.make_manifest(pathlib.Path(temp))
            row = self.completed(make_template(manifest)[0])
            row["audio_sha256"] = "b" * 64
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                check_labels(manifest, [row])

    def test_rejects_unknown_tags_and_non_boolean_ratings(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.make_manifest(pathlib.Path(temp))
            row = self.completed(make_template(manifest)[0])
            row["sound_error_tags"] = ["unknown"]
            with self.assertRaisesRegex(ValueError, "Sound-error"):
                check_labels(manifest, [row])
            row["sound_error_tags"] = ["sz_vs_ś"]
            row["intelligible"] = 1
            with self.assertRaisesRegex(ValueError, "flags required"):
                check_labels(manifest, [row])
            row["intelligible"] = True
            row["capture_quality"] = "clipped"
            counts = check_labels(manifest, [row])
            self.assertEqual(counts["flagged_capture"], 1)
            self.assertEqual(counts["marked_sound_errors"], 1)

    def test_requires_known_identifiers_once(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.make_manifest(pathlib.Path(temp))
            row = self.completed(make_template(manifest)[0])
            with self.assertRaisesRegex(ValueError, "exactly one"):
                check_labels(manifest, [row, row])
            row["id"] = "unregistered"
            with self.assertRaisesRegex(ValueError, "Unknown"):
                check_labels(manifest, [row])


if __name__ == "__main__":
    unittest.main()
