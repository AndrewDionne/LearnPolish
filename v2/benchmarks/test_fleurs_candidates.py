"""Fully offline tests of bounded, unverified FLEURS Polish corpus staging."""
from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import wave
from array import array

from fleurs_candidates import (
    _audio_url, _bounded_get, extract_candidates, get_candidates, private_root,
    rows_url, stage, stage_batch,
)
from sentence_study import validate_source


class Reply:
    def __init__(self, url: str, body: bytes):
        self.url = url
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return None
    def geturl(self):
        return self.url
    def read(self, count: int):
        return self.body[:count]


class NativeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.original = self.root / "Pl-czapka.ogg"
        self.original.write_bytes(b"DO NOT MOVE OR REPLACE THIS SOURCE")
        self.url = "https://datasets-server.huggingface.co/cached-assets/google/fleurs/--/"
        self.responses = {}
        rows = []
        for i in range(12):
            uri = self.url + "some-public-cache/audio-" + str(i) + ".wav?Expires=111"
            wav = self._wav(880+i)
            self.responses[uri] = wav
            rows.append({
                "row_idx": i,
                "row": {
                    "id": 2000 + i,
                    "num_samples": 6 * 16000,
                    "raw_transcription": "To jest prawdziwe zdanie w języku polskim numer " + str(i),
                    "transcription": "some normalized string not necessarily accurate",
                    "audio": [{"src": uri, "type": "audio/wav"}],
                    "gender": 0 if i % 2 == 0 else 1,
                }
            })
        self.metadata = {"rows": rows, "partial": False, "num_rows_total": 198}
        self.metadata_bytes = json.dumps(self.metadata).encode("utf-8")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def _wav(self, peak: int):
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(array("h", [peak] * (16000 * 6)).tobytes())
            return buffer.getvalue()

    def opener(self, request, timeout):
        uri = request.full_url
        self.calls.append(uri)
        if "rows?" in uri:
            return Reply(uri, self.metadata_bytes)
        return Reply(uri, self.responses[uri])

    def convert(self, origin, target):
        shutil.copyfile(origin, target)

    def test_preview_only_fetches_bounded_metadata(self):
        self.assertIn("config=pl_pl", rows_url(0, 80))
        self.assertIn("split=validation", rows_url(0, 80))
        cands = get_candidates(count=10, offset=0, opener=self.opener)
        self.assertEqual(len(cands), 10)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.calls[0].startswith("https://datasets-server.huggingface.co/rows?"))
        self.assertFalse((self.root / "sentences-source.json").exists())

    def test_stages_twelve_unverified_audio_and_keeps_old_recordings(self):
        candidates = extract_candidates(self.metadata, count=12)
        report = stage(self.root, candidates, opener=self.opener,
                       converter=self.convert, research_root=self.root)
        self.assertEqual(report["candidate_count"], 12)
        self.assertEqual(report["speech_ai_requests"], 0)
        self.assertFalse(report["provider_upload_approved"])
        self.assertEqual(self.original.read_bytes(), b"DO NOT MOVE OR REPLACE THIS SOURCE")
        manifest = json.loads((self.root / "sentences-source.json").read_text())
        self.assertEqual(len(manifest), 12)
        self.assertTrue(all(row["reference_verified_by_human"] is False for row in manifest))
        self.assertTrue(all(row["audio_audited_unclipped"] is False for row in manifest))
        self.assertTrue(all(row["provider_upload_approved"] is False for row in manifest))
        self.assertTrue(all(row["speaker_id"] == "REQUIRES_NATIVE_REVIEW" for row in manifest))
        self.assertTrue(all(row["speaker_role"] == "native_control" for row in manifest))
        self.assertEqual((self.root / "sentences-source.json").stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.root / "fleurs-pl-val-00000.wav").exists())
        self.assertIn("prawdziwe zdanie", manifest[0]["reference"])
        with self.assertRaisesRegex(ValueError, "Human transcript"):
            validate_source(self.root / "sentences-source.json")
        with self.assertRaisesRegex(ValueError, "overwritten"):
            stage(self.root, candidates, opener=self.opener,
                  converter=self.convert, research_root=self.root)

    def test_forbids_audio_urls_outside_public_trusted_host(self):
        for uri in [
            "http://datasets-server.huggingface.co/cached-assets/google/fleurs/--/x",
            "https://malicious.example/cached-assets/google/fleurs/--/x",
            "https://datasets-server.huggingface.co/cached-assets/other/fleurs/--/x",
            "https://name:password@datasets-server.huggingface.co/cached-assets/google/fleurs/--/x",
            "file:///Users/me/private.wav",
        ]:
            with self.assertRaisesRegex(ValueError, "safely hosted"):
                _audio_url([{"src": uri, "type": "audio/wav"}])
        with self.assertRaisesRegex(ValueError, "FLEURS request unexpectedly redirected"):
            _bounded_get("https://datasets-server.huggingface.co/rows", 100,
                         opener=lambda req, timeout: Reply("https://evil.example/a", b"json"))

    def test_no_manifest_if_audio_fetch_fails_midflight(self):
        cand = extract_candidates(self.metadata, count=3)
        count = []
        def denied(request, timeout):
            count.append(request.full_url)
            if len(count) == 2:
                raise OSError("network failed")
            return self.opener(request, timeout)
        with self.assertRaisesRegex(RuntimeError, "no retry"):
            stage(self.root, cand, opener=denied, converter=self.convert, research_root=self.root)
        self.assertFalse((self.root / "sentences-source.json").exists())
        self.assertEqual(list(self.root.glob("fleurs-pl-val-*.wav")), [])
        self.assertEqual(list(self.root.glob(".fleurs-stage-*")), [])
        self.assertTrue(self.original.exists())

    def test_new_second_batch_preserves_first_batch_and_publishes_new_manifest(self):
        first = extract_candidates(self.metadata, count=2)
        stage(self.root, first, opener=self.opener, converter=self.convert,
              research_root=self.root)
        original_manifest = (self.root / "sentences-source.json").read_bytes()
        # Use non-overlapping FLEURS row indexes for the second batch.
        second = extract_candidates({"rows": self.metadata["rows"][2:]}, count=3)
        report = stage_batch(self.root, second, "fleurs-batch-02",
                             opener=self.opener, converter=self.convert,
                             research_root=self.root)
        self.assertEqual(report["batch_name"], "fleurs-batch-02")
        self.assertEqual(report["speech_ai_requests"], 0)
        self.assertEqual((self.root / "sentences-source.json").read_bytes(), original_manifest)
        self.assertEqual(self.original.read_bytes(), b"DO NOT MOVE OR REPLACE THIS SOURCE")
        newdir = self.root / "fleurs-batch-02"
        self.assertTrue((newdir / "sentences-source.json").exists())
        self.assertEqual(len(json.loads((newdir / "sentences-source.json").read_text())), 3)
        self.assertEqual(newdir.stat().st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(ValueError, "Existing batch"):
            stage_batch(self.root, second, "fleurs-batch-02", opener=self.opener,
                        converter=self.convert, research_root=self.root)
        with self.assertRaisesRegex(ValueError, "must be named"):
            stage_batch(self.root, second, "../other", opener=self.opener,
                        converter=self.convert, research_root=self.root)

    def test_failed_second_batch_is_cleaned_without_touching_first(self):
        old = (self.root / "original-not-for-removal.ogg")
        old.write_bytes(b"ORIGINAL")
        def reject(*args):
            raise OSError("fake ffmpeg failure")
        with self.assertRaisesRegex(OSError, "fake ffmpeg failure"):
            stage_batch(self.root, extract_candidates(self.metadata, count=1),
                        "fleurs-batch-02", opener=self.opener,
                        converter=reject, research_root=self.root)
        self.assertEqual(old.read_bytes(), b"ORIGINAL")
        self.assertFalse((self.root / "fleurs-batch-02").exists())
        self.assertEqual(list(self.root.glob(".fleurs-new-batch-*")), [])

    def test_fail_closed_when_not_enough_eligible_native_sentences(self):
        short = {"rows": [dict(self.metadata["rows"][0], row=dict(self.metadata["rows"][0]["row"], num_samples=16000))]}
        with self.assertRaisesRegex(ValueError, "Too few"):
            extract_candidates(short, count=1)
        with self.assertRaisesRegex(ValueError, "Only 1"):
            extract_candidates(self.metadata, count=13)
        with self.assertRaisesRegex(ValueError, "bounded offset"):
            rows_url(-1, 80)

    def test_audio_size_limit(self):
        uri = "https://datasets-server.huggingface.co/cached-assets/google/fleurs/--/blob.wav"
        with self.assertRaisesRegex(ValueError, "exceeded bounded"):
            _bounded_get(uri, 2, opener=lambda req, timeout: Reply(uri, b"12345"))

    def test_private_root_must_be_exact_and_chmod_700(self):
        with self.assertRaisesRegex(ValueError, "ONLY"):
            private_root(self.root.parent, research_root=self.root)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "chmod 700"):
            private_root(self.root, research_root=self.root)


if __name__ == "__main__":
    unittest.main()
