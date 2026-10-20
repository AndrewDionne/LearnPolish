import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import azure_voice_audition as audition


class AzureVoiceAuditionSafetyTests(unittest.TestCase):
    def make_plan(self):
        voices = ["pl-PL-MarekNeural", "pl-PL-AgnieszkaNeural", "pl-PL-ZofiaNeural"]
        rows = []
        for index in range(8):
            polish = "Dzień dobry" if index == 0 else "Cześć" + str(index)
            for voice in voices:
                rows.append({
                    "itemId": f"lesson:{index}",
                    "polish": polish,
                    "voiceId": voice,
                    "textSha256": hashlib.sha256(polish.encode("utf-8")).hexdigest(),
                    "characters": len(polish),
                    "suggestedLocalFilename": f"{voice}/lesson_{index}.mp3",
                    "status": "not_generated_not_reviewed",
                })
        return {"schemaVersion": 1, "phase": "offline_preview_only",
                "voices": [{"id": voice} for voice in voices],
                "ownerVoicePreference": {"rankedVoiceIds": voices},
                "audition": rows}

    def test_limited_preview_is_offline_and_does_not_require_keys(self):
        plan = self.make_plan()
        with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
             patch.object(audition, "generate", side_effect=AssertionError("no synthesis")), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(audition.main(["--limit", "3"]), 0)
        self.assertIn('"status": "PREVIEW_ONLY"', output.getvalue())
        self.assertIn('"new_requests": 0', output.getvalue())

    def test_preferred_paired_voice_preview_includes_same_four_actual_phrases(self):
        plan = self.make_plan()
        pairs = audition.select_paired_rows(plan, 4)
        self.assertEqual(len(pairs), 8)
        self.assertEqual([x["voiceId"] for x in pairs[:2]],
                         ["pl-PL-MarekNeural", "pl-PL-AgnieszkaNeural"])
        self.assertEqual(len({x["itemId"] for x in pairs}), 4)
        self.assertNotIn("pl-PL-ZofiaNeural", [x["voiceId"] for x in pairs])
        with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
             patch.object(audition, "generate", side_effect=AssertionError("no API")), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(audition.main([]), 0)
        self.assertIn('"files": 8', output.getvalue())
        self.assertIn('"new_requests": 0', output.getvalue())
        self.assertEqual(len(audition.select_paired_rows(plan, 8)), 16)
        with self.assertRaisesRegex(ValueError, "requires 1–8"):
            audition.select_paired_rows(plan, 9)
        changed = self.make_plan()
        changed["ownerVoicePreference"]["rankedVoiceIds"].reverse()
        with self.assertRaisesRegex(ValueError, "ranking"):
            audition.select_paired_rows(changed, 2)

    def test_options_prevent_mixing_legacy_and_paired_modes(self):
        plan = self.make_plan()
        with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
             patch.object(audition, "generate", side_effect=AssertionError("no API")):
            with self.assertRaises(SystemExit) as failure:
                audition.main(["--pairs", "4", "--limit", "3"])
        self.assertEqual(failure.exception.code, 2)

    def test_send_needs_all_explicit_owner_guards_before_any_network(self):
        plan = self.make_plan()
        with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
             patch.object(audition, "generate", side_effect=AssertionError("no network")):
            with self.assertRaises(SystemExit) as raised:
                audition.main(["--send"])
        self.assertEqual(raised.exception.code, 2)

    def test_diagnose_delegates_to_offline_native_player_without_synthesis(self):
        with patch.object(audition, "generate", side_effect=AssertionError("no synthesis")), \
             patch("voice_audition_player.main", return_value=0) as checked, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(audition.main(["--diagnose"]), 0)
        checked.assert_called_once_with(["--diagnose"])
        with self.assertRaises(SystemExit) as error:
            audition.main(["--diagnose", "--send"])
        self.assertEqual(error.exception.code, 2)

    def test_gallery_opens_official_browser_demo_without_paid_synthesis(self):
        plan = self.make_plan()
        with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
             patch.object(audition, "generate", side_effect=AssertionError("no synthesis")), \
             patch.object(audition.webbrowser, "open", return_value=True) as opened, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(audition.main(["--gallery"]), 0)
        opened.assert_called_once_with("https://speech.microsoft.com/audiocontentcreation")

    def test_listen_invokes_local_player_not_provider(self):
        from voice_audition_player import main as player_main
        with patch.object(audition, "generate", side_effect=AssertionError("no synthesis")), \
             patch("voice_audition_player.main", return_value=0) as opened, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(audition.main(["--listen"]), 0)
        opened.assert_called_once_with(["--open"])

    def test_reject_modified_polish_duplicate_paths_and_too_many_clips(self):
        plan = self.make_plan()
        self.assertEqual(len(audition.select_audition_rows(plan, 3)), 3)
        for limit in (0, 25):
            with self.assertRaises(ValueError):
                audition.select_audition_rows(plan, limit)
        plan["audition"][0]["polish"] = "Changed"
        with self.assertRaisesRegex(ValueError, "Changed Polish"):
            audition.select_audition_rows(plan, 3)
        plan = self.make_plan()
        plan["audition"][0]["suggestedLocalFilename"] = "../outside.mp3"
        with self.assertRaisesRegex(ValueError, "Unsafe voice"):
            audition.select_audition_rows(plan, 3)

    def test_read_only_preflight_does_not_expose_key_or_contact_provider(self):
        plan = self.make_plan()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "PathToPolish-Private-AI" / "voice-audition-01"
            with patch.object(audition, "plan_from_generated_catalog", return_value=plan), \
                 patch.object(audition, "generate", side_effect=AssertionError("no calls")), \
                 patch.object(audition, "OUTPUT", folder), \
                 patch.dict(os.environ, {"AZURE_SPEECH_KEY": "private-test-key-do-not-print",
                                        "AZURE_SPEECH_REGION": "westeurope"}), \
                 redirect_stdout(io.StringIO()) as out:
                self.assertEqual(audition.main(["--preflight"]), 0)
            report = json.loads(out.getvalue())
            self.assertEqual(report["status"], "LOCAL_PREFLIGHT_ONLY")
            self.assertEqual(report["proposed_requests"], 8)
            self.assertTrue(report["azure_key_present"])
            self.assertTrue(report["azure_region_format_valid"])
            self.assertEqual(report["provider_requests_made"], 0)
            self.assertFalse(report["speech_f0_and_no_paid_billing_verified"])
            self.assertNotIn("private-test-key-do-not-print", out.getvalue())
            with patch.object(audition, "plan_from_generated_catalog", return_value=plan):
                with self.assertRaises(SystemExit) as rejected:
                    audition.main(["--preflight", "--send"])
            self.assertEqual(rejected.exception.code, 2)

    def test_partial_provider_failure_retains_verified_playable_audio_without_retry(self):
        from voice_audition_player import verified_clips, write_player
        plan = self.make_plan()
        pair = audition.select_paired_rows(plan, 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("PathToPolish-Private-AI/\\n", encoding="utf-8")
            private = root / "PathToPolish-Private-AI"
            private.mkdir()
            output = private / "voice-audition-01"
            synthetic = b"ID3" + b"x" * 180
            with patch.object(audition, "ROOT", root), \
                 patch.object(audition, "OUTPUT", output), \
                 patch.object(audition, "azure_request",
                     side_effect=[synthetic, RuntimeError("synthetic provider failure")]) as synth:
                with self.assertRaisesRegex(RuntimeError, "synthetic provider failure"):
                    audition.generate(pair, key="test-only", region="westeurope", output=output)
                self.assertEqual(synth.call_count, 2)
                report = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(len(report["clips"]), 1)
                self.assertEqual(report["status"], "synthetic_audio_unreviewed")
                self.assertFalse((output / "manifest.json.tmp").exists())
                self.assertEqual(len(verified_clips(report, plan["audition"], output)), 1)
                page = write_player(output, plan["audition"],
                                    [{"id": v["id"], "label": v["id"]} for v in plan["voices"]])
                html = page.read_text(encoding="utf-8")
                self.assertEqual(html.count("<audio controls"), 1)
                self.assertNotIn("AgnieszkaNeural</h3>", html)
                with self.assertRaisesRegex(FileExistsError, "will not be overwritten"):
                    audition.generate(pair, key="test-only", region="westeurope", output=output)
                self.assertEqual(synth.call_count, 2)

    def test_ssml_escapes_text_and_selects_exact_polish_voice(self):
        row = self.make_plan()["audition"][0]
        row["polish"] = "Dzień <dobry> & cześć"
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, n): return b"ID3" + b"\0" * 110
        captured = []
        def fake_open(request, timeout):
            captured.append((request, timeout))
            return Response()
        with patch.object(audition, "urlopen", side_effect=fake_open):
            self.assertEqual(audition.azure_request(row, "secret", "germanywestcentral")[:3], b"ID3")
        self.assertIn(b"&lt;dobry&gt; &amp; cze\xc5\x9b\xc4\x87", captured[0][0].data)
        self.assertIn(b'pl-PL-MarekNeural', captured[0][0].data)
        self.assertEqual(captured[0][1], 25)
        self.assertEqual(captured[0][0].get_method(), "POST")
        with self.assertRaises(ValueError):
            audition.azure_request(row, "secret", "https://bad.example/")


if __name__ == "__main__":
    unittest.main()
