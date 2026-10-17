#!/usr/bin/env python3
"""Prepare/check private native-speaker study labels. Never uploads or scores speech.

A completed reviewer sheet is NOT a pronunciation grade. The reviewer must listen
without seeing intended text first, then examine the known reference on pass 2.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from benchmark import load_manifest, read_audio_metadata

SOUND_TAGS = frozenset((
    "sz_vs_ś", "cz_vs_ć", "ż_vs_ź", "c_vs_cz", "ł_vs_l",
    "ą_vs_ę", "consonant_cluster", "vowel", "stress", "other",
))
QUALITIES = frozenset(("clear", "noisy", "clipped", "silence"))


def make_template(manifest: Path) -> list[dict]:
    rows = []
    for sample in load_manifest(manifest):
        metadata = read_audio_metadata(sample.audio)
        if sample.audio_sha256 and metadata["audio_sha256"] != sample.audio_sha256:
            raise ValueError("Recording bytes changed: " + sample.id)
        rows.append({
            "id": sample.id,
            "audio_sha256": metadata["audio_sha256"],
            "heard_without_reference": None,
            "intelligible": None,
            "target_correct": None,
            "capture_quality": None,
            "sound_error_tags": None,
            "stress_correct": None,
            "reviewer_notes": "",
        })
    return rows


def check_labels(manifest: Path, labels: list[dict]) -> dict:
    expected = {x["id"]: x for x in make_template(manifest)}
    if not isinstance(labels, list) or len(labels) != len(expected):
        raise ValueError("Provide exactly one labelled row for every manifest recording")
    seen = set()
    counts = {"total": len(expected), "clear": 0, "flagged_capture": 0,
              "intelligible": 0, "target_correct": 0, "marked_sound_errors": 0}
    for row in labels:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("Invalid label row")
        key = row["id"]
        if key not in expected or key in seen:
            raise ValueError("Unknown or duplicated label ID: " + key)
        seen.add(key)
        if row.get("audio_sha256") != expected[key]["audio_sha256"]:
            raise ValueError("Recording fingerprint mismatch: " + key)
        if type(row.get("intelligible")) is not bool or type(row.get("target_correct")) is not bool:
            raise ValueError("Independent intelligibility and target-correct flags required: " + key)
        if not isinstance(row.get("heard_without_reference"), str):
            raise ValueError("Blind first-pass transcription required: " + key)
        quality = row.get("capture_quality")
        if quality not in QUALITIES:
            raise ValueError("Valid capture-quality decision required: " + key)
        errors = row.get("sound_error_tags")
        if (not isinstance(errors, list) or len(set(map(str, errors))) != len(errors) or
                any(not isinstance(tag, str) or tag not in SOUND_TAGS for tag in errors)):
            raise ValueError("Sound-error tags must be a completed list of supported contrasts: " + key)
        if row.get("stress_correct") is not None and type(row["stress_correct"]) is not bool:
            raise ValueError("Stress label must be true/false/null: " + key)
        if not isinstance(row.get("reviewer_notes"), str):
            raise ValueError("Reviewer notes must be text")
        counts["clear" if quality == "clear" else "flagged_capture"] += 1
        counts["intelligible"] += int(row["intelligible"])
        counts["target_correct"] += int(row["target_correct"])
        counts["marked_sound_errors"] += int(bool(errors))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only, private Polish pronunciation review labels")
    sub = parser.add_subparsers(dest="action", required=True)
    for command in ("init", "check"):
        p = sub.add_parser(command)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--labels", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = args.manifest.resolve(strict=True)
        if args.action == "init":
            rows = make_template(manifest)
            target = args.labels.absolute()
            if target.is_symlink():
                raise ValueError("Refusing symlinked label output")
            # O_EXCL: do not destroy private manual ratings from an earlier session.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(rows, out, ensure_ascii=False, indent=2)
                out.write("\n")
            print(f"Prepared {len(rows)} ungraded private labels. Complete blind and reference passes before 'check'.")
        else:
            result = check_labels(manifest, json.loads(args.labels.read_text(encoding="utf-8")))
            print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
