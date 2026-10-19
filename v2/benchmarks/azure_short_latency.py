#!/usr/bin/env python3
"""Measure 2 or 4 real Azure scripted Polish short-phrase response times.

Owner-Mac only, zero provider calls by default, existing SHA-locked public
native WAVs, zero Groq, no retries, private append-as-you-go evidence.

This measures the Python SDK recognize_once wall time (connection + streamed
file + Azure processing + response). It is NOT the full browser-to-user
latency, nor an isolated network/server latency metric.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat
import statistics
import sys
import time
from typing import Callable

from azure_pilot import azure_scripted_assess
from public_three_model_pilot import AZURE_REGION, azure_evidence, checked_public_clips
from three_model_pilot import _output

MAX_REQUESTS = 4
MAX_FILE_BYTES = 200_000
SAMPLE_ORDER = ("greeting-day", "greeting-evening") * 2
SCORE_NAMES = ("AccuracyScore", "FluencyScore", "CompletenessScore")


def scheduled_clips(folder: Path, count: int) -> list[dict]:
    if type(count) is not int or count not in (2, 4):
        raise ValueError("Use exactly 2 or 4 Azure-only short-phrase requests")
    clips = checked_public_clips(folder)
    by_id = {clip["id"]: clip for clip in clips}
    if set(by_id) != {"greeting-day", "greeting-evening"}:
        raise ValueError("Only the two pinned Polish native clips are allowed")
    return [by_id[sid] for sid in SAMPLE_ORDER[:count]]


def plan(folder: Path, *, count: int = 4) -> dict:
    clips = scheduled_clips(folder, count)
    return {
        "status": "PREVIEW_ONLY",
        "purpose": "short_Polish_reference_latency_NOT_pronunciation_calibration",
        "request_order": [
            {"attempt": i, "sample_id": clip["id"], "reference": clip["reference"],
             "audio_sha256": clip["sha256"], "audio_seconds": round(clip["seconds"], 3)}
            for i, clip in enumerate(clips, 1)
        ],
        "planned_azure_requests": len(clips),
        "planned_groq_requests": 0,
        "planned_azure_audio_seconds": round(sum(c["seconds"] for c in clips), 3),
        "network_requests_performed": 0,
        "measurement": "monotonic wall clock per recognize_once via a newly constructed SpeechRecognizer",
        "existing_20s_wrong_reference_result_not_in_new_stats": True,
        "caution": "These are a few real provider calls once approved, not artificial response-time simulation or statistical p95",
    }


def clean_scores(native: object) -> dict[str, float] | None:
    if not isinstance(native, dict) or not isinstance(native.get("scores"), dict):
        return None
    values = native["scores"]
    if any(type(values.get(k)) not in (int, float) or
           not math.isfinite(values[k]) or not 0 <= values[k] <= 100 for k in SCORE_NAMES):
        return None
    return {key: float(values[key]) for key in SCORE_NAMES}


def row_for_response(clip: dict, attempt: int, elapsed_ms: float, payload: dict) -> dict:
    evidence = azure_evidence(clip, payload, elapsed_ms)
    scores = clean_scores(evidence["azure_native"])
    status = evidence["status"]
    if status == "ok" and scores is None:
        status = "unscored"
    return {
        "schema": "azure-public-native-latency-v1",
        "attempt": attempt,
        "sample_id": clip["id"], "reference": clip["reference"],
        "audio_sha256": clip["sha256"], "audio_seconds": round(clip["seconds"], 3),
        "engine": "azure-pl-PL-scripted", "status": status,
        "sdk_wall_latency_ms": elapsed_ms,
        "raw_scores_uncalibrated": scores,
        "azure_diagnostic": evidence["azure_diagnostic"],
    }


def _safe_evidence(folder: Path, output: Path) -> list[dict]:
    if (output.parent.resolve() != folder.resolve() or output.suffix != ".jsonl"
            or output.is_symlink() or not output.is_file()
            or stat.S_IMODE(output.stat().st_mode) & 0o077
            or not 8 <= output.stat().st_size <= MAX_FILE_BYTES):
        raise ValueError("Choose the actual owner-private mode-0600 JSONL in the validated fixture folder")
    lines = output.read_text(encoding="utf-8").splitlines()
    if not 1 <= len(lines) <= MAX_REQUESTS:
        raise ValueError("Only 1–4 saved request evidence rows can be reviewed")
    return [json.loads(line) for line in lines]


def report(folder: Path, output: Path, *, count: int | None = None) -> dict:
    """Offline summary; never calls Azure; never mixes canceled and valid times."""
    clips = scheduled_clips(folder, 4)
    by_id = {x["id"]: x for x in clips}
    rows = _safe_evidence(folder, output)
    planned = rows[0].get("planned_requests")
    if type(planned) is not int or planned not in (2, 4) or len(rows) > planned:
        raise ValueError("Missing or invalid original request budget in saved results")
    if count is not None and count != planned:
        raise ValueError("Inconsistent original request budget")
    expected_order = SAMPLE_ORDER[:planned]
    for i, row in enumerate(rows):
        expected = by_id[expected_order[i]]
        if (not isinstance(row, dict) or row.get("schema") != "azure-public-native-latency-v1"
                or row.get("attempt") != i + 1 or row.get("planned_requests") != planned
                or row.get("sample_id") != expected["id"]
                or row.get("reference") != expected["reference"]
                or row.get("audio_sha256") != expected["sha256"]
                or row.get("engine") != "azure-pl-PL-scripted"
                or row.get("status") not in ("ok", "inconclusive", "unscored", "error")
                or type(row.get("sdk_wall_latency_ms")) not in (int, float)
                or not math.isfinite(row["sdk_wall_latency_ms"])
                or row["sdk_wall_latency_ms"] < 0):
            raise ValueError("Saved latency evidence is invalid or mismatched to original Polish audio")
    scored = [r["sdk_wall_latency_ms"] for r in rows if r["status"] == "ok"]
    completed = [r["sdk_wall_latency_ms"] for r in rows]
    outcomes = {
        "successful_scored_requests": len(scored),
        "unscored_or_inconclusive_or_failed": len(rows) - len(scored),
        "all_attempts_median_ms": round(statistics.median(completed), 1),
        "all_attempts_max_ms": round(max(completed), 1),
        "successful_scored_median_ms": round(statistics.median(scored), 1) if scored else None,
        "successful_scored_max_ms": round(max(scored), 1) if scored else None,
        "attempts_at_or_above_5000ms": sum(v >= 5000 for v in completed),
        "attempts_at_or_above_10000ms": sum(v >= 10000 for v in completed),
        "attempts_at_or_above_20000ms": sum(v >= 20000 for v in completed),
        "all_attempts_under_5000ms": all(v < 5000 for v in completed),
    }
    return {
        "status": "AZURE_LATENCY_PARTIAL" if len(rows) != planned
                  else "AZURE_LATENCY_OBSERVED",
        "network_requests_performed_in_file": len(rows),
        "groq_requests_performed": 0,
        "original_wav_sha256_match": True,
        "observations": [
            {key: r[key] for key in (
                "attempt", "sample_id", "audio_seconds", "status",
                "sdk_wall_latency_ms", "raw_scores_uncalibrated", "azure_diagnostic"
            )} for r in rows
        ],
        "performance": outcomes,
        "decision": (
            "Any repeated >=10s latency is a practical warning; >=20s is a UX deal-breaker. "
            "With 2–4 requests, neither a clean sample nor a slow sample estimates true "
            "production frequency or p95. Check actual app round-trip separately."
        ),
        "private_source_unmodified": True,
    }


def run(folder: Path, *, count: int = 4, send: bool = False,
        approve_public_audio_upload: bool = False,
        confirm_azure_f0: bool = False, confirm_no_paid_billing: bool = False,
        output: Path | None = None, azure_key: str | None = None,
        azure_region: str | None = None,
        assessor: Callable | None = None,
        clock: Callable[[], float] = time.monotonic) -> dict:
    clips = scheduled_clips(folder, count)
    if not send:
        return plan(folder, count=count)
    if not (approve_public_audio_upload and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("Azure F0/free, no-paid-billing, public-upload approval are required for a live latency run")
    if (not azure_key or not azure_key.isascii() or not azure_key.isprintable() or
            azure_key != azure_key.strip() or "\u2026" in azure_key
            or azure_region != AZURE_REGION):
        raise ValueError("Use existing owner-private Azure Speech key in its actual germanywestcentral region")
    if output is None:
        raise ValueError("Specify a NEW never-used owner-private JSONL filename")
    if assessor is None:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except ImportError:
            raise RuntimeError("Install local Azure Speech SDK into existing private Python environment") from None
        assessor = azure_scripted_assess
    with _output(output, folder) as stream:
        for i, clip in enumerate(clips, 1):
            started = clock()
            try:
                assessed = assessor(clip["audio"], clip["reference"], azure_key, azure_region)
                elapsed_ms = round((clock() - started) * 1000, 1)
                row = row_for_response(clip, i, elapsed_ms, assessed)
                row["planned_requests"] = count
            except Exception:
                # Never echo SDK exception text/headers/session/key. Persist the
                # time for the attempted call, then stop WITHOUT a retry.
                elapsed_ms = round(max(0, clock() - started) * 1000, 1)
                row = {
                    "schema": "azure-public-native-latency-v1",
                    "attempt": i, "planned_requests": count,
                    "sample_id": clip["id"], "reference": clip["reference"],
                    "audio_sha256": clip["sha256"], "audio_seconds": round(clip["seconds"], 3),
                    "engine": "azure-pl-PL-scripted", "status": "error",
                    "sdk_wall_latency_ms": elapsed_ms,
                    "raw_scores_uncalibrated": None, "azure_diagnostic": None,
                }
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                print("Azure %d/%d: %s ERROR in %.1f ms" % (i, count, clip["id"], elapsed_ms), file=sys.stderr, flush=True)
                break
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            print("Azure %d/%d: %s %s in %.1f ms" % (i, count, clip["id"], row["status"], elapsed_ms), file=sys.stderr, flush=True)
    return report(folder, output, count=count)


def main() -> int:
    p = argparse.ArgumentParser(description="Up to four real Azure pl-PL latency samples, zero calls by default")
    p.add_argument("--fixture-dir", type=Path, required=True)
    p.add_argument("--count", type=int, default=4, choices=(2, 4))
    p.add_argument("--send", action="store_true", help="Opt in to at most --count Azure requests")
    p.add_argument("--approve-public-audio-upload", action="store_true")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path, help="New owner-private JSONL for actual calls")
    p.add_argument("--summarize", type=Path, help="Read existing evidence offline without Azure calls")
    args = p.parse_args()
    try:
        if args.summarize:
            if args.send or args.output:
                raise ValueError("--summarize is offline and cannot be combined with --send/--output")
            result = report(args.fixture_dir, args.summarize)
        else:
            result = run(args.fixture_dir, count=args.count, send=args.send,
                         approve_public_audio_upload=args.approve_public_audio_upload,
                         confirm_azure_f0=args.confirm_azure_f0,
                         confirm_no_paid_billing=args.confirm_no_paid_billing,
                         output=args.output, azure_key=os.getenv("AZURE_SPEECH_KEY"),
                         azure_region=os.getenv("AZURE_SPEECH_REGION"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
