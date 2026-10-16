import json
import pathlib
import tempfile
import unittest
import wave
from array import array
from urllib.parse import quote

from corpus import prepare_corpus, parse_capture_name
from benchmark import run

STAMP = "20261016T194218123Z"


def write_wav(path: pathlib.Path, length=16000, amplitude=5000):
    pcm = array("h", (amplitude if i % 2 else -amplitude for i in range(length)))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(pcm.tobytes())


def make_catalog(root: pathlib.Path):
    catalog = root / "lessons.json"
    catalog.write_text(json.dumps({
        "schemaVersion": 1, "lessons": [
            {"id": "Conversation_1", "items": [
                {"id": "Conversation_1:0", "polish": "Dzień dobry"},
                {"id": "Conversation_1:1", "polish": "Dobry wieczór"},
            ]}
        ]
    }, ensure_ascii=False), encoding="utf-8")
    return catalog


def recording(root: pathlib.Path, item: str = "Conversation_1:0", stamp: str = STAMP,
              amplitude: int = 5000):
    p = root / ("ptp-speech-v1--" + quote(item, safe="") + "--" + stamp + ".wav")
    write_wav(p, amplitude=amplitude)
    return p


class ResearchCorpusTests(unittest.TestCase):
    def test_exact_reference_and_original_wav_fingerprint_run_offline(self):
        with tempfile.TemporaryDirectory() as location:
            root = pathlib.Path(location)
            reference = make_catalog(root)
            capture = recording(root)
            rows = prepare_corpus(root, reference)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["reference"], "Dzień dobry")
            self.assertEqual(rows[0]["audio"], capture.name)
            self.assertEqual(rows[0]["item_id"], "Conversation_1:0")
            self.assertEqual(rows[0]["captured_at_utc"], "2026-10-16T19:42:18.123Z")
            self.assertEqual(len(rows[0]["audio_sha256"]), 64)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(rows), encoding="utf-8")
            checks = run(manifest, "dry-run", None)
            self.assertEqual(checks[0]["status"], "ready")
            self.assertEqual(checks[0]["audio_sha256"], rows[0]["audio_sha256"])
            # An altered WAV cannot silently be paired with the old reference.
            write_wav(capture, amplitude=3800)
            with self.assertRaisesRegex(ValueError, "Recording bytes changed"):
                run(manifest, "dry-run", None)

    def test_unknown_items_and_malformed_ids_rejected(self):
        with tempfile.TemporaryDirectory() as location:
            root = pathlib.Path(location)
            reference = make_catalog(root)
            recording(root, item="Unknown_foo:1")
            with self.assertRaisesRegex(ValueError, "No exact Polish reference"):
                prepare_corpus(root, reference)
            self.assertRaisesRegex(ValueError, "versioned V2", parse_capture_name, "old.wav")
            self.assertRaisesRegex(ValueError, "encoded recording ID",
                                   parse_capture_name, "ptp-speech-v1--%2E%2E%2Ffoo--" + STAMP + ".wav")

    def test_dry_caps_quality_and_nonduplicated_bytes(self):
        with tempfile.TemporaryDirectory() as location:
            root = pathlib.Path(location)
            reference = make_catalog(root)
            recording(root, amplitude=4000)
            with self.assertRaisesRegex(ValueError, "Recording cap"):
                prepare_corpus(root, reference, max_recordings=0)
            with self.assertRaisesRegex(ValueError, "Audio time cap"):
                prepare_corpus(root, reference, max_seconds=0.5)
            recording(root, item="Conversation_1:1", amplitude=4000)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                prepare_corpus(root, reference)
            (root / ("ptp-speech-v1--" + quote("Conversation_1:1", safe="") + "--" + STAMP + ".wav")).unlink()
            first = root / ("ptp-speech-v1--" + quote("Conversation_1:0", safe="") + "--" + STAMP + ".wav")
            write_wav(first, amplitude=0)
            with self.assertRaisesRegex(ValueError, "Unusable"):
                prepare_corpus(root, reference)


if __name__ == "__main__":
    unittest.main()
