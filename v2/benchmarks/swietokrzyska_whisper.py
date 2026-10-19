#!/usr/bin/env python3
"""Groq Whisper v3/Turbo on the SAME adult Świętokrzyska WAV already assessed by Azure.

Zero inference by default; the original two-call Azure result is read only.
On explicit opt-in, two Groq-only transcriptions at most, no retries, no
Azure SDK calls, no audio manipulation, private append-per-attempt evidence.
This compares transcription/WER and service turnaround, NEVER pronunciation
grading. One word gives WER only 0 or 1; do not infer phoneme accuracy.
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

from groq_pilot import MODELS, transcribe
from groq_env import groq_key
from swietokrzyska_latency import ITEM_ID, WORD, checked_audio, summary as azure_summary
from three_model_pilot import _output, word_error_rate

ENGINE = "groq-"
SCHEMA = "ptp-swietokrzyska-whisper-v1"
MAX_ROWS = 2
MAX_OUTPUT_BYTES = 5000


def preview(wav: Path, azure_result: Path) -> dict:
    clip = checked_audio(wav)
    previous = azure_summary(wav, azure_result)
    if previous["status"] != "PAIRED_RESULT" or any(
        attempt["status"] != "ok" for attempt in previous["observations"]
    ):
        raise ValueError("Existing Azure evidence must contain BOTH successful paired assessments")
    if clip["wav_sha256"] != previous["audio_sha256"]:
        raise ValueError("Original adult WAV does not match the previously saved Azure assessment")
    return {
        "status": "PREVIEW_ONLY",
        "reference": WORD,
        "sample_id": ITEM_ID,
        "audio_sha256": clip["wav_sha256"],
        "audio_seconds": clip["wav_seconds"],
        "existing_azure_saved_requests": 2,
        "existing_azure_raw_scores_uncalibrated": [
            {"variant": r["variant"], "scores": r["scores_uncalibrated"],
             "total_sdk_ms": r["timing_ms"]["total"]}
            for r in previous["observations"]
        ],
        "planned_groq_models": list(MODELS),
        "planned_groq_requests": 2,
        "estimated_groq_billable_audio_seconds": 20,
        "planned_new_azure_requests": 0,
        "network_requests_performed": 0,
        "caveat": "One Polish word: exact text/WER and elapsed time only. Whisper does not supply pronunciation grades.",
    }


def safe_row(variant: str, idx: int, sha: str, elapsed_ms: float, transcript: str | None) -> dict:
    if variant not in MODELS or idx not in (1, 2):
        raise ValueError("Unknown Whisper model or attempt")
    if (type(elapsed_ms) not in (float, int) or not math.isfinite(elapsed_ms)
            or not 0 <= elapsed_ms <= 120000):
        raise ValueError("Invalid wall-clock timing")
    if transcript is not None and (not isinstance(transcript, str) or len(transcript) > 500):
        raise ValueError("Invalid Whisper transcript")
    recognized = transcript.strip() if transcript is not None else None
    status = "ok" if recognized else ("inconclusive" if transcript is not None else "error")
    return {
        "schema": SCHEMA, "attempt": idx, "planned_requests": 2,
        "engine": ENGINE + variant, "sample_id": ITEM_ID,
        "reference": WORD, "audio_sha256": sha,
        "status": status, "latency_ms": round(float(elapsed_ms), 1),
        "transcript": recognized, "exact_word_match": (
            word_error_rate(WORD, recognized) == 0 if recognized else None
        ),
        "single_word_wer_transcription_only": (
            word_error_rate(WORD, recognized) if recognized else None
        ),
        "pronunciation_grade": None,
    }


def report(wav: Path, azure_result: Path, output: Path) -> dict:
    baseline = preview(wav, azure_result)
    if (output.parent.resolve() != wav.parent.resolve() or output.suffix != ".jsonl"
            or output.is_symlink() or not output.is_file()
            or stat.S_IMODE(output.stat().st_mode) & 0o077
            or not 8 <= output.stat().st_size <= MAX_OUTPUT_BYTES):
        raise ValueError("Select the original owner-private saved Groq JSONL next to the adult WAV")
    try:
        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    except (UnicodeError, OSError, json.JSONDecodeError):
        raise ValueError("Saved private Whisper result is invalid") from None
    if not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("Only one or two saved Whisper attempts may be reviewed")
    for idx, row in enumerate(rows):
        if (not isinstance(row, dict) or row.get("schema") != SCHEMA
                or row.get("attempt") != idx + 1 or row.get("planned_requests") != 2
                or row.get("engine") != ENGINE + MODELS[idx]
                or row.get("sample_id") != ITEM_ID or row.get("reference") != WORD
                or row.get("audio_sha256") != baseline["audio_sha256"]
                or row.get("status") not in ("ok", "inconclusive", "error")
                or row.get("pronunciation_grade") is not None
                or type(row.get("latency_ms")) not in (float, int)
                or not math.isfinite(row["latency_ms"]) or row["latency_ms"] < 0):
            raise ValueError("Saved Whisper result differs from the authoritative adult WAV or model order")
    return {
        "status": "WHISPER_PARTIAL" if len(rows) < 2 else "WHISPER_PAIRED_RESULT",
        "reference": WORD, "same_audio_verified": True,
        "audio_sha256": baseline["audio_sha256"],
        "new_azure_requests": 0, "groq_attempts_saved": len(rows),
        "azure_baseline": baseline["existing_azure_raw_scores_uncalibrated"],
        "whisper": [{
            "model": row["engine"].removeprefix(ENGINE),
            "status": row["status"],
            "transcript": row["transcript"],
            "exact_word_match": row["exact_word_match"],
            "single_word_wer_transcription_only": row["single_word_wer_transcription_only"],
            "latency_ms": row["latency_ms"],
            "pronunciation_grade": None,
        } for row in rows],
        "interpretation": ("Whisper recognizes words and can miss diacritics or guess a target from "
                           "context; 0 word error is not evidence of correct Polish phonemes. "
                           "Azure PA 84/100/100 remains uncalibrated; no human listener labeled this word. "
                           "These isolated CLI timings are not complete app UX latency or p95."),
    }


def run(wav: Path, azure_result: Path, *, send: bool = False,
        approve_adult_audio_upload: bool = False, confirm_groq_free: bool = False,
        confirm_no_paid_billing: bool = False, groq_key: str | None = None,
        output: Path | None = None, transcriber: Callable | None = None,
        clock: Callable[[], float] = time.monotonic) -> dict:
    prior = preview(wav, azure_result)
    if not send:
        return prior
    if not (approve_adult_audio_upload and confirm_groq_free and confirm_no_paid_billing):
        raise ValueError("Groq use requires explicit adult audio upload, free plan and no paid billing approval")
    if output is None:
        raise ValueError("Choose a NEW owner-private Groq output filename")
    if output.exists() or output.is_symlink():
        raise ValueError("Existing Groq result found; preserve it and use offline --summarize")
    if not isinstance(groq_key, str) or not groq_key.isascii() or not groq_key.isprintable() or (
        not groq_key.strip() or groq_key != groq_key.strip() or "…" in groq_key
    ):
        raise ValueError("GROQ_API_KEY missing or invalid locally; do not print or share the key")
    if transcriber is None:
        transcriber = lambda path, model, key: transcribe(path, model, key, transport="curl")
    with _output(output, wav.parent) as stream:
        for i, model in enumerate(MODELS, 1):
            started = clock()
            try:
                transcript = transcriber(wav, model, groq_key)
                elapsed_ms = round(max(0.0, clock() - started) * 1000, 1)
                row = safe_row(model, i, prior["audio_sha256"], elapsed_ms, transcript)
            except Exception:
                # Never print provider exception or raw response: may contain
                # secrets, URLs, account identifiers or private voice material.
                elapsed_ms = round(max(0.0, clock() - started) * 1000, 1)
                row = safe_row(model, i, prior["audio_sha256"], elapsed_ms, None)
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            print(f"Groq {i}/2: {model} {row['status']} in {elapsed_ms:.1f} ms", flush=True)
            if row["status"] == "error":
                break
    return report(wav, azure_result, output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Same Świętokrzyska WAV vs Whisper v3 + Turbo, zero new Azure; preview only by default")
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--azure-result", type=Path, required=True, help="Existing 2-call owner-private Azure JSONL")
    parser.add_argument("--send", action="store_true", help="Opt in to exactly two Groq requests at most")
    parser.add_argument("--approve-adult-audio-upload", action="store_true")
    parser.add_argument("--confirm-groq-free", action="store_true")
    parser.add_argument("--confirm-no-paid-billing", action="store_true")
    parser.add_argument("--output", type=Path, help="NEW private Whisper evidence JSONL")
    parser.add_argument("--summarize", type=Path, help="Review existing Groq evidence with ZERO calls")
    args = parser.parse_args()
    try:
        if args.summarize:
            if args.send or args.output:
                raise ValueError("Offline summary and live request/output cannot be combined")
            result = report(args.wav, args.azure_result, args.summarize)
        else:
            result = run(args.wav, args.azure_result, send=args.send,
                approve_adult_audio_upload=args.approve_adult_audio_upload,
                confirm_groq_free=args.confirm_groq_free,
                confirm_no_paid_billing=args.confirm_no_paid_billing,
                groq_key=groq_key() if args.send else None,
                output=args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError):
        parser.error("Private WAV/Azure evidence or Groq test preflight failed. "
                     "Check file existence/0700 directory, Groq key and flags; do not automatically retry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
