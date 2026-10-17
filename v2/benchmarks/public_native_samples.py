#!/usr/bin/env python3
"""Opt-in retrieval of six explicitly licensed native Polish pronunciation clips.

Downloads originals from Wikimedia Commons, converts *locally* to benchmark
PCM16 WAV with ffmpeg and writes a private, SHA-256-locked study manifest.
No AI API access, no shell execution, no unknown external URLs, no voice upload.
This corpus is a native-recognition control, NOT evidence of learner scoring.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from typing import Callable
import urllib.parse
import urllib.request

from benchmark import read_audio_metadata

LICENSE_BY25 = "https://creativecommons.org/licenses/by/2.5/"
LICENSE_BY40 = "https://creativecommons.org/licenses/by/4.0/"

# Source URLs and authors checked against individual Commons file pages 2026-10-17.
# Keep source and attribution attached to each exported WAV; do NOT commit WAVs.
SAMPLES = (
    ("czapka", "Rogra", LICENSE_BY25,
     "https://upload.wikimedia.org/wikipedia/commons/e/eb/Pl-czapka.ogg"),
    ("ciasto", "Frizabela", LICENSE_BY25,
     "https://upload.wikimedia.org/wikipedia/commons/d/d2/Pl-ciasto.ogg"),
    ("źle", "Derbeth", LICENSE_BY25,
     "https://upload.wikimedia.org/wikipedia/commons/e/e8/Pl-%C5%BAle.ogg"),
    ("łyżka", "Derbeth", LICENSE_BY25,
     "https://upload.wikimedia.org/wikipedia/commons/6/63/Pl-%C5%82y%C5%BCka.ogg"),
    ("szwedka", "Tsca", LICENSE_BY40,
     "https://upload.wikimedia.org/wikipedia/commons/e/e8/Pl-szwedka.ogg"),
    ("lato", "Derbeth", LICENSE_BY25,
     "https://upload.wikimedia.org/wikipedia/commons/9/9e/Pl-lato.ogg"),
)
MAX_SOURCE_BYTES = 2_000_000


def get_audio(url: str) -> bytes:
    """Fetch known Commons audio only, with a strict response cap."""
    if url not in {entry[3] for entry in SAMPLES}:
        raise ValueError("Only the six pre-reviewed Commons audio URLs are permitted")
    request = urllib.request.Request(url, headers={
        "User-Agent": "PathToPolishResearch/1.0 (non-automated small audio evaluation)",
        "Accept": "audio/ogg,application/ogg,application/octet-stream",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        if urllib.parse.urlparse(response.geturl()).hostname != "upload.wikimedia.org":
            raise ValueError("Audio download redirected outside Wikimedia")
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES or not body.startswith(b"OggS"):
        raise ValueError("Commons original is not a small Ogg audio file")
    return body


def to_wav(source: Path, destination: Path) -> None:
    """Preserve spoken audio; add brief silence to avoid truncated tiny-word ASR."""
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-i", str(source), "-af", "adelay=250,apad=pad_dur=0.5",
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(destination),
    ], check=True, stdout=subprocess.DEVNULL, timeout=35)


def _write_private(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "w", encoding="utf-8") as out:
        out.write(content)


def collect(output_dir: Path, count: int = 2, *,
            fetcher: Callable[[str], bytes] = get_audio,
            converter: Callable[[Path, Path], None] = to_wav) -> list[dict]:
    """Create new 0700 directory only. Abort on collisions or unusable clips."""
    if not 1 <= count <= len(SAMPLES):
        raise ValueError("Select between one and six curated recordings")
    target = output_dir.absolute()
    if target.is_symlink() or target.exists():
        raise ValueError("Choose a new, not-yet-existing output directory")
    parent = target.parent
    if not parent.is_dir() or parent.is_symlink() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise ValueError("Parent private AI folder must exist, be 0700 and not a symlink")
    target.mkdir(mode=0o700)
    rows = []
    sources = []
    with tempfile.TemporaryDirectory(prefix="ptp-commons-", dir=target) as work:
        tmp = Path(work)
        for i, (word, author, license_url, url) in enumerate(SAMPLES[:count], 1):
            original = tmp / f"{i:02d}.ogg"
            original.write_bytes(fetcher(url))
            path = target / f"native-{i:02d}.wav"
            converter(original, path)
            if path.is_symlink():
                raise ValueError("Audio converter created a symlink")
            metadata = read_audio_metadata(path)
            if not 0.6 <= metadata["seconds"] <= 12 or not metadata["valid_signal"]:
                raise ValueError("Unusable native clip from Commons: " + word)
            page = "https://commons.wikimedia.org/wiki/File:" + urllib.parse.unquote(url.rsplit("/", 1)[-1])
            rows.append({
                "id": f"commons-native-{i:02d}",
                "audio": path.name,
                "reference": word,
                "audio_sha256": metadata["audio_sha256"],
                "source_page": page,
                "source_author": author,
                "source_license": license_url,
                "study_role": "native_speaker_asr_control",
                "audio_conversion": "ffmpeg mono 16k PCM16; 250ms lead, 500ms trail silence",
            })
            sources.append(f"{word} — {author} — {page} — {license_url}\n"
                           "Modification: re-encoded to mono 16k PCM16 WAV with added silence.\n")
    _write_private(target / "manifest.json", json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    _write_private(target / "ATTRIBUTION.txt", "\n".join(sources))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Download curated Commons Polish WAV controls; NO AI calls")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="A new subdirectory of a private chmod-700 folder, outside Git")
    parser.add_argument("--count", type=int, default=2, choices=range(1, 7),
                        metavar="1..6", help="Download first N of six reviewed samples; default two")
    args = parser.parse_args()
    try:
        result = collect(args.output_dir, args.count)
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))
    print(f"Ready: {len(result)} native-Polish controls; no Whisper/Groq/Azure calls.")
    print("Manifest:", args.output_dir.absolute() / "manifest.json")
    print("Attribution:", args.output_dir.absolute() / "ATTRIBUTION.txt")
    print("These examples test native Polish ASR recognition, NOT learner pronunciation quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
