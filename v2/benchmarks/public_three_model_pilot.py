#!/usr/bin/env python3
"""Six-request public Polish native-audio bake-off: v3, Turbo and Azure.

Two pinned public-domain Wikimedia recordings from public_polish_audio.py.
Zero inference by default. --send requires explicit source/provider/free-tier
approval and keys from the owner's local environment, never GitHub. Uses
exact SAME PCM16 WAV bytes for each engine on a given recording. No retries.
Does NOT certify Polish phoneme coaching or grade a learner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time
from typing import Callable

from azure_pilot import azure_scripted_assess
from benchmark import extract_azure_native, read_audio_metadata
from groq_pilot import MODELS, transcribe
from model_fit_review import review as offline_review
from public_polish_audio import SOURCES, MAX_SOURCE_BYTES, validate_ogg
from research_paths import check_research_location
from three_model_pilot import _output, word_error_rate

AZURE_REGION = "germanywestcentral"
MAX_CALLS = 6


def checked_public_clips(folder: Path) -> list[dict]:
    check_research_location(folder / "manifest.json")
    if (folder.is_symlink() or not folder.is_dir() or
            stat.S_IMODE(folder.stat().st_mode) & 0o077):
        raise ValueError("Source folder must be an existing, owner-private non-symlink directory (chmod 700)")
    manifest = folder / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Missing original public-audio fixture manifest")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("status") != "public_reference_audio_only":
        raise ValueError("Unsupported public-audio manifest")
    rows = data.get("clips")
    if not isinstance(rows, list) or len(rows) != len(SOURCES):
        raise ValueError("Exactly two official public-domain original recordings required")
    checked = []
    for source, row in zip(SOURCES, rows):
        if not isinstance(row, dict):
            raise ValueError("Malformed source provenance")
        expected = {
            "id": source["id"], "text": source["text"],
            "original": source["id"] + ".ogg", "wav": source["id"] + ".wav",
            "source_url": source["description"], "author": source["author"],
            "license": "Public domain", "original_sha256": source["original_sha256"],
        }
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError("Public recording metadata changed; refuse upload")
        ogg = folder / expected["original"]
        wav = folder / expected["wav"]
        if any(p.is_symlink() or not p.is_file() for p in (ogg, wav)):
            raise ValueError("Original Ogg or normalized WAV missing, symlinked or replaced")
        if ogg.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("Original recording size exceeds bounded source limit")
        if validate_ogg(ogg.read_bytes()) != source["original_sha256"]:
            raise ValueError("Public Commons original SHA-256 changed")
        meta = read_audio_metadata(wav)
        if (meta["audio_sha256"] != row.get("wav_sha256") or
                not meta["valid_signal"] or not 0.6 <= meta["seconds"] <= 10 or
                not isinstance(row.get("seconds"), (int, float)) or
                not math.isfinite(row["seconds"]) or
                abs(meta["seconds"] - row["seconds"]) >= .001):
            raise ValueError("Normalized WAV hash, duration or signal changed")
        checked.append({"id": row["id"], "reference": row["text"], "audio": wav,
                        "sha256": meta["audio_sha256"], "seconds": meta["seconds"],
                        "source_url": source["description"]})
    if sum(c["seconds"] for c in checked) > 5:
        raise ValueError("These short public reference clips unexpectedly exceed five seconds total")
    return checked


def preview(folder: Path) -> dict:
    clips = checked_public_clips(folder)
    return {
        "status": "PREVIEW_ONLY", "purpose": "public_native_reference_engine_smoke_NOT_LEARNER_GRADING",
        "clips": [{"id": c["id"], "reference": c["reference"],
                   "audio_sha256": c["sha256"], "audio_seconds": round(c["seconds"], 3),
                   "source_url": c["source_url"]} for c in clips],
        "models": [*MODELS, "azure-pl-PL-scripted"],
        "planned_calls": 6, "groq_minimum_billable_audio_seconds_if_charged": 40,
        "azure_audio_seconds": round(sum(c["seconds"] for c in clips), 3),
        "network_calls_performed": 0,
        "warning": "Six genuine model requests only after free-plan/zero-paid checks; "
                   "Whisper WER is ASR, Azure PA is raw/unvalidated for Polish pronunciation",
    }


def execute(folder: Path, *, send: bool = False, approve_public_audio_upload: bool = False,
            confirm_groq_free: bool = False, confirm_azure_f0: bool = False,
            confirm_no_paid_billing: bool = False, output: Path | None = None,
            groq_key: str | None = None, azure_key: str | None = None,
            azure_region: str | None = None,
            transcriber: Callable | None = None, assessor: Callable | None = None) -> dict:
    plan = preview(folder)
    if not send:
        return plan
    if not (approve_public_audio_upload and confirm_groq_free and
            confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("For six public voice uploads: approve source upload, confirm Groq Free, "
                         "Azure F0 and no paid/auto-top-up. A flag is not an account guarantee.")
    if not groq_key or not azure_key or azure_region != AZURE_REGION:
        raise ValueError("Use existing private GROQ_API_KEY, AZURE_SPEECH_KEY, "
                         "AZURE_SPEECH_REGION=germanywestcentral; do not paste keys in chat")
    if not groq_key.isascii() or not azure_key.isascii() or "\u2026" in (groq_key+azure_key):
        raise ValueError("Local credentials contain non-ASCII/placeholder characters")
    if output is None:
        raise ValueError("Specify a NEW private --output JSONL filename")
    if transcriber is None:
        transcriber = lambda wav, model, key: transcribe(wav, model, key, transport="curl")
    if assessor is None:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except ImportError:
            raise RuntimeError("Local Azure Speech SDK missing. Install in private speech test venv.") from None
        assessor = azure_scripted_assess

    # Validate whole fixture and exclusive private output BEFORE any model request.
    clips = checked_public_clips(folder)
    if len(clips) * 3 != MAX_CALLS:
        raise ValueError("Public experiment must contain exactly six requests")
    calls = 0
    with _output(output, folder) as stream:
        for c in clips:
            for model in MODELS:
                started = time.monotonic()
                hypothesis = transcriber(c["audio"], model, groq_key)
                elapsed = round((time.monotonic() - started) * 1000, 1)
                if not isinstance(hypothesis, str):
                    raise ValueError("Groq returned malformed transcript; no automatic retry")
                row = {"sample_id": c["id"], "reference": c["reference"],
                       "audio_sha256": c["sha256"], "engine": "groq-" + model,
                       "status": "ok" if hypothesis.strip() else "inconclusive",
                       "transcript": hypothesis, "wer": word_error_rate(c["reference"], hypothesis),
                       "latency_ms": elapsed, "pronunciation_grade": None,
                       "source_public_native": True, "human_calibrated": False}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush(); os.fsync(stream.fileno())
                calls += 1

            started = time.monotonic()
            assessed = assessor(c["audio"], c["reference"], azure_key, azure_region)
            elapsed = round((time.monotonic() - started) * 1000, 1)
            if not isinstance(assessed, dict) or assessed.get("status") not in ("ok", "inconclusive"):
                raise ValueError("Azure result unusable; no automatic retry or fake 0")
            raw = assessed.get("raw_azure_json")
            native = extract_azure_native(raw) if isinstance(raw, dict) else {
                "status": "inconclusive", "reason": assessed.get("reason")}
            row = {"sample_id": c["id"], "reference": c["reference"],
                   "audio_sha256": c["sha256"], "engine": "azure-pl-PL-scripted",
                   "status": assessed["status"], "azure_native": native,
                   "latency_ms": elapsed, "raw_azure_json": raw,
                   "source_public_native": True, "assessment_is_human_calibrated": False}
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())
            calls += 1
    return {"status": "PUBLIC_NATIVE_SIX_CALLS_COMPLETED",
            "network_calls_performed": calls, "results_private": True,
            "report": summarize(output)}


def summarize(output: Path) -> dict:
    """Read saved provider evidence locally; no AI requests or score inventions."""
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    fit = offline_review(rows)
    per_clip = []
    for entry in rows:
        shown = {"sample_id": entry["sample_id"], "reference": entry["reference"],
                 "engine": entry["engine"], "status": entry["status"],
                 "latency_ms": entry.get("latency_ms")}
        if entry["engine"].startswith("groq-"):
            shown["transcript"] = entry.get("transcript")
            shown["word_error_rate_ASR_only"] = entry.get("wer")
        else:
            native = entry.get("azure_native")
            shown["azure_scores_uncalibrated"] = (
                native.get("scores") if isinstance(native, dict) else None)
            shown["reason"] = (native.get("reason") if isinstance(native, dict) else None)
        per_clip.append(shown)
    return {"evidence": per_clip, "fit": fit}


def main() -> int:
    p = argparse.ArgumentParser(description="Two public-domain Polish voices × 3 engines; 0 inference by default")
    p.add_argument("--fixture-dir", type=Path)
    p.add_argument("--send", action="store_true")
    p.add_argument("--approve-public-audio-upload", action="store_true")
    p.add_argument("--confirm-groq-free", action="store_true")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path, help="New private results .jsonl inside --fixture-dir")
    p.add_argument("--summarize", type=Path, help="Read saved results with ZERO provider calls")
    args = p.parse_args()
    try:
        if args.summarize:
            result = summarize(args.summarize)
        else:
            if not args.fixture_dir:
                raise ValueError("Use --fixture-dir or --summarize")
            result = execute(args.fixture_dir, send=args.send,
                approve_public_audio_upload=args.approve_public_audio_upload,
                confirm_groq_free=args.confirm_groq_free,
                confirm_azure_f0=args.confirm_azure_f0,
                confirm_no_paid_billing=args.confirm_no_paid_billing,
                output=args.output, groq_key=os.environ.get("GROQ_API_KEY"),
                azure_key=os.environ.get("AZURE_SPEECH_KEY"),
                azure_region=os.environ.get("AZURE_SPEECH_REGION"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as err:
        p.error(str(err))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
