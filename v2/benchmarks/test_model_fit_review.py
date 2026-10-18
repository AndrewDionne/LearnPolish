"""Deterministic offline contract for selecting fit of three distinct Polish speech engines."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from model_fit_review import review, main, V3, TURBO, AZURE


class ModelFitReviewTests(unittest.TestCase):
    def setUp(self):
        self.sha = "b" * 64
        self.rows = [
            {"sample_id": "same-wav", "engine": V3, "status": "ok",
             "audio_sha256": self.sha, "reference": "Dzień dobry wszystkim",
             "transcript": "Dzień dobry wszystkim", "wer": 0.95,
             "pronunciation_grade": None},
            {"sample_id": "same-wav", "engine": TURBO, "status": "ok",
             "audio_sha256": self.sha, "reference": "Dzień dobry wszystkim",
             "transcript": "Dzień dobry", "pronunciation_grade": None},
            {"sample_id": "same-wav", "engine": AZURE, "status": "ok",
             "audio_sha256": self.sha, "reference": "Dzień dobry wszystkim",
             "azure_native": {"scores": {"AccuracyScore": 93.0, "FluencyScore": 85,
                                         "CompletenessScore": 95}},
             "assessment_is_human_calibrated": False},
        ]
        self.labels = [{"id": "same-wav", "audio_sha256": self.sha,
                        "heard_without_reference": "Dzień dobry wszystkim",
                        "intelligible": True, "target_correct": True,
                        "capture_quality": "clear"}]

    def test_one_real_wav_three_engines_cannot_certify_winner(self):
        result = review(self.rows)
        self.assertEqual(result["complete_three_engine_triplets"], 1)
        self.assertEqual(result["status"], "insufficient_evidence_for_final_model_selection")
        self.assertEqual(result["independent_human_labels"], 0)
        self.assertEqual(result["model_results"][V3]["mean_wer_vs_intended_text_asr_only"], 0)
        self.assertEqual(result["model_results"][TURBO]["mean_wer_vs_intended_text_asr_only"], 0.3333)
        self.assertEqual(result["model_results"][AZURE]["raw_accuracy_mean_uncalibrated"], 93)
        self.assertNotIn("transcript", json.dumps(result).lower())
        self.assertIsNone(result["model_results"][V3]["pronunciation_quality_score"])
        self.assertFalse(result["model_results"][AZURE]["named_polish_phoneme_diagnosis_certified"])

    def test_completed_blind_labels_are_separate_from_machine_transcripts(self):
        result = review(self.rows, self.labels)
        self.assertEqual(result["model_results"][V3]["human_transcript_pairs"], 1)
        self.assertEqual(result["model_results"][TURBO]["mean_wer_vs_blind_human_transcript_asr_only"], 0.3333)
        self.assertEqual(result["model_results"][AZURE]["raw_accuracy_mean_human_target_correct_clear"], 93.0)
        self.assertIsNone(result["model_results"][AZURE]["raw_accuracy_mean_human_target_incorrect_clear"])
        self.assertEqual(result["status"], "insufficient_evidence_for_final_model_selection")

    def test_sha_mismatch_and_reference_divergence_are_hard_failures(self):
        other = copy.deepcopy(self.rows)
        other[1]["audio_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "Different audio bytes"):
            review(other)
        other = copy.deepcopy(self.rows)
        other[2]["reference"] = "Another expected phrase"
        with self.assertRaisesRegex(ValueError, "Different reference"):
            review(other)
        wrong_label = copy.deepcopy(self.labels)
        wrong_label[0]["audio_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "label WAV fingerprint"):
            review(self.rows, wrong_label)

    def test_partial_provider_errors_remain_visible_not_zero(self):
        rows = copy.deepcopy(self.rows)
        rows[2] = {**rows[2], "status": "inconclusive", "azure_native": None}
        result = review(rows)
        self.assertEqual(result["model_results"][AZURE]["inconclusive_results"], 1)
        self.assertIsNone(result["model_results"][AZURE]["raw_accuracy_mean_uncalibrated"])
        rows.pop()
        result = review(rows)
        self.assertEqual(result["complete_three_engine_triplets"], 0)
        self.assertEqual(result["model_results"][AZURE]["missing_results"], 1)

    def test_no_spoofed_grades_unknown_engine_or_duplicate_rows(self):
        bad = copy.deepcopy(self.rows)
        bad[0]["engine"] = "invented-phonetic-grader"
        with self.assertRaisesRegex(ValueError, "Unknown"):
            review(bad)
        with self.assertRaisesRegex(ValueError, "Duplicated"):
            review(self.rows + [self.rows[0]])
        bad = copy.deepcopy(self.rows)
        bad[2]["azure_native"]["scores"]["AccuracyScore"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Malformed"):
            review(bad)
        bad = copy.deepcopy(self.labels)
        bad[0]["target_correct"] = "yes"
        with self.assertRaisesRegex(ValueError, "Complete blinded"):
            review(self.rows, bad)

    def test_offline_cli_report_from_saved_results_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "saved.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in self.rows) + "\n")
            # Pure review requires no key/network/audio and does not touch inputs.
            before = path.read_bytes()
            result = review([json.loads(line) for line in path.read_text().splitlines()])
            self.assertEqual(result["distinct_audio_samples"], 1)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
