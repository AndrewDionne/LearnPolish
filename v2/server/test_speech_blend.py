"""Hermetic experimental two-provider Speak tests. No real Azure/Groq calls."""
from __future__ import annotations
import io
import json
import pathlib
import tempfile
import unittest

from family_api import create_app
from speech_assessment import assessment_from_sdk
from speech_blend import blend_assessment, transcript_hints, sound_units
from test_speech_assessment import wav_bytes


def sample_azure(score=84):
    return {"status":"ok","raw":{"NBest":[{"PronunciationAssessment":{
        "AccuracyScore":score,"FluencyScore":100,"CompletenessScore":100
    }}]}}


class BlendUnits(unittest.TestCase):
    def test_same_historical_source_yields_50_plus_84_over_two(self):
        groups=["Świę","to","krzy","ska"]
        one=transcript_hints("Świętokrzyska",groups,"Sweczo Seska")
        two=transcript_hints("Świętokrzyska",groups,"Sveczo Seska")
        self.assertEqual(one,two)
        self.assertEqual(one["transcription_similarity"],50)
        self.assertEqual([x["hint"] for x in one["segments"]],
                         ["review","review","focus","close"])
        result=blend_assessment(assessment_from_sdk(sample_azure()),
                                "Świętokrzyska",groups,"Sweczo Seska")
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["combined"],67)
        self.assertEqual(result["calibration"],"experimental-uncalibrated")
        self.assertNotIn("Sweczo",json.dumps(result))
        self.assertNotIn("transcription_similarity",json.dumps(result))
        self.assertNotIn("50",json.dumps(result))
        self.assertTrue(all(set(x)=={"polish","hint"} for x in result["colourHints"]["segments"]))

    def test_incomplete_or_unaligned_returns_no_fake_blend(self):
        groups=["Świę","to","krzy","ska"]
        for transcript in ("","123",None,"%"*25):
            self.assertEqual(blend_assessment(assessment_from_sdk(sample_azure()),
                "Świętokrzyska",groups,transcript)["status"],"inconclusive")
        self.assertEqual(blend_assessment({"status":"inconclusive"},
            "Świętokrzyska",groups,"Świętokrzyska")["status"],"inconclusive")
        self.assertEqual(blend_assessment({"status":"ok","scores":{"accuracy":None}},
            "Świętokrzyska",groups,"Świętokrzyska")["status"],"inconclusive")
        self.assertEqual(blend_assessment(assessment_from_sdk(sample_azure()),
            "Świętokrzyska",["Świę","to","WRONG","ska"],"Świętokrzyska")["status"],"inconclusive")

    def test_multiple_words_and_mixed_punctuation(self):
        groups=["Dzień ","do","bry"]
        result=transcript_hints("Dzień dobry",groups,"Dzien dobry")
        self.assertEqual("".join(x["polish"] for x in result["segments"]),"Dzień dobry")
        self.assertEqual(sound_units("w"),sound_units("v"))
        self.assertTrue(0<=result["transcription_similarity"]<=100)


