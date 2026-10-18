#!/usr/bin/env python3
"""Fetch two public-domain Polish reference voices for OFFLINE Speak E2E browser tests.

No Azure/Groq/AI calls.  Wikimedia Commons original recordings are downloaded
only during explicit CI/local fixture preparation. They are deliberately NOT
added to source control, bundled into the app, or uploaded to any AI provider.

The two target texts are the FIRST TWO Conversation 1 Speak items, allowing
real natural Polish audio rather than the old oscillator signal in E2E.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from benchmark import read_audio_metadata

SOURCES = (
    {
        "id": "greeting-day", "text": "Dzień dobry",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b8/Pl-dzie%C5%84_dobry-2.ogg",
        "description": "https://commons.wikimedia.org/wiki/File:Pl-dzie%C5%84_dobry-2.ogg",
        "author": "Julo", "license": "Public domain", "duration_hint": 1.3,
    },
    {
        "id": "greeting-evening", "text": "Dobry wieczór",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/bb/Pl-dobry_wiecz%C3%B3r-2.ogg",
        "description": "https://commons.wikimedia.org/wiki/File:Pl-dobry_wiecz%C3%B3r-2.ogg",
        "author": "SirPL0", "license": "Public domain", "duration_hint": 1.6,
    },
)
MAX_SOURCE_BYTES = 130_000


def fetch_original(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
        raise ValueError("Only Wikimedia Commons original audio HTTPS host is allowed")
    request = Request(url, headers={"User-Agent": "PathToPolish-PublicVoiceE2E/1.0 (research fixture)"})
    with urlopen(request, timeout=22) as response:
        if urlparse(response.geturl()).hostname != "upload.wikimedia.org":
            raise ValueError("Unexpected third-party audio redirect")
        data = response.read(MAX_SOURCE_BYTES + 1)
    return data


def validate_ogg(data: bytes) -> str:
    if not isinstance(data, bytes) or not 1000 <= len(data) <= MAX_SOURCE_BYTES:
        raise ValueError("Invalid original audio size")
    if not data.startswith(b"OggS"):
        raise ValueError("Audio must be original Ogg (reject HTML, WAV and other responses)")
    return hashlib.sha256(data).hexdigest()


def prepare_public_audio(output: Path, downloader=fetch_original) -> list[dict]:
    if output.is_symlink():
        raise ValueError("Refuse symlink destination")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("Refuse unsafe fixture directory")
    records = []
    for source in SOURCES:
        audio_ogg = output / (source["id"] + ".ogg")
        audio_wav = output / (source["id"] + ".wav")
        if audio_ogg.exists() or audio_wav.exists():
            raise ValueError("Fixture files already exist; use a fresh output directory")
        data = downloader(source["url"])
        source_sha = validate_ogg(data)
        with audio_ogg.open("xb") as handle:
            handle.write(data)
        try:
            subprocess.run([
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", str(audio_ogg), "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(audio_wav),
            ], check=True, timeout=15, capture_output=True)
        except FileNotFoundError:
            raise ValueError("FFmpeg is not installed on the runner; install ffmpeg before public Polish E2E") from None
        except subprocess.CalledProcessError as error:
            # Keep bounded decoder errors for debugging public, non-sensitive audio.
            details=error.stderr.decode("utf-8",errors="replace")[-500:] if error.stderr else "decoder returned failure"
            raise ValueError("FFmpeg could not decode public-domain Wikimedia Ogg: " + details) from None
        except subprocess.TimeoutExpired:
            raise ValueError("FFmpeg took over 15 seconds decoding a short Polish greeting") from None
        metadata = read_audio_metadata(audio_wav)
        if not metadata["valid_signal"] or not 0.6 <= metadata["seconds"] <= 10:
            raise ValueError("Unusable Polish recording after 16-kHz PCM conversion")
        records.append({
            "id": source["id"], "text": source["text"], "original": audio_ogg.name,
            "wav": audio_wav.name, "source_url": source["description"],
            "author": source["author"], "license": source["license"],
            "original_sha256": source_sha, "wav_sha256": metadata["audio_sha256"],
            "seconds": round(metadata["seconds"], 3),
        })
    (output / "manifest.json").write_text(
        json.dumps({"status": "public_reference_audio_only", "clips": records},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> int:
    p = argparse.ArgumentParser(description="Public Polish voice E2E fixture; no AI/provider inference")
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        rows = prepare_public_audio(args.output_dir)
    except (OSError, ValueError) as e:
        p.error(str(e))
    print(json.dumps({"clips": [{
        "text": row["text"], "seconds": row["seconds"],
        "original_sha256": row["original_sha256"],
        "normalized_sha256": row["wav_sha256"],
        "source_url": row["source_url"],
    } for row in rows], "AI_calls": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
