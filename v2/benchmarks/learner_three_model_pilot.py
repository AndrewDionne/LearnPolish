#!/usr/bin/env python3
"""One explicit adult V2 Speak WAV -> Groq V3 + Turbo + Azure, same exact bytes.

NO network by default. An adult must deliberately export the recording and
approve upload to both providers, verify F0/free/no-paid account status, and
request --send. Never use child recordings here. No replays, no retries.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import time
from typing import Callable

from azure_pilot import azure_scripted_assess
from speech_env import speech_credentials
from groq_env import groq_key
from benchmark import extract_azure_native, read_audio_metadata
from corpus import parse_capture_name, read_catalog
from groq_pilot import MODELS, transcribe
from research_paths import check_research_location
from three_model_pilot import _output, word_error_rate

AZURE_REGION = "germanywestcentral"


def prepare(manifest: Path, catalog: Path, sample_id: str, max_audio_seconds: float = 10) -> dict:
    check_research_location(manifest)
    if (manifest.is_symlink() or not manifest.is_file() or
            stat.S_IMODE(manifest.parent.stat().st_mode) & 0o077):
        raise ValueError("Select an existing owner-private real manifest under chmod 700")
    if max_audio_seconds <= 0 or max_audio_seconds > 10:
        raise ValueError("Maximum ten original audio seconds per one-triplet test")
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) > 100 or not rows:
        raise ValueError("Expected an existing private corpus manifest")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == sample_id]
    if len(matches) != 1:
        raise ValueError("Explicit --sample-id must match exactly one exported WAV")
    row = matches[0]
    filename = row.get("audio")
    if not isinstance(filename, str) or filename != Path(filename).name:
        raise ValueError("Only manifest-local exported WAVs")
    item_id, _ = parse_capture_name(filename)
    if row.get("item_id") != item_id:
        raise ValueError("Manifest and capture ID disagree")
    known = read_catalog(catalog)
    if item_id not in known or row.get("reference") != known[item_id][0]:
        raise ValueError("Built-in lesson reference must match authoritative Polish catalog")
    audio = manifest.parent / filename
    if audio.is_symlink() or not audio.is_file():
        raise ValueError("Original WAV missing or symlinked")
    meta = read_audio_metadata(audio)
    if (meta["audio_sha256"] != row.get("audio_sha256") or
            not meta["valid_signal"] or not 0.6 <= meta["seconds"] <= max_audio_seconds):
        raise ValueError("Original WAV changed, unusable or over hard audio cap")
    return {"sample_id": sample_id, "audio": audio, "reference": row["reference"],
            "sha256": meta["audio_sha256"], "seconds": meta["seconds"]}


def run(manifest: Path, catalog: Path, sample_id: str, *, max_audio_seconds: float = 10,
        send: bool = False, approve_adult_audio_upload: bool = False,
        confirm_groq_free: bool = False, confirm_azure_f0: bool = False,
        confirm_no_paid_billing: bool = False, groq_key: str | None = None,
        azure_key: str | None = None, azure_region: str | None = None,
        output: Path | None = None, transcriber: Callable | None = None,
        assessor: Callable | None = None) -> dict:
    clip = prepare(manifest, catalog, sample_id, max_audio_seconds)
    plan = {"status": "PREVIEW_ONLY" if not send else "RUNNING",
            "purpose": "exploratory_adult_learner_same_wav_NO_CALIBRATED_GRADE",
            "models": [*MODELS, "azure-pl-PL-scripted"],
            "sample_id": sample_id, "audio_sha256": clip["sha256"],
            "source_audio_seconds": clip["seconds"], "planned_requests": 3,
            "estimated_groq_billed_audio_seconds": 2 * max(10, clip["seconds"]),
            "planned_azure_audio_seconds": clip["seconds"],
            "provider_requests_performed": 0,
            "critical": "Whisper WER is not pronunciation; Azure scores remain uncalibrated"}
    if not send:
        return plan
    if not (approve_adult_audio_upload and confirm_groq_free and
            confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("Explicit adult voice upload authorization, Groq Free, Azure F0 and zero-paid-billing checks required")
    if not groq_key or not azure_key or azure_region != AZURE_REGION:
        raise ValueError("Use only local private existing Groq/Azure keys and germanywestcentral Azure region")
    if output is None:
        raise ValueError("Require a NEW private --output JSONL; never overwrite saved experiments")
    if transcriber is None:
        transcriber = lambda audio, model, key: transcribe(audio, model, key, transport="curl")
    if assessor is None:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except ImportError:
            raise RuntimeError("Azure Speech SDK unavailable; no voice uploaded") from None
        assessor = azure_scripted_assess

    # All validations including private exclusive output happen BEFORE first upload.
    # Groq and Azure work on the SAME original SHA-locked WAV without conversion.
    with _output(output, manifest.parent) as stream:
        completed = 0
        for model in MODELS:
            started = time.monotonic()
            transcript = transcriber(clip["audio"], model, groq_key)
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            if not isinstance(transcript, str):
                raise ValueError("Unusable Groq transcript; stop, preserve partial result")
            entry = {"sample_id": sample_id, "engine": "groq-" + model,
                     "audio_sha256": clip["sha256"], "reference": clip["reference"],
                     "status": "ok" if transcript.strip() else "inconclusive",
                     "transcript": transcript, "wer": word_error_rate(clip["reference"], transcript),
                     "latency_ms": latency_ms, "pronunciation_grade": None, "exploratory_only": True}
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())
            completed += 1

        started = time.monotonic()
        evidence = assessor(clip["audio"], clip["reference"], azure_key, azure_region)
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        if not isinstance(evidence, dict) or evidence.get("status") not in ("ok", "inconclusive"):
            raise ValueError("Malformed Azure result; stop without inventing grade")
        raw = evidence.get("raw_azure_json")
        native = extract_azure_native(raw) if isinstance(raw, dict) else {
            "status": "inconclusive", "reason": evidence.get("reason")}
        entry = {"sample_id": sample_id, "engine": "azure-pl-PL-scripted",
                 "audio_sha256": clip["sha256"], "reference": clip["reference"],
                 "status": evidence["status"], "azure_native": native,
                 "latency_ms": latency_ms, "raw_azure_json": raw,
                 "assessment_is_human_calibrated": False,
                 "exploratory_only": True}
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        stream.flush(); os.fsync(stream.fileno())
        completed += 1
    return {**plan, "status": "EXPLORATORY_COMPLETE",
            "provider_requests_performed": completed, "results_saved_private": True}


def main() -> int:
    p = argparse.ArgumentParser(description="ONE adult Speak take, 3 engines, 0 calls unless --send")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--catalog", default="v2/frontend/public/generated/lessons.json", type=Path)
    p.add_argument("--sample-id", required=True)
    p.add_argument("--max-audio-seconds", type=float, default=10)
    p.add_argument("--send", action="store_true")
    p.add_argument("--approve-adult-audio-upload", action="store_true")
    p.add_argument("--confirm-groq-free", action="store_true")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        key, region = speech_credentials() if args.send else (None, None)
        result = run(args.manifest, args.catalog, args.sample_id,
                     max_audio_seconds=args.max_audio_seconds,send=args.send,
                     approve_adult_audio_upload=args.approve_adult_audio_upload,
                     confirm_groq_free=args.confirm_groq_free,
                     confirm_azure_f0=args.confirm_azure_f0,
                     confirm_no_paid_billing=args.confirm_no_paid_billing,
                     groq_key=groq_key() if args.send else None,
                     azure_key=key,
                     azure_region=region,
                     output=args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError) as e:
        p.error(str(e))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
