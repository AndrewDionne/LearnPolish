"""Offline HTTP contract tests: authenticated, consented, no persistent WAV, no provider calls in CI."""
import io
import json
import pathlib
import tempfile
import unittest
import wave
from array import array

from family_api import create_app
from speech_assessment import checked_wav, InvalidAudio, assessment_from_sdk


def wav_bytes(seconds=1.0, amplitude=4500):
    output = io.BytesIO()
    with wave.open(output, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(array("h", [
            round(amplitude * __import__("math").sin(i * 0.14))
            for i in range(round(seconds * 16000))
        ]).tobytes())
    return output.getvalue()


class AssessmentUnitTests(unittest.TestCase):
    def test_audio_quality_format_duration_hard_limits(self):
        good = wav_bytes(1.2)
        self.assertAlmostEqual(checked_wav(good)[0], 1.2)
        for data in (b"not-wave", wav_bytes(.3), wav_bytes(10.1),
                     wav_bytes(1.0,0), wav_bytes(1.0,32767)):
            with self.subTest(size=len(data)):
                with self.assertRaises(InvalidAudio):
                    checked_wav(data)

    def test_only_native_scores_and_no_fabricated_zero_when_incomplete(self):
        raw = {"status":"ok","raw":{"NBest":[{"PronunciationAssessment":{
            "AccuracyScore":93.0,"FluencyScore":93.0,"CompletenessScore":92.0,
            "Words":[{"Word":"secret spoken","AccuracyScore":5}]}}]}}
        result=assessment_from_sdk(raw)
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["scores"],{"accuracy":93.0,"fluency":93.0,"completeness":92.0})
        self.assertEqual(result["calibration"],"uncalibrated")
        self.assertNotIn("secret spoken",json.dumps(result))
        self.assertNotIn("Words",json.dumps(result))
        self.assertEqual(assessment_from_sdk({"status":"ok","raw":{"NBest":[]}}),
                         {"status":"inconclusive","reason":"no_assessment"})
        self.assertNotIn("scores",assessment_from_sdk({"status":"inconclusive","reason":"canceled"}))
        incomplete={"status":"ok","raw":{"NBest":[{"PronunciationAssessment":{
            "AccuracyScore":93,"FluencyScore":95}}]}}
        self.assertNotIn("scores",assessment_from_sdk(incomplete))


class SpeechApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        self.catalog=self.root/"lessons.json"
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"a","kind":"vocabulary","items":[{"id":"a:0","polish":"Dzień dobry"}]},
            {"id":"speak_swietokrzyska","kind":"vocabulary","items":[
                {"id":"speak_swietokrzyska:0","polish":"Świętokrzyska"}]},
            {"id":"Conversation_1","kind":"vocabulary","items":[
                {"id":"Conversation_1:24","polish":"Jak ma pan/pani na imię?",
                 "referenceReview":"practice_only"},
                {"id":"Conversation_1:25","polish":"Mam na imię…",
                 "referenceReview":"practice_only"}]}
        ]}))
        self.calls=[]
        self.mail=[]
        self.database=self.root/"family.sqlite"
        self.app=create_app(str(self.database),str(self.catalog),("http://localhost:5173",),
                            verification_sender=lambda email,code:self.mail.append((email,code)),
                            speech_enabled=True,speech_assessor=self.fake_assessor)
        self.client=self.app.test_client()
        self.url="/api/v2/family/speech/assess"

    def tearDown(self):
        self.tmp.cleanup()

    def auth(self,email):
        details={"email":email,"name":"Learner","password":"Private-family-passphrase-2026"}
        self.assertEqual(self.client.post("/api/v2/family/signup",json=details).status_code,201)
        self.assertEqual(self.client.post("/api/v2/family/verification/confirm",
            json={"email":email,"code":self.mail[-1][1]}).status_code,200)
        response=self.client.post("/api/v2/family/login",json=details)
        self.assertEqual(response.status_code,200)
        return {"Authorization":"Bearer "+response.json["token"]}

    def fake_assessor(self,wav,reference,key,region):
        self.calls.append((len(wav),reference,key,region))
        return {"status":"ok","raw":{"NBest":[{"PronunciationAssessment":{
            "AccuracyScore":93,"FluencyScore":93,"CompletenessScore":92}}]}}

    def send(self,headers=None,item="a:0", consent="yes",audio=None):
        return self.client.post(self.url,headers=headers,content_type="multipart/form-data",
            data={"item_id":item,"approve_azure_audio_upload":consent,
                  "audio":(io.BytesIO(audio if audio is not None else wav_bytes()),"speech.wav","audio/wav")})

    def test_auth_and_consent_missing_never_send_provider_request(self):
        auth=self.auth("a@example.com")
        self.assertEqual(self.send().status_code,401)
        self.assertEqual(self.send(auth,consent="no").status_code,400)
        self.assertEqual(self.send(auth,item="unknown").status_code,400)
        self.assertEqual(self.send(auth,audio=wav_bytes(.2)).status_code,400)
        self.assertEqual(self.send(auth,audio=b"abc").status_code,400)
        self.assertEqual(self.send(auth,audio=wav_bytes(amplitude=0)).status_code,400)
        self.assertEqual(self.calls,[])

    def test_unverified_greeting_references_cannot_consume_provider_requests(self):
        auth=self.auth("pending@example.com")
        for item in ("Conversation_1:24","Conversation_1:25"):
            denied=self.send(auth,item=item)
            self.assertEqual(denied.status_code,400)
        self.assertEqual(self.calls,[])
        with self.app.app_context():
            import sqlite3
            with sqlite3.connect(self.database) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM speech_usage").fetchone()[0],0)

    def test_one_consented_request_returns_real_scalar_scores_not_server_stored(self):
        auth=self.auth("b@example.com")
        response=self.send(auth)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json["status"],"ok")
        self.assertEqual(response.json["engine"],"azure-pl-PL-scripted")
        self.assertEqual(response.json["calibration"],"uncalibrated")
        self.assertEqual(response.json["scores"],{"accuracy":93.0,"fluency":93.0,"completeness":92.0})
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.calls[0][1],"Dzień dobry")
        # Duration-only Server-Timing, no speech text, key or private transcript.
        header=response.headers.get("Server-Timing","")
        self.assertRegex(header, r"^speech-sdk;dur=\d+(?:\.\d+)?$")
        self.assertNotIn("Dzień",header)
        self.assertNotIn("Private",header)
        self.assertNotIn("test",header)
        self.assertNotIn("wav",self.database.read_bytes().decode("latin-1"))
        with self.app.app_context():
            import sqlite3
            with sqlite3.connect(self.database) as con:
                self.assertEqual(con.execute("SELECT requests FROM speech_usage").fetchone()[0],1)

    def test_new_swietokrzyska_reference_is_server_authoritative_and_timed(self):
        auth=self.auth("warsaw@example.com")
        response=self.send(auth,item="speak_swietokrzyska:0")
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.calls[0][1],"Świętokrzyska")
        self.assertEqual(response.json["status"],"ok")
        self.assertNotIn("latency",response.json)
        self.assertRegex(response.headers.get("Server-Timing",""), r"^speech-sdk;dur=\d+(?:\.\d+)?$")
        self.assertEqual(len(self.calls),1)
        # Unauthorized, cross-origin and no-consent paths must not issue
        # further provider requests or expose measurement headers.
        denied=self.send(auth,item="speak_swietokrzyska:0",consent="no")
        self.assertEqual(denied.status_code,400)
        self.assertIsNone(denied.headers.get("Server-Timing"))
        allowed_origin=self.send(auth|{"Origin":"http://localhost:5173"},item="speak_swietokrzyska:0")
        self.assertEqual(allowed_origin.status_code,200)
        self.assertEqual(allowed_origin.headers.get("Access-Control-Expose-Headers"),"Server-Timing")

    def test_daily_cap_durable_and_cors_untrusted(self):
        auth=self.auth("c@example.com")
        self.assertEqual(self.send(auth|{"Origin":"https://evil.example"}).status_code,403)
        for _ in range(12):
            self.assertEqual(self.send(auth).status_code,200)
        self.assertEqual(self.send(auth).status_code,429)
        self.assertEqual(len(self.calls),12)
        second=create_app(str(self.database),str(self.catalog),("http://localhost:5173",),
                          verification_sender=lambda email,code:None,
                          speech_enabled=True,speech_assessor=self.fake_assessor)
        new_client=second.test_client()
        result=new_client.post(self.url,headers=auth,
            data={"item_id":"a:0","approve_azure_audio_upload":"yes",
                  "audio":(io.BytesIO(wav_bytes()),"speech.wav","audio/wav")})
        self.assertEqual(result.status_code,429)
        self.assertEqual(len(self.calls),12)

    def test_disabled_endpoint_and_no_default_provider_key(self):
        disabled=create_app(str(self.root/"off.sqlite"),str(self.catalog),
                            ("http://localhost:5173",),
                            verification_sender=lambda e,c:None,speech_enabled=False)
        response=disabled.test_client().post(self.url)
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.calls,[])

    def test_inconclusive_sdk_does_not_synthesize_score(self):
        self.app=create_app(str(self.root/"inc.sqlite"),str(self.catalog),
                            ("http://localhost:5173",),
                            verification_sender=lambda e,c:self.mail.append((e,c)),
                            speech_enabled=True,
                            speech_assessor=lambda *_:{"status":"inconclusive","reason":"canceled"})
        self.client=self.app.test_client()
        auth=self.auth("d@example.com")
        response=self.send(auth)
        self.assertEqual(response.json["status"],"inconclusive")
        self.assertEqual(response.json["reason"],"canceled")
        self.assertNotIn("scores",response.json)


if __name__ == "__main__":
    unittest.main()
