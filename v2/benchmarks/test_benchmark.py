import json
import pathlib
import tempfile
import unittest
import wave
from array import array

from benchmark import extract_azure_native, load_manifest, polish_match, polish_target_present, run


class BenchmarkTests(unittest.TestCase):
    def test_match_keeps_diacritics(self):
        self.assertTrue(polish_match("Dzień dobry!", "dzień dobry"))
        self.assertFalse(polish_match("zle", "źle"))

    def test_target_presence_recognizes_token_but_not_whole_transcript(self):
        for transcript in ("Czap, czapka.", "Czap-czapka.", "CZAPKA!", "czapka"):
            self.assertTrue(polish_target_present("czapka", transcript))
        self.assertFalse(polish_match("czapka", "Czap, czapka."))
        self.assertFalse(polish_match("czapka", "Czap-czapka."))
        self.assertTrue(polish_match("czapka", "CZAPKA!"))

    def test_target_presence_never_fuzzes_polish_spelling_or_diacritics(self):
        for transcript in ("Często.", "CZASTO", "ciastko", "uczysto"):
            self.assertFalse(polish_target_present("ciasto", transcript))
        self.assertFalse(polish_target_present("źle", "zle"))
        self.assertTrue(polish_target_present("źle", "Powiedział źle."))
        self.assertFalse(polish_target_present("czapka", "czapkach"))
        self.assertFalse(polish_target_present("czapka", "czapką"))
        self.assertFalse(polish_target_present("czapka", ""))
        self.assertFalse(polish_target_present("", "czapka"))
        self.assertTrue(polish_target_present("dzień dobry", "Powiedział dzień dobry!"))
        self.assertFalse(polish_target_present("dzień dobry", "dzień piękny dobry"))

    def test_azure_preserves_native_scores_and_phonemes(self):
        response = {"NBest": [{"Lexical": "cześć", "PronunciationAssessment": {
            "AccuracyScore": 67.2, "FluencyScore": 88.1, "CompletenessScore": 100,
        }, "Words": [{"Word": "cześć", "PronunciationAssessment": {"ErrorType": "None", "AccuracyScore": 66},
                      "Phonemes": [{"Phoneme": "t͡ʂ", "PronunciationAssessment": {"AccuracyScore": 42}}]}]}]}
        result = extract_azure_native(response)
        self.assertEqual(result["scores"]["AccuracyScore"], 67.2)
        self.assertEqual(result["words"][0]["phonemes"][0]["accuracy"], 42)

    def test_requires_16k_pcm_and_marks_silence_inconclusive(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            audio = base / "a.wav"
            with wave.open(str(audio), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(array("h", [0] * 16000).tobytes())
            manifest = base / "manifest.json"
            manifest.write_text(json.dumps([{"id": "sample-1", "audio": "a.wav", "reference": "Cześć"}]))
            self.assertEqual(load_manifest(manifest)[0].reference, "Cześć")
            result = run(manifest, "dry-run", None)
            self.assertEqual(result[0]["status"], "inconclusive")
            with self.assertRaisesRegex(ValueError, "Audio time cap"):
                run(manifest, "dry-run", None, seconds_limit=0.5)

    def test_no_model_download_in_local_mode(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            path = base / "a.wav"
            with wave.open(str(path), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(array("h", [400] * 8000).tobytes())
            manifest = base / "manifest.json"
            manifest.write_text(json.dumps([{"id": "ok", "audio": "a.wav", "reference": "Tak"}]))
            with self.assertRaisesRegex(ValueError, "existing local"):
                run(manifest, "whisper-local", None)


if __name__ == "__main__":
    unittest.main()
