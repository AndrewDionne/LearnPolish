"""Mocked, offline tests of Azure Speech STS key check, no leaks or inference."""
import io
import json
import unittest
import urllib.error

from azure_auth_probe import HOST, URL, probe


class FakeResult:
    status = 200
    def __init__(self):
        self.read_count = 0
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, *_):
        self.read_count += 1
        raise AssertionError("Token response body MUST NEVER be read")


class AzureAuthProbeTests(unittest.TestCase):
    def test_correct_region_and_key_only_regional_token_post_no_body_read(self):
        response = FakeResult()
        requests = []
        def fake_open(req, timeout):
            requests.append(req)
            self.assertEqual(req.full_url, URL)
            self.assertEqual(req.host, HOST)
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.data, b"")
            self.assertEqual(timeout, 15)
            self.assertEqual(req.get_header("Ocp-apim-subscription-key"), "PRIVATE-NOT-TO-PRINT")
            return response

        report = probe("PRIVATE-NOT-TO-PRINT", "germanywestcentral", opener=fake_open)
        self.assertEqual(len(requests), 1)
        self.assertEqual(report["status"], "token_issuer_authorized")
        self.assertEqual(report["speech_inference_requests"], 0)
        self.assertTrue(report["no_audio_uploaded"])
        self.assertEqual(response.read_count, 0)
        self.assertNotIn("PRIVATE-NOT-TO-PRINT", json.dumps(report))

    def test_http_rejection_reports_only_allowlisted_status_not_body(self):
        def reject(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, "SECRET-MESSAGE", {},
                                         io.BytesIO(b'{"token":"SECRET","error":"private"}'))
        report = probe("PRIVATE-KEY", "germanywestcentral", opener=reject)
        self.assertEqual(report["status"], "token_issuer_rejected")
        self.assertEqual(report["http_status"], 401)
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_network_failure_omits_provider_internal_text(self):
        def fail(*_a, **_kw):
            raise urllib.error.URLError("private internal server address and key")
        report = probe("KEY", "germanywestcentral", opener=fail)
        self.assertEqual(report["status"], "connection_failed")
        self.assertNotIn("private", json.dumps(report))

    def test_non_ascii_ellipsis_placeholder_is_rejected_locally_without_network_or_secret_output(self):
        calls = []
        def unexpected(*args, **kwargs):
            calls.append("network")
            raise AssertionError("Should not reach HTTP library")
        for candidate in ("…not-a-real-key", "🔑abc", "key\nvalue",
                          "...", "[REDACTED]", " KEY ", "<KEY>"):
            with self.subTest(key_kind="placeholder/nonascii"):
                with self.assertRaisesRegex(ValueError, "AZURE_SPEECH_KEY") as err:
                    probe(candidate, "germanywestcentral", opener=unexpected)
                self.assertNotIn(candidate, str(err.exception))
                self.assertNotIn("latin-1", str(err.exception))
        self.assertEqual(calls, [])

    def test_missing_key_and_region_no_calls(self):
        calls = []
        def unexpected(*a, **kw):
            calls.append(1)
        for key, region in [("", "germanywestcentral"), ("key", "westeurope")]:
            with self.assertRaises(ValueError):
                probe(key, region, opener=unexpected)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
