"""All offline. No real learner audio, provider calls or Azure credentials."""
import json
import pathlib
import tempfile
import unittest

from polish_phoneme_evidence import inspect_raw, inspect_private_result


def raw_azure(n=13):
    return {"NBest":[{"Words":[{"Word":"PRIVATE-NO-ECHO",
        "Phonemes":[{"PronunciationAssessment":{"AccuracyScore":max(0,90-i)}} for i in range(n)],
        "PronunciationAssessment":{"AccuracyScore":85}}]}],
        "DisplayText":"PRIVATE-NO-ECHO"}


class OfflineStructureTests(unittest.TestCase):
    def test_valid_polish_phoneme_array_still_never_publishes_syllable_scores(self):
        result=inspect_raw(raw_azure())
        self.assertEqual(result["status"],"structural_evidence_only")
        self.assertEqual(result["phoneme_score_count"],13)
        self.assertTrue(result["has_ordered_phoneme_scores"])
        self.assertFalse(result["has_named_phonemes"])
        self.assertFalse(result["can_publish_syllable_scores"])
        self.assertIsNone(result["syllable_scores"])
        self.assertNotIn("PRIVATE",json.dumps(result))

    def test_azure_english_syllable_fields_do_not_unlock_polish_grading(self):
        raw=raw_azure()
        raw["NBest"][0]["Words"][0]["Syllables"]=[
            {"Syllable":"PRIVATE-NO-ECHO","PronunciationAssessment":{"AccuracyScore":99}},
            {"Syllable":"PRIVATE-NO-ECHO","PronunciationAssessment":{"AccuracyScore":98}},
        ]
        result=inspect_raw(raw)
        self.assertEqual(result["native_syllable_score_count"],2)
        self.assertFalse(result["can_publish_syllable_scores"])
        self.assertIsNone(result["syllable_scores"])

    def test_malformed_missing_omitted_or_multiword_never_invents_scores(self):
        for raw in (None,{},{"NBest":[]},{"NBest":[{"Words":[]}]},
                    {"NBest":[{"Words":[{},{}]}]}):
            with self.subTest(raw=raw):
                self.assertFalse(inspect_raw(raw)["can_publish_syllable_scores"])
        for broken in (None,{},{"AccuracyScore":-1},{"AccuracyScore":1000},
                       {"AccuracyScore":float("nan")},{"AccuracyScore":"99"}):
            raw=raw_azure()
            raw["NBest"][0]["Words"][0]["Phonemes"][0]["PronunciationAssessment"]=broken
            result=inspect_raw(raw)
            self.assertFalse(result["has_ordered_phoneme_scores"])
            self.assertEqual(result["phoneme_score_count"],0)

    def test_private_file_cannot_be_read_outside_ignored_research_directory(self):
        with tempfile.TemporaryDirectory() as root:
            path=pathlib.Path(root)/"azure.json"
            path.write_text(json.dumps({"engine":"azure-pl-PL-scripted",
                "locale":"pl-PL","raw_azure_json":raw_azure()}))
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"PathToPolish-Private-AI"):
                inspect_private_result(path)


if __name__=="__main__":
    unittest.main()
