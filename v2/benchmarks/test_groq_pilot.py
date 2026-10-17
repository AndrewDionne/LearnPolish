import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array

from groq_pilot import prepare, run, transcribe, MODELS


class GroqPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wave = self.root / "adult-test.wav"
        with wave.open(str(self.wave), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(array("h", [1000] * 16000).tobytes())
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps([{
            "id": "test-a", "audio": self.wave.name, "reference": "cześć"
        }]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_preview_never_calls_network_or_needs_key(self):
        def unexpected(*_):
            raise AssertionError("Preview must not contact any model")
        result = run(self.manifest, MODELS, transcriber=unexpected)
        self.assertEqual(result["planned_requests"], 2)
        self.assertEqual(result["estimated_billed_seconds"], 20)
        self.assertEqual(result["network_requests_performed"], 0)

    def test_requires_both_flags_and_secret_before_any_upload(self):
        observed = []
        def fake(*args):
            observed.append(args)
            return "cześć"
        with self.assertRaisesRegex(ValueError, "BOTH"):
            run(self.manifest, MODELS, send=True, api_key="dummy",
                output=self.root/"unused.jsonl", transcriber=fake)
        with self.assertRaisesRegex(ValueError, "GROQ_API_KEY"):
            run(self.manifest, MODELS, send=True,
                approve_voice_upload=True, confirm_free_plan=True,
                output=self.root/"unused.jsonl", transcriber=fake)
        self.assertEqual(observed, [])
        self.assertFalse((self.root/"unused.jsonl").exists())

    def test_budgets_are_checked_before_network(self):
        calls = []
        def fake(*args):
            calls.append(args)
            return "tak"
        with self.assertRaisesRegex(ValueError, "hard cap"):
            run(self.manifest, MODELS, max_requests=1, send=True,
                approve_voice_upload=True, confirm_free_plan=True,
                api_key="dummy", output=self.root/"unused.jsonl",
                transcriber=fake)
        with self.assertRaisesRegex(ValueError, "Billed-audio"):
            run(self.manifest, MODELS, max_billed_seconds=10, send=True,
                approve_voice_upload=True, confirm_free_plan=True,
                api_key="dummy", output=self.root/"unused.jsonl",
                transcriber=fake)
        self.assertEqual(calls, [])

    def test_both_models_share_exact_wav_and_outputs_omit_key_and_grades(self):
        seen = []
        def fake(audio, model, key):
            self.assertEqual(key, "do-not-log-this-secret")
            self.assertEqual(audio.read_bytes(), self.wave.read_bytes())
            seen.append(model)
            return "cześć" if model == "whisper-large-v3" else "część"
        output = self.root / "transcripts.jsonl"
        summary = run(self.manifest, MODELS, send=True,
            approve_voice_upload=True, confirm_free_plan=True,
            api_key="do-not-log-this-secret", output=output, transcriber=fake)
        self.assertEqual(seen, list(MODELS))
        self.assertEqual(summary["network_requests_performed"], 2)
        rows = [json.loads(x) for x in output.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["audio_sha256"], rows[1]["audio_sha256"])
        self.assertEqual([x["recognized_expected_words"] for x in rows], [True, False])
        self.assertEqual([x["pronunciation_score"] for x in rows], [None, None])
        self.assertNotIn("do-not-log-this-secret", output.read_text())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(ValueError, "already exists"):
            run(self.manifest, MODELS, send=True,
                approve_voice_upload=True, confirm_free_plan=True,
                api_key="dummy", output=output, transcriber=fake)

    def test_rejects_changed_wav_and_different_models(self):
        import hashlib
        rows = json.loads(self.manifest.read_text())
        rows[0]["audio_sha256"] = "a" * 64
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "Recording changed"):
            prepare(self.manifest, MODELS, 4, 40)
        with self.assertRaisesRegex(ValueError, "distinct supported"):
            prepare(self.manifest, ("whisper-large-v3",)*2, 4, 40)

    def test_http_body_contains_polish_language_and_both_model_names(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                return b'{"text":"dzień dobry"}'
        def fake_urlopen(request, timeout):
            self.assertEqual(timeout, 45)
            self.assertIn("/audio/transcriptions", request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer dummy")
            self.assertIn(b'name="language"\r\n\r\npl', request.data)
            self.assertIn(b'name="model"\r\n\r\nwhisper-large-v3-turbo', request.data)
            self.assertIn(b'name="file"; filename="recording.wav"', request.data)
            return FakeResponse()
        self.assertEqual(transcribe(self.wave,"whisper-large-v3-turbo","dummy",opener=fake_urlopen),
                         "dzień dobry")


if __name__ == "__main__":
    unittest.main()
