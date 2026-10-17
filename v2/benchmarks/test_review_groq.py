"""Offline regression for the owner's actual Groq Polish ASR experiment."""
import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array

from benchmark import read_audio_metadata
from review_groq import review, MODELS


class OfflineGroqReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rows = []
        sources = [
            ("commons-native-01", "czapka", ["Czap, czapka.", "Czap-czapka."]),
            ("commons-native-02", "ciasto", ["Często.", "CZASTO"]),
        ]
        self.manifest_rows = []
        for sample_id, reference, responses in sources:
            wav = self.root / (sample_id + ".wav")
            with wave.open(str(wav), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(array("h", [800] * 16000).tobytes())
            meta = read_audio_metadata(wav)
            self.manifest_rows.append({
                "id": sample_id, "audio": wav.name, "reference": reference,
                "audio_sha256": meta["audio_sha256"],
            })
            for model, transcript in zip(MODELS, responses):
                self.rows.append({
                    "id": sample_id, "reference": reference,
                    "engine": "groq-" + model, "model": model,
                    "status": "ok", "transcript": transcript,
                    "audio_sha256": meta["audio_sha256"], "audio_seconds": 1.0,
                    "recognized_expected_words": False, "pronunciation_score": None,
                })
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps(self.manifest_rows))
        self.results = self.root / "results.jsonl"
        self.write_results()

    def tearDown(self):
        self.tmp.cleanup()

    def write_results(self, rows=None):
        self.results.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n"
                                       for x in (rows if rows is not None else self.rows)))

    def test_actual_first_4_results_have_target_but_no_exact_transcription(self):
        result = review(self.manifest, self.results)
        self.assertTrue(result["complete_matrix"])
        self.assertEqual(result["processed_results"], 4)
        for model in result["models"]:
            self.assertEqual(model["reference_present"], 1)
            self.assertEqual(model["reference_exact_match"], 0)
            self.assertEqual(model["missing_responses"], 0)
        self.assertEqual([x["reference_present"] for x in result["samples"]],
                         [True, True, False, False])
        self.assertEqual([x["reference_exact_match"] for x in result["samples"]],
                         [False, False, False, False])
        self.assertTrue(all(x["legacy_recognized_expected_words"] is False
                            for x in result["samples"]))
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["new_audio_uploads"], 0)

    def test_partial_results_remain_partial_not_false_failures(self):
        self.write_results(self.rows[:1])
        result = review(self.manifest, self.results)
        self.assertFalse(result["complete_matrix"])
        self.assertEqual(result["processed_results"], 1)
        self.assertEqual([x["missing_responses"] for x in result["models"]], [1, 2])

    def test_rejects_duplicate_model_sample_and_changed_reference(self):
        self.write_results(self.rows + [self.rows[0]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            review(self.manifest, self.results)
        tampered = [dict(x) for x in self.rows]
        tampered[0]["reference"] = "ciasto"
        self.write_results(tampered)
        with self.assertRaisesRegex(ValueError, "locked source"):
            review(self.manifest, self.results)

    def test_rejects_changed_audio_sha_and_model(self):
        tampered = [dict(x) for x in self.rows]
        tampered[0]["audio_sha256"] = "f"*64
        self.write_results(tampered)
        with self.assertRaisesRegex(ValueError, "locked source"):
            review(self.manifest, self.results)
        tampered = [dict(x) for x in self.rows]
        tampered[0]["model"] = "made-up"
        self.write_results(tampered)
        with self.assertRaisesRegex(ValueError, "Unknown sample"):
            review(self.manifest, self.results)

    def test_rejects_modified_original_wav_without_rewriting_results(self):
        wav = self.root / "commons-native-01.wav"
        with wav.open("ab") as f:
            f.write(b"changed")
        with self.assertRaisesRegex(ValueError, "Source WAV content differs"):
            review(self.manifest, self.results)

    def test_rejects_fabricated_pronunciation_grade(self):
        tampered = [dict(x) for x in self.rows]
        tampered[0]["pronunciation_score"] = 99
        self.write_results(tampered)
        with self.assertRaisesRegex(ValueError, "cannot carry a pronunciation grade"):
            review(self.manifest, self.results)


if __name__ == "__main__":
    unittest.main()
