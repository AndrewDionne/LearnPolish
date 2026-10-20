"""Purely synthetic one-shot Polish phoneme feasibility; no AI calls or real voice."""
import hashlib
import io
import json
import math
import pathlib
import tempfile
import unittest
import wave
from array import array

from swietokrzyska_one_azure import (
    SYLLABLES, LOCKED_ADULT_SHA, inspect_one_response, run_one, offline_review,
)

def synthetic_wav(seconds=1.7):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(array("h", [
            round(5100*math.sin(i*.142)) for i in range(round(seconds*16000))
        ]).tobytes())
    return out.getvalue()

def azure_fixture(n=13, *, score=80, word="Świętokrzyska", missing_timing=False):
    phones = [{
        "Offset": (i+1)*1_000_000, "Duration": 850_000,
        "PronunciationAssessment":{"AccuracyScore":score+i%4},
    } for i in range(n)]
    if missing_timing and phones:
        del phones[0]["Offset"]
    return {"status":"ok", "raw":{
        "DisplayText": "PRIVATE SPEAKER VOICE",
        "NBest":[{
            "PronunciationAssessment":{
                "AccuracyScore":84, "FluencyScore":100, "CompletenessScore":100,
            },
            "Words":[{
                "Word":word, "Offset":1_000_000,"Duration":20_000_000,
                "PronunciationAssessment":{"AccuracyScore":81,"ErrorType":"Mispronunciation"},
                "Phonemes":phones,
            }],
        }],
    }}

class OneAzureScoringTests(unittest.TestCase):
    def test_13_unnamed_ordered_phones_create_diagnostic_only(self):
        result = inspect_one_response(azure_fixture())
        self.assertEqual(result["status"],"candidate_not_validated")
        self.assertEqual(result["observed_phone_count"],13)
        self.assertEqual(result["word_accuracy"],81)
        self.assertEqual(result["azure_accuracy"],84)
        self.assertEqual(result["fluency"],100)
        self.assertEqual(result["completeness"],100)
        self.assertEqual([x["syllable"] for x in result["candidate_unverified"]],list(SYLLABLES))
        self.assertEqual([x["phone_count"] for x in result["candidate_unverified"]],[5,2,3,3])
        self.assertFalse(result["can_publish_learner_syllable_grades"])
        self.assertNotIn("PRIVATE",json.dumps(result))

    def test_12_phones_wrong_word_or_invalid_phone_never_fabricates_syllables(self):
        for candidate in [
            azure_fixture(12),
            azure_fixture(word="Sveczo Seska"),
            azure_fixture(missing_timing=True),
            {"status":"inconclusive"},
            {"status":"ok","raw":{"NBest":[]}},
        ]:
            with self.subTest(candidate=str(candidate)[:80]):
                result=inspect_one_response(candidate)
                self.assertIsNone(result["candidate_unverified"])
                self.assertFalse(result["can_publish_learner_syllable_grades"])
        bad=azure_fixture()
        bad["raw"]["NBest"][0]["Words"][0]["Phonemes"][2]["PronunciationAssessment"]["AccuracyScore"]="99"
        self.assertIsNone(inspect_one_response(bad)["candidate_unverified"])
        missing=azure_fixture()
        missing["raw"]["NBest"][0]["Words"][0]["PronunciationAssessment"]["ErrorType"]="Omission"
        self.assertIsNone(inspect_one_response(missing)["candidate_unverified"])

    def test_one_exact_original_and_only_one_provider_call_when_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); folder=root/"private"; folder.mkdir(mode=0o700)
            audio=folder/"ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
            raw=synthetic_wav()
            audio.write_bytes(raw); audio.chmod(0o600)
            sha=hashlib.sha256(raw).hexdigest()
            result=folder/"azure-phoneme-01.jsonl"
            calls=[]
            def fake(wav, reference, key, region):
                calls.append((wav, reference, key, region))
                return azure_fixture()
            options=dict(expected_sha=sha, azure_key="TEST-DO-NOT-USE-AS-SECRET",
                azure_region="germanywestcentral",assessor=fake,
                approve_adult_audio_upload=True,confirm_azure_f0=True,
                confirm_no_paid_billing=True)
            preview=run_one(audio, result, **options)
            self.assertEqual(preview["planned_azure_requests"],1)
            self.assertEqual(preview["azure_requests_sent"],0)
            self.assertEqual(calls,[])
            self.assertFalse(result.exists())
            for flag in ("approve_adult_audio_upload","confirm_azure_f0","confirm_no_paid_billing"):
                settings=options|{flag:False}
                with self.assertRaises(ValueError):
                    run_one(audio,result,send=True,**settings)
                self.assertEqual(calls,[])
            done=run_one(audio,result,send=True,**options)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][0],raw)
            self.assertEqual(calls[0][1],"Świętokrzyska")
            self.assertEqual(done["provider_requests"],1)
            self.assertEqual(done["status"],"candidate_not_validated")
            self.assertFalse(done["can_publish_learner_syllable_grades"])
            self.assertEqual(result.stat().st_mode & 0o777,0o600)
            saved=result.read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE SPEAKER",saved)
            self.assertNotIn("TEST-DO-NOT-USE-AS-SECRET",saved)
            self.assertNotIn("Phonemes",saved)
            self.assertEqual(done, offline_review(audio,result,expected_sha=sha))
            with self.assertRaises(ValueError):
                run_one(audio,result,send=True,**options)
            self.assertEqual(len(calls),1)

    def test_wrong_audio_hash_is_rejected_before_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=pathlib.Path(tmp); folder.chmod(0o700)
            audio=folder/"ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
            audio.write_bytes(synthetic_wav());audio.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"locked original"):
                run_one(audio)
            self.assertEqual(len(LOCKED_ADULT_SHA),64)

if __name__=="__main__":
    unittest.main()
