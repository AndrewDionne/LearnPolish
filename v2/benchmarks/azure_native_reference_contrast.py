#!/usr/bin/env python3
"""Bounded native Polish WRONG-TARGET control, paired to an existing Azure success.

Use the already validated public Dzień dobry WAV. Positive control is its
previously saved Azure assessment against Dzień dobry; negative control
tests the SAME WAV against the intentionally incorrect Dobry wieczór prompt.

No AI calls by default, no Groq ever. A word substitution control is NOT
evidence of detecting Polish sound-level learner pronunciation mistakes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat
import time
from typing import Callable

from azure_pilot import azure_scripted_assess
from public_three_model_pilot import (
    AZURE_REGION, azure_evidence, checked_public_clips,
)
from three_model_pilot import _output

SOURCE_ID = "greeting-day"
SPOKEN = "Dzień dobry"
WRONG_PROMPT = "Dobry wieczór"
METRICS = ("AccuracyScore", "FluencyScore", "CompletenessScore")
MAX_PRIVATE_JSON_BYTES = 2_000_000


def read_one_private_jsonl(folder: Path, path: Path) -> dict:
    """Read existing private evidence, never use repo-tracked or symlinked files."""
    if (path.suffix != ".jsonl" or path.parent.resolve() != folder.resolve()
            or path.is_symlink() or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) & 0o077
            or not 10 <= path.stat().st_size <= MAX_PRIVATE_JSON_BYTES):
        raise ValueError("Evidence must be one owner-private 0600 JSONL inside the existing fixture folder")
    rows = path.read_text(encoding="utf-8").splitlines()
    if len(rows) != 1:
        raise ValueError("Contrast evaluation requires exactly one existing provider evidence row")
    data = json.loads(rows[0])
    if not isinstance(data, dict):
        raise ValueError("Malformed private provider evidence")
    return data


def checked_score_values(row: dict) -> dict[str, float]:
    native = row.get("azure_native")
    scores = native.get("scores") if isinstance(native, dict) else None
    if not isinstance(scores, dict):
        raise ValueError("No real Azure score evidence in existing result")
    result: dict[str, float] = {}
    for name in METRICS:
        score = scores.get(name)
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Missing or invalid actual Azure score " + name)
        result[name] = float(score)
    return result


def validate_evidence(row: dict, clip: dict, *, negative: bool) -> dict[str, float] | None:
    target = WRONG_PROMPT if negative else SPOKEN
    expected_id = SOURCE_ID + "-wrong-target" if negative else SOURCE_ID
    if (row.get("sample_id") != expected_id or
            row.get("reference") != target or
            row.get("audio_sha256") != clip["sha256"] or
            row.get("engine") != "azure-pl-PL-scripted" or
            row.get("status") not in ("ok", "inconclusive") or
            row.get("source_public_native") is not True or
            row.get("assessment_is_human_calibrated") is not False):
        raise ValueError("Reference-control result is not bound to the exact original audio and reference")
    if row["status"] == "inconclusive":
        if not negative:
            raise ValueError("Existing positive baseline has no usable Azure score")
        return None
    # The SDK can recognize speech without providing assessment fields. Keep
    # its private evidence even when it cannot produce all three metrics:
    # never erase a consumed provider call or invent a zero score.
    native = row.get("azure_native")
    if negative and (
        not isinstance(native, dict) or native.get("status") != "ok"
        or not isinstance(native.get("scores"), dict)
        or any(name not in native["scores"] for name in METRICS)
    ):
        return None
    return checked_score_values(row)


def source_and_baseline(folder: Path, positive: Path) -> tuple[dict, dict[str, float]]:
    candidates = checked_public_clips(folder)
    clip = next(c for c in candidates if c["id"] == SOURCE_ID)
    if clip["reference"] != SPOKEN:
        raise ValueError("Authoritative spoken Polish control has changed")
    positive_row = read_one_private_jsonl(folder, positive)
    values = validate_evidence(positive_row, clip, negative=False)
    if values is None:
        raise ValueError("Previous Azure success is missing the 3 measured scores")
    return clip, values


def compare(folder: Path, baseline_path: Path, negative_path: Path) -> dict:
    clip, positive = source_and_baseline(folder, baseline_path)
    negative_row = read_one_private_jsonl(folder, negative_path)
    negative = validate_evidence(negative_row, clip, negative=True)
    delta = {
        name: round(positive[name] - negative[name], 2)
        for name in METRICS
    } if negative is not None else None
    return {
        "status": "PAIRED_WRONG_TARGET_CONTROL_REVIEW",
        "sample_id": SOURCE_ID,
        "actual_spoken_polish": SPOKEN,
        "original_reference": SPOKEN,
        "deliberately_wrong_reference": WRONG_PROMPT,
        "original_wav_sha256": clip["sha256"],
        "same_audio_confirmed": True,
        "positive_raw_scores_uncalibrated": positive,
        "wrong_target_raw_scores_uncalibrated": negative,
        "positive_minus_wrong_target": delta,
        "wrong_target_result": ("returned_scores" if negative is not None else
            "inconclusive" if negative_row["status"] == "inconclusive"
            else "recognized_but_no_usable_scores"),
        "grading_verified": False,
        "phoneme_diagnosis_verified": False,
        "interpretation": (
            "A full wrong phrase is not the same as a learner mispronouncing a Polish phoneme. "
            "A successful distinction here only justifies proceeding to human-labeled adult learner recordings. "
            "A null wrong-target score is inconclusive, not an automatically correct rejection."
        ),
    }


def run(folder: Path, baseline_path: Path, *, send: bool = False,
        approve_public_audio_upload: bool = False,
        confirm_azure_f0: bool = False, confirm_no_paid_billing: bool = False,
        output: Path | None = None, azure_key: str | None = None,
        azure_region: str | None = None, assessor: Callable | None = None) -> dict:
    clip, positive = source_and_baseline(folder, baseline_path)
    plan = {
        "status": "PREVIEW_ONLY" if not send else "RUNNING",
        "audio": SOURCE_ID, "actual_spoken_polish": SPOKEN,
        "positive_reference": SPOKEN, "negative_reference": WRONG_PROMPT,
        "same_audio_sha256": clip["sha256"],
        "positive_raw_scores_uncalibrated": positive,
        "planned_azure_requests": 1, "planned_groq_requests": 0,
        "network_requests_performed": 0,
        "limitation": "Wrong phrase, NOT subtle learner mispronunciation",
    }
    if not send:
        return plan
    if not (approve_public_audio_upload and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("One Azure request needs explicit public audio upload, F0/free and no-paid authorization")
    if (not azure_key or not azure_key.isascii() or not azure_key.isprintable() or
            azure_key != azure_key.strip() or "\u2026" in azure_key or
            azure_region != AZURE_REGION):
        raise ValueError("Use validated existing private Azure Speech F0 key and germanywestcentral region")
    if output is None or output.resolve() == baseline_path.resolve():
        raise ValueError("Choose a NEW independent 0600 private JSONL output filename")
    if assessor is None:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except ImportError:
            raise RuntimeError("Azure Speech SDK unavailable in this local Python environment") from None
        assessor = azure_scripted_assess
    with _output(output, folder) as file:
        started = time.monotonic()
        response = assessor(clip["audio"], WRONG_PROMPT, azure_key, azure_region)
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        row = azure_evidence({
            "id": SOURCE_ID + "-wrong-target", "reference": WRONG_PROMPT,
            "sha256": clip["sha256"],
        }, response, latency_ms)
        row["control_condition"] = "public_native_wrong_full_phrase"
        validate_evidence(row, clip, negative=True)
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
        file.flush()
        os.fsync(file.fileno())
    return {
        "status": "WRONG_TARGET_AZURE_CONTROL_COMPLETED",
        "network_requests_performed": 1, "groq_requests_performed": 0,
        "azure_latency_ms": latency_ms,
        "comparison": compare(folder, baseline_path, output),
        "private_result_saved": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="1 opposite-phrase Azure control with existing 100/100/100 native baseline")
    p.add_argument("--fixture-dir", type=Path, required=True)
    p.add_argument("--positive-result", type=Path, required=True)
    p.add_argument("--review-result", type=Path, help="Existing negative JSONL: fully offline review, no inference")
    p.add_argument("--send", action="store_true", help="ONE actual Azure call after explicit F0 and audio-use checks")
    p.add_argument("--approve-public-audio-upload", action="store_true")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path, help="NEW private negative-control JSONL")
    args = p.parse_args()
    try:
        if args.review_result:
            if args.send or args.output:
                raise ValueError("Offline --review-result cannot be combined with --send/--output")
            report = compare(args.fixture_dir, args.positive_result, args.review_result)
        else:
            report = run(args.fixture_dir, args.positive_result,
                         send=args.send, approve_public_audio_upload=args.approve_public_audio_upload,
                         confirm_azure_f0=args.confirm_azure_f0,
                         confirm_no_paid_billing=args.confirm_no_paid_billing,
                         output=args.output, azure_key=os.getenv("AZURE_SPEECH_KEY"),
                         azure_region=os.getenv("AZURE_SPEECH_REGION"))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError, TypeError, json.JSONDecodeError) as e:
        p.error(str(e))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
