"""Offline unit tests for the real adult Speak three-provider research route."""
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave
from array import array

from benchmark import read_audio_metadata
from learner_three_model_pilot import prepare, run
from model_fit_review import review


class AdultSpeakBakeoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.folder.chmod(0o700)
        self.name = "ptp-speech-v1--basic%3A0--20261018T180000000Z.wav"
        self.audio = self.folder / self.name
        with wave.open(str(self.audio), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(array("h", [round(4500 * math.sin(i * .14)) for i in range(16000)]).tobytes())
        self.sha = read_audio_metadata(self.audio)["audio_sha256"]
        self.sample = "basic:0@2026-10-18T18:00:00.000Z"
        self.manifest = self.folder / "manifest.json"
        self.manifest.write_text(json.dumps([{
            "id": self.sample, "audio": self.name, "reference": "Dzień dobry",
            "item_id": "basic:0", "audio_sha256": self.sha
        }]))
        self.catalog = self.folder / "catalog.json"
        self.catalog.write_text(json.dumps({"schemaVersion": 1,"lessons":[{
            "id":"basic","items":[{"id":"basic:0","polish":"Dzień dobry"}]
        }]}))
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, output):
        def whisper(audio, model, key):
            self.calls.append((audio, model, key))
            return "Dzień dobry" if model == "whisper-large-v3" else "Dzień"
        def azure(audio, reference, key, region):
            self.calls.append((audio, "azure", key))
            return {"status": "ok", "raw_azure_json": {"NBest":[{
                "PronunciationAssessment":{"AccuracyScore":84,"FluencyScore":87,
                                           "CompletenessScore":90}
            }]}}
        return dict(send=True, approve_adult_audio_upload=True,
                    confirm_groq_free=True, confirm_azure_f0=True,
                    confirm_no_paid_billing=True,
                    groq_key="MOCK-KEY", azure_key="MOCK-KEY", azure_region="germanywestcentral",
                    output=output, transcriber=whisper, assessor=azure)

    def test_preview_zero_calls_and_includes_three_real_engine_names(self):
        result=run(self.manifest,self.catalog,self.sample)
        self.assertEqual(result["status"],"PREVIEW_ONLY")
        self.assertEqual(result["planned_requests"],3)
        self.assertEqual(result["estimated_groq_billed_audio_seconds"],20)
        self.assertEqual(result["planned_azure_audio_seconds"],1)
        self.assertEqual(result["provider_requests_performed"],0)
        self.assertEqual(self.calls,[])

    def test_one_wav_all_three_engines_then_offline_fit_review(self):
        path=self.folder/"adult-01.jsonl"
        result=run(self.manifest,self.catalog,self.sample,**self.args(path))
        self.assertEqual(result["provider_requests_performed"],3)
        self.assertEqual(len(self.calls),3)
        self.assertEqual({a for a,_,_ in self.calls},{self.audio})
        self.assertEqual([m for _,m,_ in self.calls],
                         ["whisper-large-v3","whisper-large-v3-turbo","azure"])
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len({r["audio_sha256"] for r in rows}),1)
        self.assertEqual({r["audio_sha256"] for r in rows},{self.sha})
        self.assertEqual(rows[0]["wer"],0)
        self.assertEqual(rows[1]["pronunciation_grade"],None)
        self.assertEqual(rows[2]["azure_native"]["scores"]["AccuracyScore"],84)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        self.assertEqual(review(rows)["complete_three_engine_triplets"],1)
        with self.assertRaisesRegex(ValueError,"Output exists"):
            run(self.manifest,self.catalog,self.sample,**self.args(path))
        self.assertEqual(len(self.calls),3)

    def test_all_owner_flags_credentials_and_immutable_source_guard_before_upload(self):
        path=self.folder/"blocked.jsonl"
        for name,value in [
            ("approve_adult_audio_upload",False),("confirm_groq_free",False),
            ("confirm_azure_f0",False),("confirm_no_paid_billing",False),
            ("groq_key",""),("azure_key",""),("azure_region","westus")]:
            args=self.args(path)
            args[name]=value
            with self.assertRaises(ValueError):
                run(self.manifest,self.catalog,self.sample,**args)
        self.assertFalse(path.exists())
        self.assertEqual(self.calls,[])
        bad=json.loads(self.manifest.read_text())
        bad[0]["audio_sha256"]="a"*64
        self.manifest.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,"changed"):
            run(self.manifest,self.catalog,self.sample,**self.args(path))
        self.assertEqual(self.calls,[])

    def test_catalog_reference_mismatch_fails_closed(self):
        catalog=json.loads(self.catalog.read_text())
        catalog["lessons"][0]["items"][0]["polish"]="Nieprawdziwe"
        self.catalog.write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError,"authoritative"):
            prepare(self.manifest,self.catalog,self.sample)
        self.assertEqual(self.calls,[])

    def test_preserve_partial_evidence_on_second_provider_failure(self):
        output=self.folder/"partial-01.jsonl"
        args=self.args(output)
        n=0
        def fail_second(audio,model,key):
            nonlocal n
            n+=1
            if n==2:raise RuntimeError("Mock provider unavailable")
            return "Dzień dobry"
        args["transcriber"]=fail_second
        with self.assertRaisesRegex(RuntimeError,"unavailable"):
            run(self.manifest,self.catalog,self.sample,**args)
        rows=[json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["engine"],"groq-whisper-large-v3")
        self.assertEqual(n,2)
        self.assertFalse(self.calls)


if __name__=="__main__":
    unittest.main()
