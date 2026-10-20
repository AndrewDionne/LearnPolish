#!/usr/bin/env python3
"""Strict, *offline* extraction of manually marked intervals from an original WAV.

Cuts original PCM16 frames at chosen timestamps without speech synthesis,
Whisper, Azure, audio resampling or inferred scores. The only permitted output
is a new directory within the ignored PathToPolish-Private-AI research folder.
Human/private sound remains private; never push generated clips to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import wave

from research_paths import check_research_location

EXPECTED = ("Świę", "to", "krzy", "ska")
FILENAMES = ("01-swien.wav", "02-to.wav", "03-krzy.wav", "04-ska.wav")
SAMPLE_RATE = 16000


def _private_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Private research parent directory does not exist or is a symlink")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private research folder must be chmod 700")


def _read_private_source(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".wav":
        raise ValueError("Expected an existing original non-symlink WAV")
    _private_directory(path.parent)
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private WAV must be chmod 600")
    if path.stat().st_size > 10_000_000:
        raise ValueError("Private WAV too large")
    return path.read_bytes()


def _manual_intervals(record: object, raw: bytes, duration: float) -> list[tuple[float, float]]:
    if not isinstance(record, dict) or record.get("schemaVersion") != 1 or (
        record.get("method") != "manual-syllable-audition-v1"
    ) or record.get("polish") != "Świętokrzyska" or record.get("syllables") != list(EXPECTED):
        raise ValueError("Not an authored Świętokrzyska manual syllable interval file")
    if record.get("assessmentStatus") != "timing_only_unverified" or record.get("scores") is not None:
        raise ValueError("Timing-only evidence cannot contain pronunciation scores")
    sha = hashlib.sha256(raw).hexdigest()
    if record.get("sourceSha256") != sha or record.get("sourceBytes") != len(raw):
        raise ValueError("The original WAV differs from the marked recording")
    reported_duration = record.get("sourceDurationSeconds")
    if type(reported_duration) not in (int, float) or not math.isfinite(reported_duration) or (
        abs(reported_duration - duration) > .03
    ):
        raise ValueError("Duration differs from original source WAV")
    intervals = record.get("intervals")
    if not isinstance(intervals, list) or len(intervals) != 4:
        raise ValueError("Four manually verified syllable ranges are required")
    parsed: list[tuple[float, float]] = []
    prior = None
    for i, row in enumerate(intervals):
        if not isinstance(row, dict) or row.get("polish") != EXPECTED[i]:
            raise ValueError("Intervals must match the four authored Polish syllables")
        a, b = row.get("startSeconds"), row.get("endSeconds")
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in (a,b)):
            raise ValueError("Non-finite boundary")
        if a < 0 or b - a < .044 or b > duration + .001 or (
            prior is not None and abs(prior - a) > .002
        ):
            raise ValueError("Invalid, overlapping or unconnected syllable timing")
        parsed.append((float(a),float(b)))
        prior = b
    return parsed


def prepare_clips(audio: Path, timings: Path, target: Path) -> dict:
    """Create private audition WAV clips; refuse stale hashes, overwrite or ambiguity."""
    original = _read_private_source(audio)
    _private_directory(timings.parent)
    if timings.is_symlink() or not timings.is_file() or timings.stat().st_size > 100_000:
        raise ValueError("Use an existing small, private non-symlink timings JSON")
    if stat.S_IMODE(timings.stat().st_mode) & 0o077:
        raise ValueError("Private timing JSON must be chmod 600")
    if target.exists() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError("Choose a NEW output directory; existing output is never overwritten")
    _private_directory(target.parent)
    check_research_location(target)
    # Only use an ignored private child of the canonical research folder.
    root = Path(__file__).resolve().parents[2]
    private_root = root / "PathToPolish-Private-AI"
    if private_root not in target.absolute().parents or target.resolve(strict=False).is_relative_to(private_root.resolve()) is False:
        raise ValueError("Clips must remain inside the canonical ignored PathToPolish-Private-AI folder")
    with wave.open(str(audio), "rb") as wav:
        if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=SAMPLE_RATE or wav.getcomptype()!="NONE":
            raise ValueError("Original must be mono 16kHz PCM16, without compression")
        sample_count=wav.getnframes()
    duration=sample_count/SAMPLE_RATE
    record=json.loads(timings.read_text(encoding="utf-8"))
    intervals=_manual_intervals(record, original, duration)

    # Validate complete manifest and source before creating any output.
    target.mkdir(mode=0o700)
    report={"schemaVersion":1,"purpose":"listening_only_no_scores","polish":"Świętokrzyska",
            "sourceSha256":hashlib.sha256(original).hexdigest(),"samples":sample_count,
            "sampleRate":SAMPLE_RATE,"segments":[]}
    try:
        with wave.open(str(audio),"rb") as wav:
            for i, (start,end) in enumerate(intervals):
                first=round(start*SAMPLE_RATE)
                last=round(end*SAMPLE_RATE)
                if last-first<round(.04*SAMPLE_RATE) or last>sample_count:
                    raise ValueError("Syllable interval resolves to too few source frames")
                wav.setpos(first)
                data=wav.readframes(last-first)
                if len(data)!=(last-first)*2:
                    raise ValueError("Incomplete original audio frames")
                destination=target/FILENAMES[i]
                flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0)
                fd=os.open(destination,flags,0o600)
                with os.fdopen(fd,"wb") as out:
                    with wave.open(out,"wb") as clip:
                        clip.setnchannels(1)
                        clip.setsampwidth(2)
                        clip.setframerate(SAMPLE_RATE)
                        clip.writeframes(data)
                report["segments"].append({"polish":EXPECTED[i],"filename":FILENAMES[i],
                    "startSeconds":start,"endSeconds":end,
                    "clipSha256":hashlib.sha256(destination.read_bytes()).hexdigest()})
        manifest=target/"listening-clips.json"
        fd=os.open(manifest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(report,out,ensure_ascii=False,indent=2)
            out.write("\n")
    except Exception:
        # Safe only because the fresh destination was confirmed absent above.
        shutil.rmtree(target)
        raise
    return {"status":"created_local_syllable_clips","count":len(report["segments"]),
            "sample_rate":SAMPLE_RATE,"phonetic_grades_computed":False,
            "network_requests":0}


def main() -> int:
    parser=argparse.ArgumentParser(description="Offline-only original-WAV syllable clip exporter")
    parser.add_argument("--audio",required=True,type=Path)
    parser.add_argument("--timings",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    try:
        result=prepare_clips(args.audio,args.timings,args.output_dir)
    except (OSError, ValueError, wave.Error, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
