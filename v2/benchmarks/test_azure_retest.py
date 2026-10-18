"""Offline Azure SDK reason diagnostic and exactly-one-call retest safeguards."""
from __future__ import annotations

import json
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace

from azure_pilot import azure_recognition_diagnostic
from benchmark import read_audio_metadata
from azure_retest import run


def mock_sdk():
    return SimpleNamespace(
        ResultReason=SimpleNamespace(NoMatch="NOMATCH", Canceled="CANCELED"),
        NoMatchReason=SimpleNamespace(NotRecognized="NOT_RECOGNIZED",
                                      InitialSilenceTimeout="SILENCE",
                                      InitialBabbleTimeout="BABBLE",
                                      EndSilenceTimeout="END_SILENCE",
                                      KeywordNotRecognized="KEYWORD"),
        CancellationReason=SimpleNamespace(Error="ERR", EndOfStream="EOF", CancelledByUser="USER"),
        CancellationErrorCode=SimpleNamespace(
            NoError="NO_ERROR", AuthenticationFailure="AUTH",
            ConnectionFailure="CONNECTION", Forbidden="FORBIDDEN",
            BadRequest="BAD", ServiceError="SERVICE", RuntimeError="RUNTIME",
            ServiceTimeout="TIMEOUT", ServiceUnavailable="UNAVAILABLE",
            TooManyRequests="LIMIT", EmbeddedModelError="MODEL",
            ServiceRedirectPermanent="REDIRECT_P", ServiceRedirectTemporary="REDIRECT_T"),
    )


class AzureReasonTests(unittest.TestCase):
    def test_no_match_records_allowlisted_reason_without_error_text(self):
        r = SimpleNamespace(reason="NOMATCH",
                            no_match_details=SimpleNamespace(reason="SILENCE", extra="private phrase"))
        out = azure_recognition_diagnostic(r, mock_sdk())
        self.assertEqual(out["azure_result_reason"], "NoMatch")
        self.assertEqual(out["azure_no_match_reason"], "InitialSilenceTimeout")
        self.assertNotIn("private", str(out))

    def test_canceled_records_auth_and_connection_without_secret_or_provider_text(self):
        for code, expected in (("AUTH", "AuthenticationFailure"), ("CONNECTION", "ConnectionFailure"),
                               ("FORBIDDEN", "Forbidden"), ("LIMIT", "TooManyRequests")):
            r = SimpleNamespace(reason="CANCELED",
                                cancellation_details=SimpleNamespace(
                                    reason="ERR", error_code=code,
                                    error_details="private key: DO-NOT-LOG, speech text here"))
            out = azure_recognition_diagnostic(r, mock_sdk())
            self.assertEqual(out["azure_result_reason"], "Canceled")
            self.assertEqual(out["azure_cancellation_reason"], "Error")
            self.assertEqual(out["azure_error_code"], expected)
            self.assertNotIn("DO-NOT-LOG", str(out))
            self.assertNotIn("speech text here", str(out))

    def test_sdk_documented_code_property_is_used_even_when_error_code_is_absent(self):
        # Reproduce actual Speech SDK CancellationDetails: the error enum
        # lives at .code; the previous implementation always returned Unknown.
        for code, expected in (("AUTH", "AuthenticationFailure"),
                               ("CONNECTION", "ConnectionFailure"),
                               ("LIMIT", "TooManyRequests"),
                               ("SERVICE", "ServiceError")):
            result = SimpleNamespace(
                reason="CANCELED",
                cancellation_details=SimpleNamespace(
                    reason="ERR", code=code,
                    error_details="do-not-log-private-key-or-speech"))
            out = azure_recognition_diagnostic(result, mock_sdk())
            self.assertEqual(out["azure_error_code"], expected)
            self.assertNotIn("do-not-log", str(out))

    def test_sdk_code_property_takes_precedence_over_legacy_error_code(self):
        result = SimpleNamespace(
            reason="CANCELED",
            cancellation_details=SimpleNamespace(
                reason="ERR", code="FORBIDDEN", error_code="AUTH",
                error_details="do-not-print"))
        out = azure_recognition_diagnostic(result, mock_sdk())
        self.assertEqual(out["azure_error_code"], "Forbidden")
        self.assertNotIn("do-not-print", str(out))

    def test_unrecognized_enum_never_serializes_untrusted_value(self):
        fake = SimpleNamespace(reason="CANCELED",
                               cancellation_details=SimpleNamespace(
                                   reason="ERROR secret", error_code="secret-key-value"))
        out = azure_recognition_diagnostic(fake, mock_sdk())
        self.assertEqual(out["azure_error_code"], "Unknown")
        self.assertEqual(out["azure_cancellation_reason"], "Unknown")
        self.assertNotIn("secret", str(out))


class AzureOnlyRetestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.wav = self.root / "fleurs-pl-val-00003.wav"
        with wave.open(str(self.wav), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(array("h", [3500] * 6 * 16000).tobytes())
        meta = read_audio_metadata(self.wav)
        self.manifest = self.root / "sentences-source.json"
        self.manifest.write_text(json.dumps([{
            "id": "fleurs-pl-val-00003", "audio": self.wav.name,
            "reference": "Amerykański prezydent wyraził pełne zadowolenie z oświadczenia.",
            "audio_sha256": meta["audio_sha256"],
            "source_dataset": "google/fleurs", "source_config": "pl_pl",
            "source_split": "validation",
            "source_license": "CC BY 4.0 — Google FLEURS (confirm third-party service use before upload)",
            "reference_verified_by_human": False,
            "provider_upload_approved": False,
        }]))
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, path, ref, key, region):
        self.calls.append((path, ref, key, region))
        return {"status": "inconclusive", "reason": "Azure canceled speech recognition",
                "azure_result_reason": "Canceled",
                "azure_cancellation_reason": "Error",
                "azure_error_code": "AuthenticationFailure"}

    def flags(self, output):
        return dict(send=True, approve_public_audio_upload=True, confirm_azure_f0=True,
                    confirm_no_paid_billing=True, key="DO-NOT-PRINT", region="germanywestcentral",
                    output=output, assessor=self.fake)

    def test_offline_preview_requires_no_key_and_no_requests(self):
        report = run(self.manifest, "fleurs-pl-val-00003")
        self.assertEqual(report["status"], "PREVIEW_ONLY")
        self.assertEqual(report["planned_azure_requests"], 1)
        self.assertEqual(report["groq_requests"], 0)
        self.assertEqual(self.calls, [])

    def test_one_azure_only_call_reports_safe_reason_and_preserves_sources(self):
        before = self.wav.read_bytes()
        manifest_before = self.manifest.read_bytes()
        output = self.root / "azure-sdk-diagnostic-01.jsonl"
        report = run(self.manifest, "fleurs-pl-val-00003", **self.flags(output))
        self.assertEqual(report["network_calls_performed"], 1)
        self.assertEqual(report["sdk_result_reason"], "Canceled")
        self.assertEqual(report["sdk_error_code"], "AuthenticationFailure")
        self.assertEqual(report["groq_requests"], 0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2], "DO-NOT-PRINT")
        data = json.loads(output.read_text())
        self.assertEqual(data["azure_error_code"], "AuthenticationFailure")
        self.assertFalse(data["human_verified"])
        self.assertIsNone(data["raw_azure_json"])
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("DO-NOT-PRINT", output.read_text())
        self.assertEqual(self.wav.read_bytes(), before)
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        with self.assertRaisesRegex(ValueError, "Output exists"):
            run(self.manifest, "fleurs-pl-val-00003", **self.flags(output))
        self.assertEqual(len(self.calls), 1)

    def test_hard_limit_flags_and_credentials_block_every_call(self):
        output = self.root / "out.jsonl"
        base = self.flags(output)
        for changed in (
            {"send": False},  # PREVIEW only
            {"approve_public_audio_upload": False},
            {"confirm_azure_f0": False},
            {"confirm_no_paid_billing": False},
            {"key": ""},
            {"region": "westeurope"},
        ):
            kw = dict(base, **changed)
            if changed.get("send") is False:
                self.assertEqual(run(self.manifest, "fleurs-pl-val-00003", **kw)["network_calls_performed"], 0)
            else:
                with self.assertRaises(ValueError):
                    run(self.manifest, "fleurs-pl-val-00003", **kw)
        with self.assertRaisesRegex(ValueError, "EXACTLY one"):
            run(self.manifest, "fleurs-pl-val-00003", max_requests=2)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            run(self.manifest, "fleurs-pl-val-00003", max_audio_seconds=5)
        self.assertEqual(self.calls, [])
        self.assertFalse(output.exists())

    def test_changed_source_hash_refuses_before_network(self):
        rows = json.loads(self.manifest.read_text())
        rows[0]["audio_sha256"] = "f" * 64
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "checksum"):
            run(self.manifest, "fleurs-pl-val-00003", **self.flags(self.root / "unused.jsonl"))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
