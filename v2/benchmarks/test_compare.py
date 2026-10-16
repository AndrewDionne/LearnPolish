import unittest
from compare import compare

class CompareEvidenceTests(unittest.TestCase):
    def test_rejects_unlabelled_and_non_comparable_provider_data(self):
        w={"a":{"engine":"whisper-local","reference":"cześć","audio_seconds":1,"status":"ok","recognized_expected_words":True}}
        a={"a":{"engine":"azure-raw","reference":"cześć","audio_seconds":1,"status":"ok","recognized_expected_words":True,"scores":{"AccuracyScore":79},"words":[{"phonemes":[{"phoneme":"t͡ɕ"}]}]}}
        with self.assertRaisesRegex(ValueError,"human"):
            compare(w,a,[])
        with self.assertRaisesRegex(ValueError,"intelligibility"):
            compare(w,a,[{"id":"a"}])
        z=compare(w,a,[{"id":"a","intelligible":True}])
        self.assertEqual(z["sample_count"],1)
        self.assertEqual(z["azure_native_phoneme_data_count"],1)
        self.assertEqual(z["whisper_word_recognition"]["agreement_with_human_intelligibility"],1)
        a["a"]["audio_seconds"]=2
        with self.assertRaisesRegex(ValueError,"duration"):
            compare(w,a,[{"id":"a","intelligible":True}])

    def test_absent_inference_is_inconclusive_not_fake_failure(self):
        w={"a":{"engine":"whisper-local","reference":"tak","audio_seconds":1,"status":"inconclusive"}}
        a={"a":{"engine":"azure-raw","reference":"tak","audio_seconds":1,"status":"inconclusive"}}
        z=compare(w,a,[{"id":"a","intelligible":False}])
        self.assertIsNone(z["whisper_word_recognition"]["agreement_with_human_intelligibility"])
        self.assertIsNone(z["azure_word_recognition"]["agreement_with_human_intelligibility"])

if __name__=="__main__": unittest.main()