class BlendEndpoint(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=pathlib.Path(self.tmp.name)
        self.catalog=root/"catalog.json"
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"speak_swietokrzyska","kind":"vocabulary","items":[{
                "id":"speak_swietokrzyska:0","polish":"Świętokrzyska",
                "pronunciationSegments":{"method":"authored-v1",
                       "segments":["Świę","to","krzy","ska"]}}]},
            {"id":"test_other","kind":"vocabulary","items":[{
                "id":"test_other:0","polish":"Dzień dobry",
                "pronunciationSegments":{"method":"draft-orthographic-v1",
                       "segments":["Dzień ","do","bry"]}}]},
        ]}),encoding="utf-8")
        self.mail=[]
        self.azure=[]
        self.groq=[]
        self.app=create_app(str(root/"family.sqlite"),str(self.catalog),
                            ("http://localhost:5173",),
                            verification_sender=lambda e,c:self.mail.append((e,c)),
                            speech_enabled=True,speech_assessor=self.fake_azure,
                            speech_blend_enabled=True,speech_transcriber=self.fake_whisper)
        self.client=self.app.test_client()
        self.url="/api/v2/family/speech/assess-blend"

    def tearDown(self):
        self.tmp.cleanup()

    def fake_azure(self,wav,ref,key,region):
        self.azure.append((len(wav),ref))
        return sample_azure()

    def fake_whisper(self,wav,key):
        self.groq.append(len(wav))
        return "Sveczo Seska"

    def auth(self):
        details={"email":"adult@example.test","name":"Adult",
                 "password":"Synthetic-Safe-Test-Passphrase-2026"}
        self.assertEqual(self.client.post("/api/v2/family/signup",json=details).status_code,201)
        code=self.mail[-1][1]
        self.assertEqual(self.client.post("/api/v2/family/verification/confirm",
                     json={"email":details["email"],"code":code}).status_code,200)
        return {"Authorization":"Bearer "+self.client.post(
            "/api/v2/family/login",json=details).json["token"]}

    def send(self,headers=None,azure="yes",groq="yes",audio=None,item="speak_swietokrzyska:0"):
        return self.client.post(self.url,headers=headers,
            data={"item_id":item,
                  "approve_azure_audio_upload":azure,
                  "approve_groq_audio_upload":groq,
                  "audio":(io.BytesIO(wav_bytes() if audio is None else audio),"take.wav","audio/wav")},
            content_type="multipart/form-data")

    def test_both_consents_and_source_data_required_before_network(self):
        auth=self.auth()
        self.assertEqual(self.send().status_code,401)
        self.assertEqual(self.send(auth,groq="no").status_code,400)
        self.assertEqual(self.send(auth,azure="no").status_code,400)
        self.assertEqual(self.send(auth,item="unknown").status_code,400)
        self.assertEqual(self.send(auth,audio=b"not-wav").status_code,400)
        self.assertEqual(self.azure,[])
        self.assertEqual(self.groq,[])

    def test_authorized_one_take_calls_each_once_and_no_persistent_private_result(self):
        auth=self.auth()
        reply=self.send(auth)
        self.assertEqual(reply.status_code,200,reply.json)
        self.assertEqual(reply.json["status"],"ok")
        self.assertEqual(reply.json["engine"],"azure-whisper-blend-v1")
        self.assertEqual(reply.json["combined"],67)
        self.assertEqual(reply.json["colourHints"]["segments"][2]["hint"],"focus")
        self.assertEqual(len(self.azure),1)
        self.assertEqual(len(self.groq),1)
        self.assertEqual(self.azure[0][1],"Świętokrzyska")
        self.assertIn("speech-blend;dur=",reply.headers.get("Server-Timing",""))
        self.assertNotIn("Sveczo",reply.get_data(as_text=True))
        self.assertNotIn("azureAccuracy",reply.get_data(as_text=True))
        self.assertEqual(self.send(auth,groq="no").status_code,400)
        self.assertEqual(len(self.groq),1)

    def test_whisper_failure_stays_inconclusive_without_second_call(self):
        self.app=create_app(str(pathlib.Path(self.tmp.name)/"failing.sqlite"),
                            str(self.catalog),("http://localhost:5173",),
                            verification_sender=lambda e,c:self.mail.append((e,c)),
                            speech_enabled=True,speech_assessor=self.fake_azure,
                            speech_blend_enabled=True,
                            speech_transcriber=lambda *_: (_ for _ in ()).throw(RuntimeError("SECRET")))
        self.client=self.app.test_client()
        auth=self.auth()
        reply=self.send(auth)
        self.assertEqual(reply.status_code,200)
        self.assertEqual(reply.json["status"],"inconclusive")
        self.assertNotIn("SECRET",reply.get_data(as_text=True))
        self.assertNotIn("combined",reply.json)
        self.assertEqual(len(self.azure),1)

    def test_azure_failure_does_not_call_whisper(self):
        self.app=create_app(str(pathlib.Path(self.tmp.name)/"failedazure.sqlite"),
                            str(self.catalog),("http://localhost:5173",),
                            verification_sender=lambda e,c:self.mail.append((e,c)),
                            speech_enabled=True,speech_assessor=lambda *_:{"status":"inconclusive","reason":"no_match"},
                            speech_blend_enabled=True,speech_transcriber=self.fake_whisper)
        self.client=self.app.test_client()
        auth=self.auth()
        reply=self.send(auth)
        self.assertEqual(reply.json["status"],"inconclusive")
        self.assertEqual(self.groq,[])
