"""Offline tests for transcript-derived syllable estimate and private report UI.

Only dummy WAV, fake provider evidence; NEVER real voice, keys, networks.
"""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave

from phonetic_similarity import (
    SCHEMA, SYLLABLES, WORD, align, english_guide, estimate, from_saved, per_syllable,
    render_html, sound_units, write_private_html,
)
from groq_pilot import MODELS
from swietokrzyska_latency import checked_audio, clean_payload
from swietokrzyska_whisper import safe_row


class PolishSyllableProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.folder.chmod(0o700)
        self.wav = self.folder / "ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
        with wave.open(str(self.wav),"wb") as file:
            file.setnchannels(1);file.setsampwidth(2);file.setframerate(16000)
            file.writeframes(array("h", [
                int(4600*math.sin(i*.11)) for i in range(48000)
            ]).tobytes())
        meta=checked_audio(self.wav)
        self.azure=self.folder/"azure-compare-01.jsonl"
        azure_rows=[]
        for i, variant in enumerate(("ordinary","preconnect"),1):
            azure_rows.append(clean_payload(variant,i,meta,{
                "status":"ok",
                "timing_ms":{"total":2459.7 if i==1 else 1923.3,
                             "preconnection":0.0 if i==1 else 423.9,
                             "recognition":2457.4 if i==1 else 1499.1},
                "connected_before_recognition":i==2,
                "scores":{"AccuracyScore":84.0,"FluencyScore":100.0,"CompletenessScore":100.0},
            }))
        self.azure.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in azure_rows))
        self.azure.chmod(0o600)
        self.whisper=self.folder/"whisper-01.jsonl"
        groq_rows=[
            safe_row(MODELS[0],1,meta["wav_sha256"],1034.9,"Sweczo Seska"),
            safe_row(MODELS[1],2,meta["wav_sha256"],470.8,"Sveczo Seska"),
        ]
        self.whisper.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in groq_rows))
        self.whisper.chmod(0o600)
        self.azure_bytes=self.azure.read_bytes()
        self.whisper_bytes=self.whisper.read_bytes()
        self.wav_bytes=self.wav.read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def test_shared_english_cues_exactly_align_to_four_scored_syllables(self):
        guide = english_guide()
        self.assertEqual(guide["polish"],WORD)
        self.assertEqual(tuple(x["polish"] for x in guide["syllables"]),SYLLABLES)
        self.assertEqual(guide["stressIndex"],2)
        self.assertEqual(guide["reviewStatus"],"needs_native_speaker_review")
        self.assertEqual([x["englishCue"] for x in guide["syllables"]],
                         ["shfyehn","toh","KSHIH","skah"])
        self.assertTrue(all(x["letterFocus"] and x["tip"] for x in guide["syllables"]))
        score = estimate(WORD,[(MODELS[0],"Sweczo Seska"),(MODELS[1],"Sveczo Seska")])
        self.assertEqual(score["english_guide"],guide)
        page = render_html(score)
        self.assertIn("English-friendly sounds sit below each Polish syllable",page)
        self.assertIn("KSHIH · STRESS",page)
        self.assertIn("shfyehn",page)
        self.assertIn("skah",page)
        self.assertIn("English guide (approx.)",page)
        self.assertEqual(page.count('class="english-cue"'),4)
        self.assertNotIn("<script",page)

    def test_expected_polish_syllable_segmentation_and_word_v_are_equivalent_in_asr(self):
        self.assertEqual(SYLLABLES,("Świę","to","krzy","ska"))
        self.assertEqual(sound_units("Sweczo Seska"),sound_units("Sveczo Seska"))
        self.assertEqual(sound_units("Świętokrzyska"),
                         sum([sound_units(s) for s in SYLLABLES],[]))
        self.assertEqual(sound_units("krzy"),["k","sz","y"])
        self.assertEqual(sound_units("w"),sound_units("v"))

    def test_perfect_written_recognition_is_100_but_not_proof_of_perfect_pronunciation(self):
        report=estimate(WORD,[(MODELS[0],WORD),(MODELS[1],WORD)])
        self.assertEqual(report["overall_estimate_range"],[100,100])
        self.assertEqual([s["min_estimate"] for s in report["syllables"]],[100]*4)
        self.assertTrue(all(not s["comparisons"][0]["edits"] for s in report["syllables"]))
        self.assertIn("not verified speaker errors",report["scoring_contract"]["warning"])

    def test_both_real_spellings_give_same_proxy_but_not_same_verified_sounds(self):
        report=estimate(WORD,[(MODELS[0],"Sweczo Seska"),(MODELS[1],"Sveczo Seska")])
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(len(report["syllables"]),4)
        self.assertTrue(all(s["transcription_proxy_agreement"] for s in report["syllables"]))
        self.assertEqual(report["overall_estimate_range"][0],report["overall_estimate_range"][1])
        self.assertLess(report["overall_estimate_range"][0],100)
        self.assertEqual(report["syllables"][-1]["syllable"],"ska")
        self.assertEqual(report["syllables"][-1]["min_estimate"],100)
        self.assertEqual(report["syllables"][-1]["status"],"close")
        self.assertTrue(any(s["min_estimate"]<100 for s in report["syllables"][:-1]))
        self.assertEqual(report["network_calls"],0)

    def test_disagreeing_models_show_neutral_uncertainty_not_a_confident_single_score(self):
        report=estimate(WORD,[(MODELS[0],WORD),(MODELS[1],"Sveczo Seska")])
        self.assertEqual(len(report["overall_estimate_range"]),2)
        self.assertLess(report["overall_estimate_range"][0],100)
        self.assertEqual(report["overall_estimate_range"][1],100)
        self.assertTrue(any(s["status"]=="uncertain" for s in report["syllables"]))

    def test_unknown_words_and_unreviewed_target_do_not_generate_false_syllables(self):
        with self.assertRaises(ValueError):
            per_syllable("Dzień dobry","Dzień dobry")
        for candidate in ("", "ź#x", "s" * 501):
            with self.assertRaises(ValueError):
                sound_units(candidate)
        with self.assertRaises(ValueError):
            estimate(WORD, [])
        with self.assertRaises(ValueError):
            estimate(WORD, [(MODELS[0],"")])

    def test_realistic_saved_evidence_processed_offline_originals_unchanged(self):
        report=from_saved(self.wav,self.azure,self.whisper)
        self.assertEqual(report["network_calls"],0)
        self.assertTrue(report["same_original_audio_verified"])
        self.assertEqual(report["prior_azure_calls"],2)
        self.assertEqual(report["prior_whisper_calls"],2)
        self.assertEqual(self.wav.read_bytes(),self.wav_bytes)
        self.assertEqual(self.azure.read_bytes(),self.azure_bytes)
        self.assertEqual(self.whisper.read_bytes(),self.whisper_bytes)

    def test_private_html_is_clickable_readable_colour_coded_and_never_overwrites(self):
        report=from_saved(self.wav,self.azure,self.whisper)
        private_html=render_html(report)
        self.assertIn("<details",private_html)
        self.assertEqual(private_html.count('<details class="segment'),4)
        self.assertIn("Świę",private_html)
        self.assertIn("krzy",private_html)
        self.assertIn("ska",private_html)
        self.assertIn("focus",private_html)
        self.assertIn("uncertain",private_html)
        self.assertIn("not an acoustic measurement",private_html)
        self.assertNotIn("<script",private_html)
        self.assertNotIn("https://",private_html)
        page=self.folder/"phonetic-review-01.html"
        write_private_html(page,self.wav,private_html)
        self.assertEqual(page.stat().st_mode & 0o777,0o600)
        self.assertEqual(page.read_text(),private_html)
        with self.assertRaises(ValueError):
            write_private_html(page,self.wav,private_html)
        with self.assertRaises(ValueError):
            write_private_html(self.folder/"sample.json",self.wav,private_html)
        self.assertEqual(self.azure.read_bytes(),self.azure_bytes)

    def test_untrusted_text_is_escaped_when_rendering_html(self):
        report=estimate(WORD,[(MODELS[0],"Sveczo Seska")])
        report["model_hypotheses"][0]["transcript"]='<img src=x onerror=alert(1)>'
        report["syllables"][0]["comparisons"][0]["model"]='<script>alert(1)</script>'
        page=render_html(report)
        self.assertNotIn('<img src=x',page)
        self.assertNotIn('<script>alert(1)</script>',page)
        self.assertIn('&lt;script&gt;',page)

    def test_forged_prior_whisper_audio_hash_or_wrong_audio_refused_before_analysis(self):
        tampered=[json.loads(line) for line in self.whisper.read_text().splitlines()]
        tampered[0]["audio_sha256"]="b"*64
        self.whisper.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in tampered))
        with self.assertRaises(ValueError):
            from_saved(self.wav,self.azure,self.whisper)


if __name__=="__main__":
    unittest.main()
