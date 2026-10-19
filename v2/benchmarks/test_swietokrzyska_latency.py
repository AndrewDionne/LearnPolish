"""Private Świętokrzyska latency A/B: no SDK, keys, network, or real voice."""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave
import contextlib
import io
import os
import sys
from unittest.mock import patch

from swietokrzyska_latency import (
    WORD, ITEM_ID, VARIANTS, checked_audio, preview, run, summary, clean_payload
)


class ŚwiętokrzyskaLatencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.folder.chmod(0o700)
        self.audio=self.folder/"ptp-speech-v1--speak_swietokrzyska%3A0--20261019T112900000Z.wav"
        with wave.open(str(self.audio),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(array("h",[int(6000*math.sin(i*.12)) for i in range(24000)]).tobytes())
        self.output=self.folder/"measured-01.jsonl"
        self.calls=[]
        self.report_fake=None

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self,wav,reference,key,region,variant):
        self.calls.append((wav,reference,key,region,variant))
        return {
            "status":"ok",
            "timing_ms":{
                "total":4500.0 if variant=="ordinary" else 1800.0,
                "preconnection":0.0 if variant=="ordinary" else 500.0,
                "recognition":4400.0 if variant=="ordinary" else 1200.0,
            },
            "scores":{"AccuracyScore":94.0,"FluencyScore":91.0,"CompletenessScore":100.0},
            "connected_before_recognition":variant=="preconnect",
            "sdk_result_reason":None,
            "SECRET_HEADER":"never log",
        }

    def options(self):
        return dict(output=self.output,send=True,
            approve_adult_audio_upload=True,confirm_azure_f0=True,
            confirm_no_paid_billing=True,azure_key="not-real-test-key",
            azure_region="germanywestcentral",assessor=self.fake)

    def test_preview_only_new_target_and_no_calls(self):
        data=preview(self.audio)
        self.assertEqual(data["reference"],WORD)
        self.assertEqual(data["sample_id"],ITEM_ID)
        self.assertEqual(data["planned_azure_requests"],2)
        self.assertEqual(data["provider_calls"],0)
        self.assertEqual(data["planned_groq_requests"],0)
        self.assertEqual(data["sequence"],list(VARIANTS))
        self.assertEqual(data["wav_seconds"],1.5)
        self.assertEqual(run(self.audio)["status"],"PREVIEW_ONLY")
        self.assertEqual(self.calls,[])
        self.assertFalse(self.output.exists())

    def test_cold_vs_preconnect_same_exact_original_no_key_leak(self):
        data=run(self.audio,**self.options())
        self.assertEqual(data["status"],"PAIRED_RESULT")
        self.assertTrue(data["same_audio_verified"])
        self.assertEqual(data["actual_provider_attempts_saved"],2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual([x[-1] for x in self.calls],list(VARIANTS))
        self.assertEqual([x[1] for x in self.calls],[WORD,WORD])
        self.assertEqual({x[0] for x in self.calls},{self.audio})
        self.assertTrue(data["observations"][1]["connected_before_recognition"])
        self.assertEqual(data["observations"][0]["timing_ms"]["total"],4500)
        self.assertEqual(data["observations"][1]["timing_ms"]["recognition"],1200)
        saved=self.output.read_text()
        self.assertEqual(self.output.stat().st_mode & 0o777,0o600)
        self.assertNotIn("not-real-test-key",saved)
        self.assertNotIn("SECRET_HEADER",saved)
        self.assertEqual(summary(self.audio,self.output),data)
        with self.assertRaises(ValueError):
            run(self.audio,**self.options())
        self.assertEqual(len(self.calls),2)

    def test_reject_unapproved_or_incorrect_key_region_before_azure(self):
        for name,value in (
            ("approve_adult_audio_upload",False),
            ("confirm_azure_f0",False),
            ("confirm_no_paid_billing",False),
            ("azure_key",""),
            ("azure_key","secret\u2026"),
            ("azure_region","eastus"),
            ("output",None),
        ):
            options=self.options()
            options[name]=value
            with self.assertRaises(ValueError):
                run(self.audio,**options)
            self.assertEqual(self.calls,[])
            self.assertFalse(self.output.exists())

    def test_reject_wrong_word_filename_changed_audio_and_world_readable_folder(self):
        bad=self.folder/"ptp-speech-v1--anyone%3A0--20261019T112900000Z.wav"
        bad.write_bytes(self.audio.read_bytes())
        with self.assertRaises(ValueError):
            checked_audio(bad)
        bad.unlink()
        self.folder.chmod(0o755)
        with self.assertRaises(ValueError):
            checked_audio(self.audio)
        self.folder.chmod(0o700)
        with open(self.audio,"r+b") as f:
            f.truncate(50)
        with self.assertRaises((ValueError,EOFError)):
            checked_audio(self.audio)
        self.assertEqual(self.calls,[])

    def test_safe_error_partial_does_not_attempt_second_upload(self):
        calls=[]
        def raises(*args):
            calls.append(1)
            raise RuntimeError("PRIVATE SDK EXCEPTION with key and audio")
        options=self.options();options["assessor"]=raises
        result=run(self.audio,**options)
        self.assertEqual(len(calls),1)
        self.assertEqual(result["status"],"PARTIAL")
        self.assertEqual(result["observations"][0]["status"],"error")
        self.assertNotIn("PRIVATE SDK",self.output.read_text())
        self.assertNotIn("key and audio",self.output.read_text())

    def test_inconclusive_keeps_separate_native_grade_and_no_fabrication(self):
        options=self.options()
        outcomes=iter([
            {"status":"inconclusive","scores":None,
             "timing_ms":{"total":4500,"preconnection":0,"recognition":4400},
             "connected_before_recognition":False,"sdk_result_reason":"NoMatch"},
            {"status":"ok","scores":{"AccuracyScore":97,"FluencyScore":93,"CompletenessScore":100},
             "timing_ms":{"total":900,"preconnection":150,"recognition":650},
             "connected_before_recognition":False,"sdk_result_reason":None},
        ])
        options["assessor"]=lambda *_:next(outcomes)
        result=run(self.audio,**options)
        self.assertEqual([x["status"] for x in result["observations"]],["inconclusive","ok"])
        self.assertIsNone(result["observations"][0]["scores_uncalibrated"])
        self.assertFalse(result["observations"][1]["connected_before_recognition"])
        self.assertEqual(result["observations"][1]["scores_uncalibrated"]["AccuracyScore"],97)

    def test_safe_preflight_names_missing_key_and_region_without_provider_calls(self):
        options=self.options()
        options["azure_key"]=None
        with self.assertRaisesRegex(ValueError,"AZURE_SPEECH_KEY is not exported"):
            run(self.audio,**options)
        options["azure_key"]="SECRET" + "\u2026"
        with self.assertRaisesRegex(ValueError,"invalid shape or placeholder"):
            run(self.audio,**options)
        options["azure_key"]="PRIVATE-TEST-NOT-REAL"
        options["azure_region"]=None
        with self.assertRaisesRegex(ValueError,"AZURE_SPEECH_REGION must be germanywestcentral"):
            run(self.audio,**options)
        self.assertEqual(self.calls,[])
        self.assertFalse(self.output.exists())

    def test_existing_private_result_is_reported_before_key_check_and_never_retried(self):
        self.output.write_text('{"partial":"preserve"}\\n')
        self.output.chmod(0o600)
        original=self.output.read_bytes()
        options=self.options()
        options["azure_key"]=None
        with self.assertRaisesRegex(ValueError,"Output already exists; preserve it"):
            run(self.audio,**options)
        self.assertEqual(self.output.read_bytes(),original)
        self.assertEqual(self.calls,[])

    def test_cli_safe_preflight_messages_never_expose_key_or_private_path(self):
        from swietokrzyska_latency import main
        flags=["--wav",str(self.audio),"--send","--approve-adult-audio-upload",
               "--confirm-azure-f0","--confirm-no-paid-billing",
               "--output",str(self.output)]
        def invoke(env):
            stderr=io.StringIO()
            with patch.object(sys,"argv",["swietokrzyska_latency.py",*flags]), \\
                 patch.dict(os.environ, env, clear=True), contextlib.redirect_stderr(stderr), \\
                 self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code,2)
            return stderr.getvalue()
        no_key=invoke({"AZURE_SPEECH_REGION":"germanywestcentral"})
        self.assertIn("AZURE_SPEECH_KEY is not exported",no_key)
        self.assertNotIn(str(self.audio),no_key)
        self.assertEqual(self.calls,[])
        # File is present: stop before even checking keys or contacting Azure.
        self.output.write_text('{"partial":"preserve"}\\n')
        self.output.chmod(0o600)
        file_present=invoke({})
        self.assertIn("Output already exists; preserve it",file_present)
        self.assertNotIn(str(self.audio),file_present)
        self.assertNotIn("partial",file_present)
        self.assertEqual(self.calls,[])

    def test_only_allowlisted_sanitized_score_and_timing_payload(self):
        x=clean_payload("ordinary",1,checked_audio(self.audio),{
            "status":"ok","timing_ms":{"total":2200,"preconnection":0,"recognition":2100},
            "scores":{"AccuracyScore":98,"FluencyScore":90,"CompletenessScore":100},
            "sdk_result_reason":"PRIVATE ERROR INCLUDING KEY",
        })
        self.assertEqual(x["sdk_result_reason"],"Other")
        self.assertNotIn("PRIVATE",json.dumps(x))
        with self.assertRaises(ValueError):
            clean_payload("ordinary",1,checked_audio(self.audio),{
                "status":"ok","timing_ms":{"total":1000,"preconnection":0,"recognition":900},
                "scores":{"AccuracyScore":float("nan"),"FluencyScore":92,"CompletenessScore":100},
            })


if __name__=="__main__":
    unittest.main()
