"""No-network tests of Groq curl transport on the owner's macOS workflow."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from groq_curl_transport import request_json
from groq_pilot import check_access, transcribe, run, MODELS


class GroqCurlTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audio = self.root / "polish audio.wav"
        self.audio.write_bytes(b"RIFF fake for transport tests")
        self.calls = []
        self.key = "gsk_PRIVATE_TEST_NEVER_ECHO"

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, args, **kw):
        self.calls.append((args, kw))
        self.assertEqual(args[0:2], ["curl", "-q"])
        self.assertEqual(args.count("--config"), 1)
        self.assertIn("--silent", args)
        self.assertIn("--max-redirs", args)
        self.assertNotIn("--location", args)
        self.assertNotIn("--retry", args)
        self.assertNotIn("--verbose", args)
        self.assertTrue(kw["capture_output"])
        self.assertFalse(kw["check"])
        self.assertNotIn(self.key, " ".join(args))
        self.assertIn(b"Authorization: Bearer " + self.key.encode(), kw["input"])
        return subprocess.CompletedProcess(args, 0, self.success_body, b"")

    def test_curl_read_only_get_models_has_no_audio(self):
        self.success_body = json.dumps({"data": [{"id": MODELS[0]}, {"id": MODELS[1]}]}).encode() + b"\n200"
        result = check_access(self.key, transport="curl", curl_runner=self.fake)
        self.assertEqual(result["models_listed"], {x: True for x in MODELS})
        args = self.calls[0][0]
        self.assertEqual(args[-1], "https://api.groq.com/openai/v1/models")
        self.assertEqual(args[args.index("--request") + 1], "GET")
        self.assertNotIn("--form", args)
        self.assertTrue(result["no_audio_sent"])

    def test_curl_post_uses_exact_local_audio_and_polish(self):
        self.success_body = b'{"text":"czapka"}\n200'
        self.assertEqual(transcribe(self.audio, MODELS[0], self.key,
                                    transport="curl", curl_runner=self.fake), "czapka")
        args = self.calls[0][0]
        self.assertEqual(args[-1], "https://api.groq.com/openai/v1/audio/transcriptions")
        self.assertEqual(args[args.index("--request") + 1], "POST")
        fields = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "--form"]
        self.assertIn("model=whisper-large-v3", fields)
        self.assertIn("language=pl", fields)
        self.assertIn("response_format=json", fields)
        self.assertIn("temperature=0", fields)
        self.assertIn("file=@" + str(self.audio) + ";filename=recording.wav;type=audio/wav", fields)
        self.assertEqual(len(self.calls), 1)

    def test_denied_curl_response_is_safe_no_raw_body(self):
        self.success_body = b'{"error":{"code":"model_permission_blocked_org","message":"API key leaked from provider: gsk_SOME_SECRET"}}\n403'
        with self.assertRaisesRegex(RuntimeError, "model_permission_blocked_org") as caught:
            transcribe(self.audio, MODELS[0], self.key,
                       transport="curl", curl_runner=self.fake)
        self.assertNotIn("gsk_SOME_SECRET", str(caught.exception))
        self.assertNotIn(self.key, str(caught.exception))

    def test_non_json_waf_403_is_reported_without_echoing_html(self):
        self.success_body = b'<html>WAF denied: SECRET_TOKEN</html>\n403'
        with self.assertRaisesRegex(RuntimeError, "HTTP 403") as caught:
            check_access(self.key, transport="curl", curl_runner=self.fake)
        self.assertNotIn("SECRET_TOKEN", str(caught.exception))

    def test_rejects_untrusted_key_url_and_model_without_network(self):
        bad = ["x\nheader = \"X: leak\"", "x\"\nurl=https://bad", "", "x y"]
        for key in bad:
            with self.assertRaisesRegex(ValueError, "normal API key"):
                request_json("https://api.groq.com/openai/v1/models", key, runner=self.fake)
        with self.assertRaisesRegex(ValueError, "documented Groq"):
            request_json("https://evil.example/models", self.key, runner=self.fake)
        with self.assertRaisesRegex(ValueError, "approved Whisper"):
            request_json("https://api.groq.com/openai/v1/audio/transcriptions",
                         self.key, audio=self.audio, model="unapproved", runner=self.fake)
        self.assertEqual(self.calls, [])

    def test_transport_failure_redacts_stderr(self):
        def denied(args, **kw):
            return subprocess.CompletedProcess(args, 7, b"", b"SECRET_TOKEN")
        with self.assertRaisesRegex(RuntimeError, "transport failed") as caught:
            request_json("https://api.groq.com/openai/v1/models", self.key, runner=denied)
        self.assertNotIn("SECRET_TOKEN", str(caught.exception))

    def test_even_preview_curl_transport_does_not_send(self):
        import json
        import wave
        from array import array
        wav = self.root / "normal.wav"
        with wave.open(str(wav), "wb") as fd:
            fd.setnchannels(1)
            fd.setsampwidth(2)
            fd.setframerate(16000)
            fd.writeframes(array("h", [1000] * 16000).tobytes())
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps([{
            "id": "test-curl", "audio": wav.name, "reference": "czapka"
        }]), encoding="utf-8")
        result = run(manifest, MODELS, transport="curl", send=False)
        self.assertEqual(result["planned_requests"], 2)
        self.assertEqual(result["network_requests_performed"], 0)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
