#!/usr/bin/env python3
"""Read-only acoustic triage + optional human microphone-quality review.

No provider calls and no edits to audio, imported transcript or native
pronunciation certification. Acoustic measurements are diagnostic flags only.
Only a real independent fluent Polish listener may certify Polish reference.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import wave

from research_paths import check_research_location

BLOCK_FRAMES = 3200  # 200ms @ 16kHz
LABELS = {"c": "clear", "q": "too_quiet", "d": "noisy_or_distorted", "u": "uncertain"}


def _db(value: float) -> float:
    return round(20 * math.log10(max(value, 1e-12)), 1)


def measure_wav(path: Path) -> dict:
    """Compute auditable level/clip metrics on untouched PCM16 WAV samples."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("WAV must be a real regular file")
    total = 0
    sum_sq = 0
    peak = 0
    clipped = 0
    window_sq = 0
    window_count = 0
    windows = []
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
            raise ValueError("Expected mono 16kHz PCM16 WAV")
        while True:
            frames = wav.readframes(BLOCK_FRAMES)
            if not frames:
                break
            samples = array("h")
            samples.frombytes(frames)
            if sys.byteorder != "little":
                samples.byteswap()
            for sample in samples:
                amp = abs(sample)
                peak = max(peak, amp)
                sum_sq += sample * sample
                clipped += amp >= 32700
                total += 1
                window_sq += sample * sample
                window_count += 1
                if window_count == BLOCK_FRAMES:
                    windows.append(math.sqrt(window_sq / window_count) / 32768)
                    window_sq = window_count = 0
        if window_count:
            windows.append(math.sqrt(window_sq / window_count) / 32768)
    if not total:
        raise ValueError("Empty WAV")
    rms = math.sqrt(sum_sq / total) / 32768
    peak_norm = peak / 32768
    # Detect low-level recordings, not the quality of the human's accent.
    # Silence fraction may be high in natural speech: only a review hint.
    quiet_windows = sum(v < 0.0031623 for v in windows)
    clipping_pct = 100 * clipped / total
    hints = []
    if _db(rms) < -32 or _db(peak_norm) < -25:
        hints.append("low_signal_level")
    if clipping_pct > 0.1:
        hints.append("possible_clipping")
    if len(windows) >= 8 and quiet_windows / len(windows) > 0.65:
        hints.append("long_low_level_sections")
    return {
        "duration_seconds": round(total / 16000, 3),
        "rms_dbfs": _db(rms),
        "peak_dbfs": _db(peak_norm),
        "clipped_sample_percent": round(clipping_pct, 3),
        "quiet_window_percent": round(100 * quiet_windows / len(windows), 1),
        "flags": hints,
    }


def inspect_manifest(manifest: Path) -> list[dict]:
    """Never interpret a source row's metadata as verified native speech."""
    check_research_location(manifest)
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Manifest must be a real file")
    if stat.S_IMODE(manifest.parent.stat().st_mode) & 0o077:
        raise ValueError("Source directory must be chmod 700")
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Expected 1–100 source recordings")
    out = []
    names = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Invalid source row")
        name, sid = item.get("audio"), item.get("id")
        if (not isinstance(sid, str) or not sid or
                not isinstance(name, str) or name != Path(name).name or
                not name.endswith(".wav") or name in names):
            raise ValueError("Expected unique local WAV filename/id")
        names.add(name)
        path = manifest.parent / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or symlinked WAV: " + name)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if item.get("audio_sha256") != sha:
            raise ValueError("Checksum missing or changed for " + name)
        metrics = measure_wav(path)
        out.append({
            "id": sid, "audio": name, "audio_sha256": sha,
            "acoustics": metrics,
            "human_audio_quality": None,
            "native_pronunciation_verified": False,
            "reference_verified_by_human": item.get("reference_verified_by_human") is True,
            "provider_upload_approved": False,
            "review_notes": "",
        })
    return out


def review_recordings(items: list[dict], folder: Path, *, reader=input,
                      player=None) -> list[dict]:
    """Ratings concern *recording quality*, not correctness of spoken Polish."""
    if player is None:
        player = lambda path: subprocess.run(["afplay", str(path)], check=True)
    for i, row in enumerate(items, start=1):
        path = folder / row["audio"]
        print(f"\n--- Audio quality {i}/{len(items)}: {row['audio']} ---")
        a = row["acoustics"]
        print(f"level: RMS {a['rms_dbfs']} dBFS, peak {a['peak_dbfs']} dBFS; advisory flags: {', '.join(a['flags']) or 'none'}")
        while True:
            player(path)
            label = reader("Mic quality [c]lear/[q]uiet/[d]istorted or noisy/[u]nsure/[r]eplay: ").lower().strip()
            if label == "r":
                continue
            if label not in LABELS:
                print("Choose c, q, d, u or r.")
                continue
            row["human_audio_quality"] = LABELS[label]
            break
    return items


def save_review(items: list[dict], destination: Path) -> None:
    check_research_location(destination)
    if destination.is_symlink() or destination.exists():
        raise ValueError("Choose a fresh private review output filename")
    folder = destination.parent
    if folder.is_symlink() or not folder.is_dir() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("Review output directory must exist and be chmod 700")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(destination, flags, 0o600), "w", encoding="utf-8") as out:
        json.dump({
            "type": "preliminary_recording_quality_only",
            "does_not_certify_native_polish": True,
            "does_not_approve_provider_upload": True,
            "recordings": items,
        }, out, ensure_ascii=False, indent=2)


def main() -> int:
    p = argparse.ArgumentParser(description="Local 16-kHz WAV quality triage; no Azure/Groq calls")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--review", action="store_true", help="Actually play WAVs and ask for mic-quality labels")
    p.add_argument("--output", type=Path, help="NEW private review JSON filename (with --review)")
    args = p.parse_args()
    try:
        if args.review and args.output is None:
            raise ValueError("--review requires a NEW --output JSON path")
        if not args.review and args.output:
            raise ValueError("--output only applies to interactive --review")
        if args.review and not sys.stdin.isatty():
            raise ValueError("Interactive review requires a Mac Terminal, not Python heredoc/stdin")
        items = inspect_manifest(args.manifest)
        if args.review:
            items = review_recordings(items, args.manifest.parent)
            save_review(items, args.output)
        else:
            for row in items:
                a = row["acoustics"]
                print(f"{row['audio']}: RMS {a['rms_dbfs']} dBFS, peak {a['peak_dbfs']} dBFS, clipped {a['clipped_sample_percent']}%, hints={','.join(a['flags']) or 'none'}")
            print("Review flags are NOT proof of native pronunciation or a valid transcript.")
        print(json.dumps({
            "checked": len(items),
            "quality_review_saved": str(args.output) if args.review else None,
            "speech_ai_requests": 0,
            "native_verified": 0,
            "audio_files_modified": 0,
        }, indent=2))
    except (ValueError, OSError, json.JSONDecodeError, wave.Error, subprocess.SubprocessError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
