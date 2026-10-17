#!/usr/bin/env python3
"""Free-first, explicit-upload Groq Whisper comparison for private Polish WAVs.

Default is NO NETWORK ACCESS. This runner never uploads without three distinct
conditions: --send, --approve-voice-upload, and --confirm-free-plan.
No retries, no paid-plan detection claim, no pronunciation scoring.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import stat
import urllib.error
import urllib.request
from typing import Callable

from benchmark import load_manifest, polish_match, read_audio_metadata

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
MODELS = ("whisper-large-v3", "whisper-large-v3-turbo")


def prepare(manifest: Path, models: tuple[str, ...], max_requests: int,
            max_billed_seconds: float) -> tuple[list[tuple], int, float]:
    """Validate *all* inputs and budget before any network requests."""
    if not models or len(set(models)) != len(models) or any(m not in MODELS for m in models):
        raise ValueError("Only distinct supported Whisper models are permitted")
    if max_requests < 1 or max_billed_seconds <= 0:
        raise ValueError("Limits must be positive")
    checked = []
    for sample in load_manifest(manifest):
        if sample.audio.is_symlink() or not sample.audio.is_file():
            raise ValueError("Recording must be a regular, non-symlink WAV")
        meta = read_audio_metadata(sample.audio)
        if sample.audio_sha256 and sample.audio_sha256 != meta["audio_sha256"]:
            raise ValueError("Recording changed since corpus creation: " + sample.id)
        if not meta["valid_signal"] or not 0.6 <= meta["seconds"] <= 12:
            raise ValueError("Unusable audio; re-record before upload: " + sample.id)
        if sample.audio.stat().st_size > 25_000_000:
            raise ValueError("Audio exceeds Groq free-tier 25MB per-file cap")
        checked.append((sample, meta))
    calls = len(checked) * len(models)
    billed_seconds = sum(max(10.0, m["seconds"]) for _, m in checked) * len(models)
    if calls > max_requests:
        raise ValueError(f"API-request hard cap exceeded ({calls} > {max_requests})")
    if billed_seconds > max_billed_seconds:
        raise ValueError(f"Billed-audio cap exceeded ({billed_seconds:.1f}s > {max_billed_seconds:.1f}s)")
    return checked, calls, billed_seconds


def _multipart(audio: bytes, model: str) -> tuple[bytes, str]:
    boundary = "ptp_" + secrets.token_hex(16)
    delimiter = boundary.encode("ascii")
    parts = []
    for field, value in (("model", model), ("language", "pl"),
                         ("response_format", "json"), ("temperature", "0")):
        parts.append(b"--" + delimiter + b"\r\nContent-Disposition: form-data; name=\"" +
                     field.encode("ascii") + b"\"\r\n\r\n" + value.encode("ascii") + b"\r\n")
    parts.append(b"--" + delimiter + b"\r\n"
                 b'Content-Disposition: form-data; name="file"; filename="recording.wav"\r\n'
                 b"Content-Type: audio/wav\r\n\r\n" + audio + b"\r\n")
    parts.append(b"--" + delimiter + b"--\r\n")
    return b"".join(parts), boundary


def transcribe(audio_path: Path, model: str, api_key: str,
               opener: Callable | None = None) -> str:
    if model not in MODELS or not api_key:
        raise ValueError("Supported model and an environment API key required")
    data, boundary = _multipart(audio_path.read_bytes(), model)
    request = urllib.request.Request(
        GROQ_ENDPOINT, method="POST", data=data,
        headers={"Authorization": "Bearer " + api_key,
                 "Content-Type": "multipart/form-data; boundary=" + boundary})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=45) as response:
            payload = json.loads(response.read(65536))
    except urllib.error.HTTPError as error:
        # Never echo remote body: it may contain user text or implementation details.
        raise RuntimeError(f"Groq returned HTTP {error.code}; no automatic retry") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Groq connection failed; no automatic retry") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        raise ValueError("Groq returned a malformed transcription response")
    return payload["text"].strip()


def _private_output(path: Path):
    """Create results outside Git with 0600 permissions; never overwrite."""
    destination = path.absolute()
    root = Path(__file__).resolve().parents[2]
    resolved = destination.resolve(strict=False)
    if resolved == root or root in resolved.parents:
        raise ValueError("AI research results must be saved outside the Git repository")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output already exists; choose a new filename")
    parent = destination.parent
    if not parent.is_dir() or (stat.S_IMODE(parent.stat().st_mode) & 0o077):
        raise ValueError("Output directory must exist and be owner-private (chmod 700)")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    return os.fdopen(os.open(destination, flags, 0o600), "w", encoding="utf-8")


def run(manifest: Path, models: tuple[str, ...], max_requests: int = 4,
        max_billed_seconds: float = 40.0, *, send: bool = False,
        approve_voice_upload: bool = False, confirm_free_plan: bool = False,
        output: Path | None = None, api_key: str | None = None,
        transcriber: Callable = transcribe) -> dict:
    checked, calls, billed = prepare(manifest, models, max_requests, max_billed_seconds)
    summary = {"recordings": len(checked), "models": list(models),
               "planned_requests": calls, "estimated_billed_seconds": billed,
               "network_requests_performed": 0}
    if not send:
        return summary
    if not (approve_voice_upload and confirm_free_plan):
        raise ValueError("Upload requires BOTH --approve-voice-upload and --confirm-free-plan")
    if not api_key:
        raise ValueError("Load GROQ_API_KEY in your local shell; never paste it into GitHub")
    if output is None:
        raise ValueError("A private --output JSONL path is required for live evaluation")
    # Create private results file before the first API request, to persist each
    # successful result even if the next request fails or is rate limited.
    with _private_output(output) as stream:
        for sample, meta in checked:
            for model in models:
                transcript = transcriber(sample.audio, model, api_key)
                result = {"id": sample.id, "reference": sample.reference,
                          "engine": "groq-" + model, "model": model,
                          "audio_seconds": round(meta["seconds"], 3),
                          "audio_sha256": meta["audio_sha256"],
                          "status": "ok" if transcript else "inconclusive",
                          "transcript": transcript,
                          "recognized_expected_words": (
                              polish_match(sample.reference, transcript) if transcript else None),
                          "pronunciation_score": None}
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                summary["network_requests_performed"] += 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Groq Polish ASR pilot (default NO UPLOAD)")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--max-requests", type=int, default=4)
    parser.add_argument("--max-billed-seconds", type=float, default=40)
    parser.add_argument("--send", action="store_true", help="Actually upload each private WAV to Groq")
    parser.add_argument("--approve-voice-upload", action="store_true",
                        help="I have explicit informed consent for sending these adult voice recordings to Groq")
    parser.add_argument("--confirm-free-plan", action="store_true",
                        help="I checked Groq Console account limits, free plan and disabled paid billing")
    parser.add_argument("--output", type=Path, help="New private JSONL outside this repository (0600)")
    args = parser.parse_args()
    try:
        report = run(args.manifest.resolve(), tuple(args.models), args.max_requests,
                     args.max_billed_seconds, send=args.send,
                     approve_voice_upload=args.approve_voice_upload,
                     confirm_free_plan=args.confirm_free_plan,
                     output=args.output, api_key=os.environ.get("GROQ_API_KEY"))
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    if not args.send:
        print("PREVIEW ONLY — no voice uploaded, no API requests, no charges generated.")
    else:
        print("These are recognition transcripts, NOT pronunciation grades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
