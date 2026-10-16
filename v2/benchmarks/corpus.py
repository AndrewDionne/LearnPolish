#!/usr/bin/env python3
"""Create an exact-text, checksum-locked private research corpus from V2 Speak WAVs.

No remote calls, model inference, copying of voice recordings, or uploads.
The output manifest belongs next to the exported WAV files, outside Git.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import pathlib
import re
from urllib.parse import quote, unquote

from benchmark import read_audio_metadata, MAX_FREE_RECORDINGS, MAX_FREE_SECONDS

NAME = re.compile(r"^ptp-speech-v1--(.+)--(\d{8}T\d{9}Z)\.wav$")
ITEM_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")
SHA = re.compile(r"^[a-f0-9]{64}$")


def read_catalog(path: pathlib.Path) -> dict[str, tuple[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schemaVersion") != 1 or not isinstance(raw.get("lessons"), list):
        raise ValueError("Run npm run content and point --catalog at generated/lessons.json")
    items: dict[str, tuple[str, str]] = {}
    for lesson in raw["lessons"]:
        if not isinstance(lesson, dict) or not isinstance(lesson.get("items"), list):
            raise ValueError("Invalid lesson catalog")
        for entry in lesson["items"]:
            item_id = entry.get("id")
            reference = entry.get("polish")
            if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id) or (
                not isinstance(reference, str) or not reference.strip()
            ) or item_id in items:
                raise ValueError("Ambiguous or malformed catalog item")
            items[item_id] = (reference, lesson.get("id", ""))
    return items


def parse_capture_name(filename: str) -> tuple[str, str]:
    match = NAME.fullmatch(filename)
    if not match:
        raise ValueError("Not a versioned V2 Speak WAV: " + filename)
    encoded, raw_time = match.groups()
    item_id = unquote(encoded)
    if not ITEM_ID.fullmatch(item_id) or quote(item_id, safe="") != encoded:
        raise ValueError("Invalid encoded recording ID: " + filename)
    try:
        dt = datetime.strptime(raw_time, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ValueError("Invalid recording timestamp: " + filename) from error
    return item_id, dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def prepare_corpus(directory: pathlib.Path, catalog: pathlib.Path,
                   max_recordings: int = MAX_FREE_RECORDINGS,
                   max_seconds: float = MAX_FREE_SECONDS) -> list[dict]:
    if not directory.is_dir():
        raise ValueError("Audio directory does not exist")
    reference = read_catalog(catalog)
    wavs = sorted(x for x in directory.iterdir() if x.name.startswith("ptp-speech-v1--"))
    if not wavs:
        raise ValueError("No explicitly exported V2 Speak WAVs found in directory")
    if len(wavs) > max_recordings:
        raise ValueError("Recording cap exceeded")
    rows: list[dict] = []
    digests: set[str] = set()
    total_seconds = 0.0
    for wav in wavs:
        if wav.is_symlink() or not wav.is_file():
            raise ValueError("Research recordings must be regular, non-symlink files")
        item_id, captured_at = parse_capture_name(wav.name)
        if item_id not in reference:
            raise ValueError("No exact Polish reference found for " + item_id)
        metadata = read_audio_metadata(wav)
        total_seconds += metadata["seconds"]
        if total_seconds > max_seconds:
            raise ValueError("Audio time cap exceeded")
        if not (0.6 <= metadata["seconds"] <= 12 and metadata["valid_signal"]):
            raise ValueError("Unusable or near-silent WAV; re-record " + wav.name)
        digest = metadata["audio_sha256"]
        if not SHA.fullmatch(digest) or digest in digests:
            raise ValueError("Duplicate or invalid WAV fingerprint")
        digests.add(digest)
        original_text, lesson_id = reference[item_id]
        rows.append({
            "id": item_id + "@" + captured_at,
            "audio": wav.name,
            "reference": original_text,
            "audio_sha256": digest,
            "item_id": item_id,
            "lesson_id": lesson_id,
            "captured_at_utc": captured_at,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a private V2 audio corpus; never contacts a service")
    parser.add_argument("--audio-dir", type=pathlib.Path, required=True)
    parser.add_argument("--catalog", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path,
                        help="Defaults to manifest.json inside the private recording directory")
    args = parser.parse_args()
    directory = args.audio_dir.resolve()
    destination = (args.output or directory / "manifest.json").resolve()
    if destination.parent != directory or destination.suffix != ".json":
        parser.error("Manifest must be a JSON file directly inside --audio-dir")
    try:
        rows = prepare_corpus(directory, args.catalog.resolve())
        if destination.exists() and destination.is_symlink():
            raise ValueError("Manifest path must not be a symlink")
        destination.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Private benchmark corpus ready: {len(rows)} validated WAVs; no inference or upload performed.")
    print(f"Manifest: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
