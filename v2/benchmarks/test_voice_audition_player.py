import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import voice_audition_player as player


class VoiceAuditionPlayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.voices = [
            {"id": "pl-PL-ZofiaNeural", "label": "Zofia"},
            {"id": "pl-PL-MarekNeural", "label": "Marek"},
            {"id": "pl-PL-AgnieszkaNeural", "label": "Agnieszka"},
        ]
        self.text = "Dzień dobry"
        self.planned = []
        self.clips = []
        for v in self.voices:
            voice_id = v["id"]
            filename = f"{voice_id}/Conversation_1_0.mp3"
            audio = b"ID3" + voice_id.encode("ascii") + b"\0" * 128
            dest = self.output / filename
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(audio)
            original = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
            entry = {"itemId": "Conversation_1:0", "polish": self.text,
                     "voiceId": voice_id, "textSha256": original,
                     "suggestedLocalFilename": filename}
            self.planned.append(entry)
            self.clips.append({
                "itemId": entry["itemId"], "polish": entry["polish"],
                "voiceId": voice_id, "textSha256": original,
                "audioPath": filename, "audioSha256": hashlib.sha256(audio).hexdigest(),
                "audioBytes": len(audio),
                "reviewStatus": "needs_native_speaker_listening_review",
            })

    def save_manifest(self, clips=None):
        report = {"schemaVersion": 1, "status": "synthetic_audio_unreviewed",
                  "clips": self.clips if clips is None else clips}
        (self.output / "manifest.json").write_text(json.dumps(report), encoding="utf-8")
        return report

    def test_real_verified_samples_render_audio_controls_and_no_external_assets(self):
        report = self.save_manifest()
        verified = player.verified_clips(report, self.planned, self.output)
        html = player.render_player(verified, self.planned, self.voices)
        self.assertIn('lang="pl">Dzień dobry', html)
        self.assertEqual(html.count("<audio controls"), 3)
        self.assertEqual(html.count("Not generated"), 0)
        self.assertIn("Zofia", html)
        self.assertIn("Marek", html)
        self.assertIn("Agnieszka", html)
        self.assertIn("default-src 'none'", html)
        self.assertNotIn("<script", html)
        path = player.write_player(self.output, self.planned, self.voices)
        self.assertTrue(path.is_file())
        with self.assertRaises(FileExistsError):
            player.write_player(self.output, self.planned, self.voices)

    def test_partial_generation_never_displays_unavailable_play_button(self):
        report = self.save_manifest(self.clips[:2])
        verified = player.verified_clips(report, self.planned, self.output)
        html = player.render_player(verified, self.planned, self.voices)
        self.assertEqual(html.count("<audio controls"), 2)
        self.assertEqual(html.count("Not generated"), 1)
        self.assertIn("Agnieszka", html)

    def test_changed_bytes_and_wrong_spoken_text_fail_closed(self):
        report = self.save_manifest()
        (self.output / self.clips[0]["audioPath"]).write_bytes(b"ID3tampered")
        with self.assertRaisesRegex(ValueError, "checksum/size mismatch"):
            player.verified_clips(report, self.planned, self.output)
        # Restore audio for subsequent source-check tests.
        self.setUp_restore_first()
        bad = self.save_manifest()
        bad["clips"][0]["polish"] = "Cześć"
        with self.assertRaisesRegex(ValueError, "Unsafe, stale or mismatched"):
            player.verified_clips(bad, self.planned, self.output)

    def setUp_restore_first(self):
        voice_id = self.voices[0]["id"]
        (self.output / self.clips[0]["audioPath"]).write_bytes(
            b"ID3" + voice_id.encode("ascii") + b"\0" * 128)

    def test_missing_and_symlinked_audio_fails(self):
        report = self.save_manifest()
        file = self.output / self.clips[0]["audioPath"]
        file.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or symlinked"):
            player.verified_clips(report, self.planned, self.output)
        file.symlink_to(self.output / self.clips[1]["audioPath"])
        with self.assertRaisesRegex(ValueError, "Missing or symlinked"):
            player.verified_clips(report, self.planned, self.output)

    def test_no_audio_cannot_generate_placeholder_player(self):
        with self.assertRaisesRegex(ValueError, "No private voice-audition manifest"):
            player.write_player(self.output, self.planned, self.voices)
        report = self.save_manifest([])
        with self.assertRaisesRegex(ValueError, "No generated clips"):
            player.verified_clips(report, self.planned, self.output)


if __name__ == "__main__":
    unittest.main()
