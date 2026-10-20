"""Synthetic only: confirm exact 67/100 experimental blend and hint-only UI."""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave

from blended_pronunciation_preview import build_blend, load_existing, render_html_preview, SCHEMA
from groq_pilot import MODELS
from phonetic_similarity import WORD, estimate
from swietokrzyska_latency import checked_audio, clean_payload
from swietokrzyska_whisper import safe_row
from phonetic_similarity import write_private_html


class BlendedPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.folder.chmod(0o700)
        self.wav = self.folder/"ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
        with wave.open(str(self.wav),"wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(array("h", [round(4400*math.sin(i*.13)) for i in range(48000)]).tobytes())
        meta = checked_audio(self.wav)
        self.azure = self.folder/"azure-compare-01.jsonl"
        rows = []
        for i,variant in enumerate(("ordinary","preconnect"),1):
            rows.append(clean_payload(variant,i,meta,{
                "status":"ok","timing_ms":{"total":2100.0,
                    "preconnection":0.0,"recognition":2000.0},
                "connected_before_recognition":i==2,
                "scores":{"AccuracyScore":84,"FluencyScore":100,"CompletenessScore":100},
            }))
        self.azure.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
        self.azure.chmod(0o600)
        self.whisper = self.folder/"whisper-01.jsonl"
        rows = [
            safe_row(MODELS[0],1,meta["wav_sha256"],1034.9,"Sweczo Seska"),
            safe_row(MODELS[1],2,meta["wav_sha256"],470.8,"Sveczo Seska"),
        ]
        self.whisper.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
        self.whisper.chmod(0o600)
        self.originals=(self.wav.read_bytes(),self.azure.read_bytes(),self.whisper.read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def test_saved_sources_yield_actual_blend_67_and_color_only(self):
        result=load_existing(self.wav,self.azure,self.whisper)
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(result["reference"],WORD)
        self.assertEqual(result["azure_word_estimate"],84)
        self.assertEqual(result["whisper_transcript_similarity"],50)
        self.assertEqual(result["experimental_blended_overall"],67)
        self.assertEqual(result["new_provider_requests"],0)
        self.assertIsNone(result["syllable_numeric_scores"])
        self.assertFalse(result["can_publish_as_validated_pronunciation_grade"])
        self.assertFalse(result["affects_xp_or_progression"])
        self.assertEqual([x["hint"] for x in result["syllable_hints"]],
            ["review","review","focus","close"])
        self.assertEqual([x["polish"] for x in result["syllable_hints"]],
            ["Świę","to","krzy","ska"])
        html=render_html_preview(result)
        # Exactly one unboxed coloured word and one score in the body.
        self.assertIn('<h1 class="word"',html)
        self.assertIn('gap:.12em;',html)  # Three subtle visual breaks; no actual spaces in word
        self.assertEqual(html.count('class="syllable '),4)
        self.assertIn('>67/100</output>',html)
        self.assertEqual(html.count('class="syllable review"'),2)
        self.assertEqual(html.count('class="syllable focus"'),1)
        self.assertEqual(html.count('class="syllable close"'),1)
        self.assertIn('.syllable.review{color:',html)
        self.assertIn('.syllable.focus{color:',html)
        self.assertIn('.syllable.close{color:',html)
        self.assertNotIn('.syllable.review{background:',html)
        body=html.split('<body>',1)[1].split('</body>',1)[0]
        import re
        visible=''.join(re.sub(r'<[^>]+>','',body).split())
        self.assertEqual(visible,'Świętokrzyska67/100')
        for excluded in (
            '<p', '<header', '<footer', '<summary', '<details', '<small',
            '<input', '<label', '<button', 'class="card"', 'class="legend"',
            'class="cue"', 'class="english-cue"',
        ):
            self.assertNotIn(excluded,body)
        self.assertNotIn("Świę 50%",html)
        self.assertNotIn("krzy 0%",html)
        self.assertNotIn("Sweczo Seska",html)
        self.assertNotIn("Sveczo Seska",html)
        self.assertNotIn("<script",html)
        self.assertNotIn("https://",html)
        preview=self.folder/"blend-preview-01.html"
        write_private_html(preview,self.wav,html)
        self.assertEqual(preview.stat().st_mode&0o777,0o600)
        self.assertEqual((self.wav.read_bytes(),self.azure.read_bytes(),self.whisper.read_bytes()),self.originals)
        with self.assertRaises(ValueError):
            write_private_html(preview,self.wav,html)

    def test_different_azure_estimates_or_malformed_results_refuse_blend(self):
        proxy=estimate(WORD,[(MODELS[0],"Sweczo Seska"),(MODELS[1],"Sveczo Seska")])
        valid={"status":"WHISPER_PAIRED_RESULT","reference":WORD,"same_audio_verified":True,
            "azure_baseline":[
                {"scores":{"AccuracyScore":84}},{"scores":{"AccuracyScore":81}},
            ]}
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            build_blend(proxy,valid)
        valid["azure_baseline"][1]["scores"]["AccuracyScore"]=84
        self.assertEqual(build_blend(proxy,valid)["experimental_blended_overall"],67)
        for wrong in (float("nan"),101,True,"84"):
            valid["azure_baseline"][0]["scores"]["AccuracyScore"]=wrong
            with self.assertRaises(ValueError):
                build_blend(proxy,valid)
        valid["azure_baseline"][0]["scores"]["AccuracyScore"]=84
        proxy["syllables"][0]["transcription_proxy_agreement"]=False
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            build_blend(proxy,valid)

    def test_disagreeing_whisper_proxies_refuse_numeric_blend(self):
        proxy=estimate(WORD,[(MODELS[0],"Świętokrzyska"),(MODELS[1],"Sveczo Seska")])
        valid={"status":"WHISPER_PAIRED_RESULT","reference":WORD,"same_audio_verified":True,
            "azure_baseline":[{"scores":{"AccuracyScore":84}},{"scores":{"AccuracyScore":84}}]}
        with self.assertRaisesRegex(ValueError,"disagree"):
            build_blend(proxy,valid)

    def test_not_allowed_to_render_forged_validated_score_or_syllable_grade(self):
        example=load_existing(self.wav,self.azure,self.whisper)
        for mutation in (
            {"can_publish_as_validated_pronunciation_grade":True},
            {"syllable_numeric_scores":[50,50,0,100]},
            {"experimental_blended_overall":84},
            {"new_provider_requests":1},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    render_html_preview(example|mutation)

    def test_saved_sha_mismatch_rejected_without_any_provider_call(self):
        lines=self.whisper.read_text(encoding="utf-8").splitlines()
        first=json.loads(lines[0]);first["audio_sha256"]="0"*64
        lines[0]=json.dumps(first)
        self.whisper.write_text("\n".join(lines)+"\n",encoding="utf-8")
        with self.assertRaises(ValueError):
            load_existing(self.wav,self.azure,self.whisper)


if __name__=="__main__":
    unittest.main()
