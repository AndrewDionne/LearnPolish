#!/usr/bin/env python3
"""Offline, auditable Polish sentence/tempo study preparation.

This NEVER downloads audio, sends audio, changes originals or uses AI.
Original WAVs must be human-reviewed BEFORE the study is prepared.
The output is a NEW child directory of the owner's existing ignored folder.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

from benchmark import read_audio_metadata
from research_paths import check_research_location

SPEEDS = (1.0, 0.85, 0.75)
ROLES = ("native_control", "adult_learner")
STYLES = ("natural_normal", "natural_slow")


def _owner_private(path: Path) -> None:
    if path.is_symlink() or not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private folder must exist, be non-symlink and chmod 700")


def validate_source(manifest: Path, min_samples: int = 8) -> list[dict]:
    """Fail closed if speaker/context/reference/rights or WAV evidence is absent."""
    if not 1 <= min_samples <= 12:
        raise ValueError("Minimum sample count must be between 1 and 12")
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Source manifest must be a regular file")
    _owner_private(manifest.parent)
    source = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(source, list) or not min_samples <= len(source) <= 12:
        raise ValueError("Requires between min_samples and 12 reviewed sentences")
    ids, hashes, speakers = set(), set(), set()
    checked = []
    for row in source:
        if not isinstance(row, dict):
            raise ValueError("Each source row must be an object")
        sid, name, reference = row.get("id"), row.get("audio"), row.get("reference")
        if not isinstance(sid, str) or not sid or not sid.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Sample id must contain letters/digits/hyphen/underscore")
        if sid in ids:
            raise ValueError("Duplicate sample id")
        ids.add(sid)
        if not isinstance(name, str) or Path(name).is_absolute() or name != Path(name).name or not name.endswith(".wav"):
            raise ValueError("Audio must name an existing WAV in the source manifest folder")
        audio = manifest.parent / name
        if audio.is_symlink() or not audio.is_file():
            raise ValueError("Audio must be a real non-symlink file: " + sid)
        if not isinstance(reference, str) or len(reference.split()) < 4 or len(reference) > 500:
            raise ValueError("Use an independently verified natural Polish phrase of at least four words")
        if row.get("reference_verified_by_human") is not True or row.get("audio_audited_unclipped") is not True:
            raise ValueError("Human transcript and unclipped audio review must be confirmed: " + sid)
        if row.get("speaker_role") not in ROLES or row.get("speaking_style") not in STYLES:
            raise ValueError("Select native_control/adult_learner and natural_normal/natural_slow")
        speaker = row.get("speaker_id")
        if not isinstance(speaker, str) or not speaker or len(speaker) > 50:
            raise ValueError("Speaker needs anonymous local ID")
        speakers.add(speaker)
        if row.get("speaker_role") == "adult_learner" and row.get("adult_consent_confirmed") is not True:
            raise ValueError("Adult learner recording requires consent confirmation")
        if row.get("speaker_role") == "native_control":
            if not isinstance(row.get("source_license"), str) or not row["source_license"].strip():
                raise ValueError("Native public control requires verified license or permission")
            if not isinstance(row.get("source_page"), str) or not row["source_page"].startswith(("https://", "local-consented:")):
                raise ValueError("Native control requires traceable source or locally consented identifier")
        # Planning consent is metadata; only separate explicit send flags permit a remote upload.
        if row.get("provider_upload_approved") not in (True, False):
            raise ValueError("Specify provider_upload_approved true/false explicitly")
        meta = read_audio_metadata(audio)
        if not meta["valid_signal"] or not 5.0 <= meta["seconds"] <= 15.0:
            raise ValueError("Expected clear 5–15-second WAV; review or replace " + sid)
        if meta["audio_sha256"] in hashes:
            raise ValueError("Duplicate audio WAV contents")
        hashes.add(meta["audio_sha256"])
        checked.append({
            "id": sid, "source_file": audio, "reference": reference,
            "meta": meta, "speaker_id": speaker,
            "speaker_role": row["speaker_role"], "speaking_style": row["speaking_style"],
            "reference_verified_by_human": True,
            "audio_audited_unclipped": True,
            "adult_consent_confirmed": row.get("adult_consent_confirmed", False),
            "provider_upload_approved": row["provider_upload_approved"],
            "source_license": row.get("source_license"),
            "source_page": row.get("source_page"),
        })
    if len(checked) >= 8 and len(speakers) < 2:
        raise ValueError("The 8–12-sentence evaluation needs at least two speakers")
    return checked


def to_wav_with_tempo(source: Path, output: Path, speed: float, runner=subprocess.run) -> None:
    if speed not in SPEEDS or speed == 1.0:
        raise ValueError("Only reviewed pitch-preserving slowing factors 0.85 and 0.75")
    runner([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-i", str(source), "-filter:a", "atempo=" + str(speed),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(output),
    ], check=True, timeout=60, stdout=subprocess.DEVNULL)


def _row(item: dict, audio_name: str, fingerprint: dict, speed: float) -> dict:
    return {
        "id": item["id"], "audio": audio_name, "reference": item["reference"],
        "audio_sha256": fingerprint["audio_sha256"],
        "original_sha256": item["meta"]["audio_sha256"],
        "audio_seconds": round(fingerprint["seconds"], 3),
        "speed_factor": speed, "artificially_stretched": speed != 1.0,
        "speaker_id": item["speaker_id"], "speaker_role": item["speaker_role"],
        "speaking_style": item["speaking_style"],
        "reference_verified_by_human": item["reference_verified_by_human"],
        "audio_audited_unclipped": item["audio_audited_unclipped"],
        "adult_consent_confirmed": item["adult_consent_confirmed"],
        "provider_upload_approved": item["provider_upload_approved"],
        "source_license": item["source_license"], "source_page": item["source_page"],
    }


def prepare(manifest: Path, output: Path, *, speeds: tuple[float, ...] = (0.85,),
            min_samples: int = 8, converter=to_wav_with_tempo) -> dict:
    """Copy untouched 1× controls into new study output, and derive tempo variants.

    Source recordings never move; never overwrite an existing output directory.
    Staging cleaned automatically if conversion fails. Entirely offline.
    """
    if not speeds or any(s not in (0.85, 0.75) for s in speeds) or len(set(speeds)) != len(speeds):
        raise ValueError("Only unique 0.85 and optionally 0.75 tempo factors")
    check_research_location(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Choose a new non-existing study output folder")
    _owner_private(output.parent)
    items = validate_source(manifest, min_samples=min_samples)
    with tempfile.TemporaryDirectory(prefix=".ptp-sentence-stage-", dir=output.parent) as staging:
        staged = Path(staging)
        rows = {"original": []}
        for speed in speeds:
            rows[f"tempo-{int(speed * 100):03d}"] = []
        for item in items:
            frozen = staged / (item["id"] + "-original.wav")
            shutil.copyfile(item["source_file"], frozen, follow_symlinks=False)
            frozen_meta = read_audio_metadata(frozen)
            if frozen_meta["audio_sha256"] != item["meta"]["audio_sha256"]:
                raise ValueError("Source changed during frozen study copy")
            rows["original"].append(_row(item, frozen.name, frozen_meta, 1.0))
            for speed in speeds:
                variant = staged / (item["id"] + f"-tempo-{int(speed * 100):03d}.wav")
                converter(frozen, variant, speed)
                metadata = read_audio_metadata(variant)
                expected = item["meta"]["seconds"] / speed
                if (not metadata["valid_signal"] or
                        abs(metadata["seconds"] - expected) > 0.20):
                    raise ValueError("Invalid time-stretched WAV for " + item["id"])
                rows[f"tempo-{int(speed * 100):03d}"].append(_row(
                    item, variant.name, metadata, speed))
        for label, entries in rows.items():
            name = ("manifest.json" if label == "original" else f"{label}-manifest.json")
            path = staged / name
            with path.open("x", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            path.chmod(0o600)
        for path in staged.iterdir():
            if path.suffix == ".wav":
                path.chmod(0o600)
        # Atomic publication only once all checks, conversions and manifests pass.
        os.rename(staged, output)
        output.chmod(0o700)
    return {
        "samples": len(items), "speaker_count": len(set(x["speaker_id"] for x in items)),
        "tempo_factors": [1.0, *speeds], "output": str(output),
        "manifest_names": ["manifest.json", *(f"tempo-{int(x*100):03d}-manifest.json" for x in speeds)],
        "network_requests": 0, "source_files_moved": 0,
        "important": "No results are pronunciation grades. Human review tempo artifacts before using variant audio."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Polish sentence corpus audit/tempo preparation — offline only")
    parser.add_argument("--manifest", type=Path, required=True, help="Private source manifest with verified WAVs")
    parser.add_argument("--prepare", action="store_true", help="Create private study copy and tempo variants")
    parser.add_argument("--output-dir", type=Path, help="New child folder inside unchanged PathToPolish-Private-AI/")
    parser.add_argument("--speeds", nargs="+", type=float, default=[0.85], help="0.85, optionally 0.75")
    parser.add_argument("--min-samples", type=int, default=8)
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.output_dir is None:
                raise ValueError("--output-dir is required to prepare a new study")
            report = prepare(args.manifest, args.output_dir,
                             speeds=tuple(args.speeds), min_samples=args.min_samples)
        else:
            if args.output_dir:
                raise ValueError("--output-dir requires --prepare")
            items = validate_source(args.manifest, min_samples=args.min_samples)
            report = {"ready_recordings": len(items), "speakers": len(set(x["speaker_id"] for x in items)),
                      "network_requests": 0, "files_written": 0}
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
