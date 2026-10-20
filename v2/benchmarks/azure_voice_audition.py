#!/usr/bin/env python3
"""Owner-triggered Polish Azure TTS audition. Default: offline preview; ZERO API calls.

No automatic fallback, no bulk generation, no key logging. Writes synthetic MP3s
ONLY inside the existing Git-ignored PathToPolish-Private-AI directory.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "v2" / "frontend"
OUTPUT = ROOT / "PathToPolish-Private-AI" / "voice-audition-01"
VOICE = re.compile(r"^pl-PL-[A-Za-z]+Neural$")
REGION = re.compile(r"^[a-z0-9-]{2,40}$")
FILE = re.compile(r"^pl-PL-[A-Za-z]+Neural/[A-Za-z0-9_-]+\.mp3$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_from_generated_catalog() -> dict:
    task = subprocess.run(
        ["node", "scripts/voice-production.mjs", "--json"],
        cwd=FRONTEND, capture_output=True, text=True,
        check=True, timeout=30,
    )
    return json.loads(task.stdout)


def select_audition_rows(plan: dict, limit: int) -> list[dict]:
    if plan.get("schemaVersion") != 1 or plan.get("phase") != "offline_preview_only":
        raise ValueError("Expected offline, generated V2 audition plan")
    rows = plan.get("audition")
    if not isinstance(rows, list) or len(rows) != 24:
        raise ValueError("Audition input must have precisely 24 reviewed planning rows")
    if not 1 <= limit <= 24:
        raise ValueError("--limit must be 1..24")
    for row in rows:
        if not isinstance(row, dict) or not VOICE.fullmatch(str(row.get("voiceId"))) or not FILE.fullmatch(str(row.get("suggestedLocalFilename"))):
            raise ValueError("Unsafe voice ID or output filename")
        text = row.get("polish")
        if not isinstance(text, str) or not text.strip() or len(text) > 120:
            raise ValueError("Missing or overly long Polish text")
        if sha256(text.encode("utf-8")) != row.get("textSha256"):
            raise ValueError("Changed Polish spoken text in candidate")
        if row.get("status") != "not_generated_not_reviewed":
            raise ValueError("Only ungenerated preview candidates are permitted")
        if not row["suggestedLocalFilename"].startswith(row["voiceId"] + "/"):
            raise ValueError("Voice and output path disagree")
    return rows[:limit]


def azure_request(row: dict, key: str, region: str) -> bytes:
    if not REGION.fullmatch(region):
        raise ValueError("Azure Speech region must be a canonical region ID")
    voice = row["voiceId"]
    polish = html.escape(row["polish"], quote=True)
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        ' xml:lang="pl-PL"><voice name="' + voice + '">'
        + polish + '</voice></speak>'
    ).encode("utf-8")
    request = Request(
        "https://" + region + ".tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml, method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "PathToPolish-VoiceAudition/1.0",
        },
    )
    # The key and full provider errors are never logged or persisted.
    with urlopen(request, timeout=25) as response:
        mp3 = response.read(3_000_000)
    if len(mp3) < 100 or not (mp3[:3] == b"ID3" or (mp3[0] == 0xFF and mp3[1] & 0xE0 == 0xE0)):
        raise ValueError("Provider did not return a recognizable MP3")
    return mp3


def generate(rows: list[dict], *, key: str, region: str, output: Path = OUTPUT) -> list[dict]:
    if not key.strip() or not REGION.fullmatch(region):
        raise ValueError("Missing private Azure key/region")
    if not (ROOT / ".gitignore").is_file() or output != OUTPUT:
        raise ValueError("Only the fixed Git-ignored owner-private output is supported")
    if not output.parent.is_dir():
        raise ValueError("Owner private research folder missing; do not create it automatically")
    if output.exists():
        raise FileExistsError("Existing audition directory will not be overwritten")
    output.mkdir(mode=0o700)
    completed = []
    for row in rows:
        audio = azure_request(row, key, region)
        destination = output / row["suggestedLocalFilename"]
        destination.parent.mkdir(mode=0o700, exist_ok=True)
        # Never overwrite old audition bytes. Failed sequences stay inspectable.
        with destination.open("xb") as handle:
            handle.write(audio)
        completed.append({
            "itemId": row["itemId"], "polish": row["polish"],
            "voiceId": row["voiceId"], "audioPath": row["suggestedLocalFilename"],
            "textSha256": row["textSha256"], "audioSha256": sha256(audio),
            "audioBytes": len(audio), "reviewStatus": "needs_native_speaker_listening_review"
        })
    report = {
        "schemaVersion": 1, "status": "synthetic_audio_unreviewed",
        "notes": "No human voice ground truth or pronunciation grading. Never commit these files.",
        "clips": completed,
    }
    (output / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return completed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3, help="1–24 candidate files; default 3")
    parser.add_argument("--send", action="store_true", help="Explicit Azure synthesis call(s)")
    parser.add_argument("--approve-generation", action="store_true")
    parser.add_argument("--confirm-speech-f0", action="store_true")
    parser.add_argument("--confirm-no-paid-billing", action="store_true")
    args = parser.parse_args(argv)
    plan = plan_from_generated_catalog()
    rows = select_audition_rows(plan, args.limit)
    preview = {
        "status": "READY_TO_REQUEST_ONLY" if args.send else "PREVIEW_ONLY",
        "files": len(rows), "characters": sum(r["characters"] for r in rows),
        "voices": sorted({r["voiceId"] for r in rows}),
        "new_requests": 0 if not args.send else len(rows),
        "output": "PathToPolish-Private-AI/voice-audition-01/",
    }
    if not args.send:
        print(json.dumps(preview, indent=2))
        return 0
    if not (args.approve_generation and args.confirm_speech_f0 and args.confirm_no_paid_billing):
        parser.error("--send requires --approve-generation --confirm-speech-f0 --confirm-no-paid-billing")
    key = os.getenv("AZURE_SPEECH_KEY", "")
    region = os.getenv("AZURE_SPEECH_REGION", "")
    if not key or not REGION.fullmatch(region):
        parser.error("Set private AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in your own terminal")
    try:
        completed = generate(rows, key=key, region=region)
    except Exception:
        print("Synthesis stopped; inspect the private output directory. No automatic retries or overwrites.", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps({
        "status": "PRIVATE_SYNTHETIC_AUDIO_UNREVIEWED",
        "clips": len(completed),
        "review": "Native Polish listening comparison required before publishing.",
        "output": preview["output"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
