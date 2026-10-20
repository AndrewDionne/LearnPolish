"""Offline security and provider tests for V2's HTTPS-only Render Free email path."""
import io
import json
import os
import unittest
from unittest.mock import patch

from recovery_mail import configured_sender


class FakeHTTP(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class HTTPSMailTests(unittest.TestCase):
    def env(self, **values):
        cleared = {key: "" for key in (
            "PTP_FAMILY_RESEND_API_KEY", "PTP_FAMILY_RESEND_FROM",
            "PTP_FAMILY_SMTP_HOST", "PTP_FAMILY_SMTP_USER",
            "PTP_FAMILY_SMTP_PASSWORD", "PTP_FAMILY_SMTP_FROM",
        )}
        cleared.update(values)
        return patch.dict(os.environ, cleared)

    def test_absent_or_partial_email_provider_fail_closed(self):
        with self.env():
            self.assertIsNone(configured_sender("verification"))
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test"):
            with self.assertRaises(RuntimeError):
                configured_sender("verification")
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test",
                      PTP_FAMILY_RESEND_FROM="parent@example.test",
                      PTP_FAMILY_SMTP_HOST="smtp.example.test"):
            with self.assertRaises(RuntimeError):
                configured_sender("recovery")
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test",
                      PTP_FAMILY_RESEND_FROM="bad\nInjected: yes"):
            with self.assertRaises(RuntimeError):
                configured_sender()

    def test_verification_uses_fixed_https_host_and_no_browser_secret(self):
        sent = []
        def send(req, timeout):
            sent.append((req, timeout))
            return FakeHTTP(json.dumps({"id": "email_test_01"}).encode())
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test_private",
                      PTP_FAMILY_RESEND_FROM="accounts@example.test"), \
             patch("recovery_mail.urllib.request.urlopen", side_effect=send):
            sender = configured_sender("verification")
            sender("learner@example.test", "one-time-private-code")
        self.assertEqual(len(sent), 1)
        request, timeout = sent[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 10)
        self.assertEqual(request.get_header("Authorization"), "Bearer re_test_private")
        body = json.loads(request.data.decode())
        self.assertEqual(body["to"], ["learner@example.test"])
        self.assertIn("30 minutes", body["text"])
        self.assertIn("one-time-private-code", body["text"])

    def test_recovery_uses_same_private_provider_and_15_minute_expiry(self):
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test_private",
                      PTP_FAMILY_RESEND_FROM="accounts@example.test"), \
             patch("recovery_mail.urllib.request.urlopen",
                   return_value=FakeHTTP(b'{"id":"email_test_02"}')) as send:
            configured_sender("recovery")("learner@example.test", "reset-token")
        body = json.loads(send.call_args.args[0].data)
        self.assertIn("15 minutes", body["text"])
        self.assertIn("reset-token", body["text"])

    def test_broken_response_never_treats_email_as_sent(self):
        with self.env(PTP_FAMILY_RESEND_API_KEY="re_test_private",
                      PTP_FAMILY_RESEND_FROM="accounts@example.test"), \
             patch("recovery_mail.urllib.request.urlopen",
                   return_value=FakeHTTP(b'{"error":"delivery_unavailable"}')):
            with self.assertRaises(RuntimeError):
                configured_sender("verification")("learner@example.test", "code")

    def test_smtp_remains_usable_only_when_configured(self):
        with self.env(PTP_FAMILY_SMTP_HOST="smtp.example.test",
                      PTP_FAMILY_SMTP_USER="sender",
                      PTP_FAMILY_SMTP_PASSWORD="private",
                      PTP_FAMILY_SMTP_FROM="sender@example.test"):
            self.assertTrue(callable(configured_sender("recovery")))
        with self.assertRaises(ValueError):
            configured_sender("unknown")


if __name__ == "__main__":
    unittest.main()
