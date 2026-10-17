#!/usr/bin/env python3
"""Exactly one public FLEURS original WAV to Azure: narrow exploratory diagnostics.

NO Groq calls, no additional voice downloads, no native-certification claims.
No requests without explicit --send, public upload rights and F0/no-paid gates.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from azure_pilot import azure_scripted_assess
from benchmark import extract_azure_native
from three_model_pilot import choose_source, _output

REGION = "germanywestcentral"


def run(manifest: Path, sample_id: str, *, send: bool = False,
        approve_public_audio_upload: bool = False,
        confirm_azure_f0: bool = False,
        confirm_no_paid_billing: bool = False,
        max_requests: int = 1,
        max_audio_seconds: float = 10.0,
        output: Path | None = None,
        key: str | None = None,
        region: str | None = None,
        assessor: Callable = azure_scripted_assess) -> dict:
    if max_requests != 1 or not 5 <= max_audio_seconds <= 15:
        raise ValueError("Azure-only research permits EXACTLY one request, max 5–15 seconds")
    sample = choose_source(manifest, sample_ids=(sample_id,), count=1)[0]
    if sample["seconds"] > max_audio_seconds:
        raise ValueError("Selected original WAV exceeds Azure audio seconds cap")
    result = {
        "status": "PREVIEW_ONLY",
        "purpose": "azure_sdk_diagnostic_NOT_NATIVE_CERTIFICATION",
        "sample_id": sample["id"],
        "source_sha256": sample["sha256"],
        "audio_seconds": round(sample["seconds"], 3),
        "planned_azure_requests": 1,
        "network_calls_performed": 0,
        "groq_requests": 0,
        "human_verified": False,
        "azure_region": REGION,
    }
    if not send:
        return result
    if not (approve_public_audio_upload and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("Live Azure retest needs --approve-public-audio-upload --confirm-azure-f0 --confirm-no-paid-billing")
    if not key or region != REGION:
        raise ValueError("Use existing AZURE_SPEECH_KEY and AZURE_SPEECH_REGION=germanywestcentral in Mac shell")
    if output is None:
        raise ValueError("Provide a NEW private --output JSONL file; prior results cannot be overwritten")
    # SDK import is required only for a real network run. Test/review mocks use
    # an injected assessor and never need SDK or provider access.
    if assessor is azure_scripted_assess:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except ImportError:
            raise RuntimeError("Azure Speech SDK missing; run with existing private .venv-speech-test Python") from None
    with _output(output, manifest.parent) as stream:
        payload = assessor(sample["path"], sample["reference"], key, region)
        if not isinstance(payload, dict) or payload.get("status") not in ("ok", "inconclusive"):
            raise ValueError("Unrecognized Azure SDK response")
        raw = payload.get("raw_azure_json")
        native = extract_azure_native(raw) if isinstance(raw, dict) else {
            "status": "inconclusive", "reason": payload.get("reason")}
        row = {
            "id": sample["id"], "reference": sample["reference"],
            "engine": "azure-pl-PL-scripted",
            "status": payload["status"],
            "source_sha256": sample["sha256"],
            "audio_seconds": round(sample["seconds"], 3),
            "azure_result_reason": payload.get("azure_result_reason"),
            "azure_no_match_reason": payload.get("azure_no_match_reason"),
            "azure_cancellation_reason": payload.get("azure_cancellation_reason"),
            "azure_error_code": payload.get("azure_error_code"),
            "azure_native": native, "raw_azure_json": raw,
            "exploratory_only": True,
            "human_verified": False,
            "assessment_is_human_calibrated": False,
        }
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return dict(result, status=payload["status"],
                network_calls_performed=1,
                output=str(output),
                sdk_result_reason=row["azure_result_reason"],
                sdk_no_match_reason=row["azure_no_match_reason"],
                sdk_cancellation_reason=row["azure_cancellation_reason"],
                sdk_error_code=row["azure_error_code"],
                azure_scores_uncalibrated=native.get("scores"))


def main() -> int:
    p = argparse.ArgumentParser(description="Exactly ONE Azure SDK speech diagnostic on already-downloaded public Polish WAV")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--sample-id", required=True)
    p.add_argument("--max-requests", type=int, default=1)
    p.add_argument("--max-audio-seconds", type=float, default=10.0)
    p.add_argument("--send", action="store_true")
    p.add_argument("--approve-public-audio-upload", action="store_true",
                   help="I checked public FLEURS rights and permit Azure processing")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        out = run(args.manifest, args.sample_id, max_requests=args.max_requests,
                  max_audio_seconds=args.max_audio_seconds, send=args.send,
                  approve_public_audio_upload=args.approve_public_audio_upload,
                  confirm_azure_f0=args.confirm_azure_f0,
                  confirm_no_paid_billing=args.confirm_no_paid_billing,
                  output=args.output, key=os.environ.get("AZURE_SPEECH_KEY"),
                  region=os.environ.get("AZURE_SPEECH_REGION"))
    except (ValueError, RuntimeError, OSError) as exc:
        p.error(str(exc))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
