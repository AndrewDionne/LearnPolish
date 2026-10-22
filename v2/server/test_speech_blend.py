"""Hermetic experimental two-provider Speak tests. No real Azure/Groq calls."""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import sqlite3
import tempfile
import unittest

from family_api import create_app
from speech_assessment import assessment_from_sdk
from speech_blend import blend_assessment, transcript_hints, sound_units
from test_speech_assessment import wav_bytes
from unittest.mock import patch
from speech_blend import groq_whisper_transcribe


def sample_azure(score=84):
    return {"status":"ok","raw":{"NBest":[{"PronunciationAssessment":{
        "AccuracyScore":score,"FluencyScore":100,"CompletenessScore":100
    }}]}}


class BlendUnits(unittest.TestCase):
    def test_groq_transport_one_bounded_request_with_exact_wav_and_no_retries(self):
        """A local fake HTTPS response proves the provider adapter does not mutate takes."""
        recording=wav_bytes(seconds=1.123,amplitude=4900)
        seen=[]
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def read(self,limit):
                self_limit=limit
                assert self_limit<=16384
                return '{"text":"Świętokrzyska"}'.encode("utf-8")
        def fake_open(request,timeout):
            seen.append((request,timeout))
            return FakeResponse()
        with patch("speech_blend.urllib.request.urlopen",side_effect=fake_open):
            result=groq_whisper_transcribe(recording,"SYNTHETIC-NO-REAL-KEY")
        self.assertEqual(result,"Świętokrzyska")
        self.assertEqual(len(seen),1)
        req,timeout=seen[0]
        self.assertEqual(timeout,18)
        self.assertEqual(req.full_url,"https://api.groq.com/openai/v1/audio/transcriptions")
        self.assertEqual(req.data.count(recording),1)
        self.assertNotIn("SYNTHETIC-NO-REAL-KEY",str(req.data))
        self.assertEqual(req.get_method(),"POST")
        seen.clear()
        with patch("speech_blend.urllib.request.urlopen",
                   side_effect=TimeoutError("FAKE PROVIDER TIMEOUT")):
            with self.assertRaises(TimeoutError):
                groq_whisper_transcribe(recording,"SYNTHETIC-NO-REAL-KEY")
        # No automatic retries hidden in this provider adapter.
        self.assertEqual(seen,[])

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
        self.additional=json.loads(
            (pathlib.Path(__file__).resolve().parents[1]/
             "content"/"additional-speak-reference-blockers.json").read_text(encoding="utf-8")
        )["sourceBlockers"]
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"speak_swietokrzyska","kind":"vocabulary","items":[{
                "id":"speak_swietokrzyska:0","polish":"Świętokrzyska",
                "pronunciationSegments":{"method":"authored-v1",
                       "segments":["Świę","to","krzy","ska"]}}]},
            {"id":"test_other","kind":"vocabulary","items":[{
                "id":"test_other:0","polish":"Dzień dobry",
                "pronunciationSegments":{"method":"draft-orthographic-v1",
                       "segments":["Dzień ","do","bry"]}}]},
            {"id":"Conversation_1","kind":"vocabulary","items":[{
                "id":"Conversation_1:24","polish":"Jak ma pan/pani na imię?",
                "referenceReview":"practice_only",
                "pronunciationSegments":{"method":"draft-orthographic-v1",
                    "segments":["Jak ma pan/pani na imię?"]}},
                {"id":"Conversation_1:25","polish":"Mam na imię…",
                "referenceReview":"practice_only",
                "pronunciationSegments":{"method":"draft-orthographic-v1",
                    "segments":["Mam na imię…"]}}]},
            {"id":"additional","kind":"vocabulary","items":[
                {"id":row["itemId"],"polish":row["polish"],
                 "referenceReview":"practice_only",
                 "pronunciationSegments":{"method":"draft-orthographic-v1",
                                         "segments":[row["polish"]]}}
                for row in self.additional]},
            {"id":"unflagged","kind":"vocabulary","items":[
                {"id":"new:slash","polish":"Co pan/pani poleca?",
                 "pronunciationSegments":{"method":"draft-orthographic-v1",
                                          "segments":["Co pan/pani poleca?"]}},
                {"id":"new:digits","polish":"Droga 999",
                 "pronunciationSegments":{"method":"draft-orthographic-v1",
                                          "segments":["Droga 999"]}},
                {"id":"new:ellipsis","polish":"Jestem w …",
                 "pronunciationSegments":{"method":"draft-orthographic-v1",
                                          "segments":["Jestem w …"]}}]},
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
        self.azure.append((len(wav),ref,hashlib.sha256(wav).hexdigest()))
        return sample_azure()

    def fake_whisper(self,wav,key):
        self.groq.append((len(wav),hashlib.sha256(wav).hexdigest()))
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

    def test_unverified_greetings_are_rejected_before_azure_or_groq(self):
        auth=self.auth()
        blocked=["Conversation_1:24","Conversation_1:25"] + [
            row["itemId"] for row in self.additional
        ] + ["new:slash","new:digits","new:ellipsis"]
        self.assertEqual(len(blocked),17)
        for item in blocked:
            denied=self.send(auth,item=item)
            self.assertEqual(denied.status_code,400)
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


    def test_validated_take_is_identical_bytes_at_both_provider_adapters(self):
        """No resynthesis/re-encode/alternate take, only synthetic local adapters."""
        auth=self.auth()
        take=wav_bytes(seconds=1.37,amplitude=5200)
        expected=hashlib.sha256(take).hexdigest()
        result=self.send(auth,audio=take)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json["status"],"ok")
        self.assertEqual(self.azure,[(len(take),"Świętokrzyska",expected)])
        self.assertEqual(self.groq,[(len(take),expected)])
        self.assertNotIn(expected,result.get_data(as_text=True))
        self.assertNotIn(expected,self.app.test_client().get(
            "/api/v2/family/health").get_data(as_text=True))

    def test_rejected_silence_clipping_duration_and_bad_riff_cost_zero(self):
        """Before quota/provider, reject failed captures; no retry or fake grade."""
        auth=self.auth()
        cases=[
            b"RIFF"+b"bad",b"not a wave",wav_bytes(.59),
            wav_bytes(10.01),wav_bytes(1,amplitude=0),
            wav_bytes(1,amplitude=32767),wav_bytes(1)[:-14],
        ]
        for take in cases:
            with self.subTest(audio_bytes=len(take)):
                result=self.send(auth,audio=take)
                self.assertEqual(result.status_code,400,result.json)
                self.assertNotIn("scores",result.json)
                self.assertNotIn("combined",result.json)
        self.assertEqual(self.azure,[])
        self.assertEqual(self.groq,[])
        with sqlite3.connect(pathlib.Path(self.tmp.name)/"family.sqlite") as db:
            self.assertEqual(db.execute("SELECT COALESCE(SUM(requests),0) "
                "FROM speech_usage").fetchone()[0],0)

    def test_shared_f0_daily_cap_blocks_blend_and_single_provider(self):
        """Azure-only and two-provider share 12/user and count before SDK."""
        auth=self.auth()
        audio=wav_bytes()
        first=self.client.post("/api/v2/family/speech/assess",headers=auth,
            content_type="multipart/form-data",data={
                "item_id":"speak_swietokrzyska:0",
                "approve_azure_audio_upload":"yes",
                "audio":(io.BytesIO(audio),"take.wav","audio/wav")})
        self.assertEqual(first.status_code,200,first.json)
        for _ in range(11):
            self.assertEqual(self.send(auth).status_code,200)
        denied=self.send(auth)
        self.assertEqual(denied.status_code,429,denied.json)
        self.assertNotIn("scores",denied.json)
        self.assertNotIn("combined",denied.json)
        self.assertEqual(len(self.azure),12)
        self.assertEqual(len(self.groq),11)
        with sqlite3.connect(pathlib.Path(self.tmp.name)/"family.sqlite") as db:
            self.assertEqual(db.execute("SELECT requests FROM speech_usage").fetchone()[0],12)

    def test_provider_exception_remains_inconclusive_and_consumes_one_allowance(self):
        """Do not refund SDK/network failures; never leak exception text."""
        def failure(*_):
            self.azure.append(("attempt",))
            raise TimeoutError("PRIVATE PROVIDER KEY AND TRANSCRIPT")
        # An injected mock endpoint only; no real service ever contacted.
        self.app=create_app(str(pathlib.Path(self.tmp.name)/"timeout.sqlite"),
            str(self.catalog),("http://localhost:5173",),
            verification_sender=lambda e,c:self.mail.append((e,c)),
            speech_enabled=True,speech_assessor=failure,
            speech_blend_enabled=True,speech_transcriber=self.fake_whisper)
        self.client=self.app.test_client()
        auth=self.auth()
        result=self.send(auth)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json["status"],"inconclusive")
        self.assertNotIn("combined",result.json)
        self.assertNotIn("scores",result.json)
        self.assertNotIn("PRIVATE",result.get_data(as_text=True))
        self.assertEqual(self.groq,[])
        with sqlite3.connect(pathlib.Path(self.tmp.name)/"timeout.sqlite") as db:
            self.assertEqual(db.execute("SELECT requests FROM speech_usage").fetchone()[0],1)
