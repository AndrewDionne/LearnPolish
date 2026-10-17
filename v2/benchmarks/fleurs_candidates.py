#!/usr/bin/env python3
"""Stage a SMALL Polish FLEURS candidate corpus for independent native review.

No Groq/Azure/other speech AI calls. Every candidate is UNVERIFIED and
provider-upload is FALSE. Owner's chosen root PathToPolish-Private-AI/
and all existing files remain unchanged; no partial manifest is published.
FLEURS pl_pl validation rows are obtained using the public HF dataset-viewer
rows API; cached audio is fetched one file at a time only with --download.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from benchmark import read_audio_metadata

DATASET_PAGE = "https://huggingface.co/datasets/google/fleurs"
VIEWER_HOST = "datasets-server.huggingface.co"
EXPECTED_CONFIG = "pl_pl"
EXPECTED_SPLIT = "validation"
MAX_METADATA_BYTES = 2_000_000
MAX_AUDIO_BYTES = 8_000_000
LICENSE = "CC BY 4.0 — Google FLEURS (confirm third-party service use before upload)"


def private_root(path: Path, *, research_root: Path | None = None) -> Path:
    canonical = (research_root or Path(__file__).resolve().parents[2] /
                 "PathToPolish-Private-AI").absolute()
    candidate = path.absolute()
    if candidate != canonical or candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("Use ONLY the established repo-root PathToPolish-Private-AI/ folder")
    if stat.S_IMODE(candidate.stat().st_mode) & 0o077:
        raise ValueError("Research directory must be private: chmod 700 PathToPolish-Private-AI")
    return candidate


def rows_url(offset: int, limit: int) -> str:
    if not 0 <= offset <= 1000 or not 1 <= limit <= 100:
        raise ValueError("FLEURS request must use bounded offset and length")
    return "https://" + VIEWER_HOST + "/rows?" + urlencode({
        "dataset": "google/fleurs", "config": EXPECTED_CONFIG,
        "split": EXPECTED_SPLIT, "offset": offset, "length": limit,
    })


def _bounded_get(url: str, limit: int, *, opener=urlopen) -> bytes:
    request = Request(url, headers={"User-Agent": "PathToPolish-NativeResearch/1.0",
                                    "Accept": "application/json, audio/*, */*"})
    try:
        with opener(request, timeout=25) as response:
            # Check any HTTP redirect destination too. No bearer keys or voice
            # data ever enter these requests; never expose signed URLs in errors.
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname != VIEWER_HOST:
                raise ValueError("FLEURS request unexpectedly redirected outside trusted dataset host")
            content = response.read(limit + 1)
    except ValueError:
        raise
    except Exception:
        raise RuntimeError("FLEURS dataset fetch failed (no retry); check network or expiry") from None
    if len(content) > limit:
        raise ValueError("FLEURS response exceeded bounded maximum bytes")
    return content


def _audio_url(value: object) -> str:
    sources = value if isinstance(value, list) else []
    for source in sources:
        if not isinstance(source, dict):
            continue
        url, kind = source.get("src"), source.get("type")
        if not isinstance(url, str) or not isinstance(kind, str) or not kind.startswith("audio/"):
            continue
        p = urlparse(url)
        if (p.scheme == "https" and p.hostname == VIEWER_HOST and
                p.path.startswith("/cached-assets/google/fleurs/") and
                not p.username and not p.password and not p.fragment):
            return url
    raise ValueError("FLEURS row has no safely hosted audio URL; abort without fetching")


def extract_candidates(payload: object, *, count: int = 10) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise ValueError("Unexpected Hugging Face dataset-viewer rows response")
    if not 1 <= count <= 12:
        raise ValueError("Only 1–12 FLEURS candidates may be staged per trial")
    ready, seen = [], set()
    for outer in payload["rows"]:
        if not isinstance(outer, dict) or not isinstance(outer.get("row"), dict):
            continue
        row = outer["row"]
        idx, n, reference = outer.get("row_idx"), row.get("num_samples"), row.get("raw_transcription")
        if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or idx > 100000:
            continue
        if idx in seen:
            raise ValueError("Duplicate FLEURS row index")
        seen.add(idx)
        if not isinstance(n, int) or isinstance(n, bool) or not 5.0 <= n / 16000 <= 15.0:
            continue
        if (not isinstance(reference, str) or
                not 4 <= len(reference.split()) <= 80 or len(reference) > 500):
            continue
        # Prevent accidental fallback to normalized text that conceals
        # misalignments. Human listening must verify the raw text.
        audio = _audio_url(row.get("audio"))
        ready.append({
            "row_idx": idx, "recording_id": row.get("id"),
            "reference": reference.strip(), "audio_url": audio,
            "expected_seconds": round(n / 16000, 3),
        })
        if len(ready) == count:
            break
    if len(ready) != count:
        raise ValueError("Too few duration-eligible full-sentence candidates; choose a new offset")
    return ready


def get_candidates(*, count: int = 10, offset: int = 0, opener=urlopen) -> list[dict]:
    if not 1 <= count <= 12:
        raise ValueError("Only 1–12 candidates allowed")
    try:
        data = json.loads(_bounded_get(rows_url(offset, 80), MAX_METADATA_BYTES, opener=opener))
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Invalid FLEURS metadata response") from error
    return extract_candidates(data, count=count)


def ffmpeg_convert(source: Path, target: Path) -> None:
    try:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-y", "-i", str(source), "-vn", "-map_metadata", "-1",
            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target),
        ], check=True, timeout=45, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError("FFmpeg could not decode a FLEURS candidate (no retry)") from None


def stage(destination: Path, candidates: list[dict], *,
          opener=urlopen, converter=ffmpeg_convert,
          research_root: Path | None = None) -> dict:
    """Write previously unverified candidate WAVs + manifest, never originals.

    Candidate ids/metadata come from the bounded, fixed FLEURS viewer route;
    URL revalidated at download time; never store expiring signed URLs on disk.
    """
    folder = private_root(destination, research_root=research_root)
    if not 1 <= len(candidates) <= 12:
        raise ValueError("Expected 1–12 FLEURS candidates")
    target_manifest = folder / "sentences-source.json"
    filenames = [f"fleurs-pl-val-{c['row_idx']:05d}.wav" for c in candidates]
    if (len(set(filenames)) != len(filenames) or
            target_manifest.exists() or target_manifest.is_symlink() or
            any((folder / n).exists() or (folder / n).is_symlink() for n in filenames)):
        raise ValueError("Existing study files would be overwritten; no files changed")

    staged_rows = []
    staged_files = []
    promoted = []
    with tempfile.TemporaryDirectory(prefix=".fleurs-stage-", dir=folder) as tmp:
        root = Path(tmp)
        for cand, filename in zip(candidates, filenames):
            asset = _audio_url([{"src": cand["audio_url"], "type": "audio/wav"}])
            raw = root / (filename + ".source")
            data = _bounded_get(asset, MAX_AUDIO_BYTES, opener=opener)
            raw.write_bytes(data)
            wav = root / filename
            converter(raw, wav)
            meta = read_audio_metadata(wav)
            if not meta["valid_signal"] or not 5.0 <= meta["seconds"] <= 15.0:
                raise ValueError("Candidate WAV silent, invalid or outside 5–15 seconds")
            # Compressed input duration may vary a little; reject mismatched
            # dataset metadata rather than silently trim or re-time content.
            if abs(meta["seconds"] - cand["expected_seconds"]) > 0.65:
                raise ValueError("Audio duration differs from FLEURS metadata")
            wav.chmod(0o600)
            staged_files.append((wav, folder / filename))
            staged_rows.append({
                "id": f"fleurs-pl-val-{cand['row_idx']:05d}",
                "audio": filename, "reference": cand["reference"],
                "audio_sha256": meta["audio_sha256"],
                "source_dataset": "google/fleurs", "source_config": "pl_pl",
                "source_split": "validation", "source_row_idx": cand["row_idx"],
                "source_recording_id": cand["recording_id"],
                "source_license": LICENSE, "source_page": DATASET_PAGE,
                "speaker_id": "REQUIRES_NATIVE_REVIEW",
                "speaker_role": "native_control",
                "speaking_style": "natural_normal",
                "reference_verified_by_human": False,
                "audio_audited_unclipped": False,
                "provider_upload_approved": False,
                "review_status": "UNVERIFIED_NEEDS_NATIVE_LISTENER",
            })
        draft = root / "sentences-source.json"
        with draft.open("x", encoding="utf-8") as out:
            json.dump(staged_rows, out, ensure_ascii=False, indent=2)
        draft.chmod(0o600)
        # Hard-link each staged inode without overwrite; unlink only OUR new
        # files if publication fails. Original user recordings untouched.
        try:
            for source, target in staged_files:
                os.link(source, target, follow_symlinks=False)
                promoted.append(target)
            os.link(draft, target_manifest, follow_symlinks=False)
        except Exception:
            for target in promoted:
                target.unlink(missing_ok=True)
            raise
    return {
        "candidate_count": len(staged_rows),
        "manifest": str(target_manifest),
        "status": "UNVERIFIED — native-speaker listening required before any Azure/Groq assessment",
        "source_existing_files_moved": 0, "speech_ai_requests": 0,
        "provider_upload_approved": False,
    }


def stage_batch(destination: Path, candidates: list[dict], batch_name: str, *,
                opener=urlopen, converter=ffmpeg_convert,
                research_root: Path | None = None) -> dict:
    """Atomically place a NEW second batch child inside the SAME private root.

    The first batch's existing source WAVs and sentences-source.json are
    never overwritten. Do not create another research root.
    """
    folder = private_root(destination, research_root=research_root)
    if not re.fullmatch(r"fleurs-batch-[0-9]{2}", batch_name):
        raise ValueError("New batch must be named fleurs-batch-02, -03, etc")
    new_folder = folder / batch_name
    if new_folder.exists() or new_folder.is_symlink():
        raise ValueError("Existing batch directory would be overwritten; use a NEW batch name")
    staging = Path(tempfile.mkdtemp(prefix=".fleurs-new-batch-", dir=folder))
    try:
        report = stage(staging, candidates, opener=opener,
                       converter=converter, research_root=staging)
        # Prevent replacing a real directory even if the initial check passed.
        if new_folder.exists() or new_folder.is_symlink():
            raise ValueError("Batch path appeared while staging; refusing overwrite")
        os.rename(staging, new_folder)
        report["manifest"] = str(new_folder / "sentences-source.json")
        report["batch_name"] = batch_name
        return report
    finally:
        if staging.exists():
            # Cleanup ONLY our temporary batch on failure.
            shutil.rmtree(staging)


def main() -> int:
    p = argparse.ArgumentParser(description="Bounded FLEURS Polish sentence candidates; no speech AI")
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Exactly PathToPolish-Private-AI/; existing audio stays untouched")
    p.add_argument("--count", type=int, default=10, help="1–12 candidates; default 10")
    p.add_argument("--offset", type=int, default=0, help="Viewer validation split row offset")
    p.add_argument("--batch-name", help="Fresh child of existing private root, e.g. fleurs-batch-02; never overwrite batch 01")
    p.add_argument("--download", action="store_true",
                   help="Explicitly fetch 1–12 public dataset audio files into the existing private folder")
    args = p.parse_args()
    try:
        private_root(args.source_dir)
        candidates = get_candidates(count=args.count, offset=args.offset)
        if args.download:
            report = (stage_batch(args.source_dir, candidates, args.batch_name)
                      if args.batch_name else stage(args.source_dir, candidates))
        else:
            report = {
                "planned_candidates": len(candidates),
                "source": "google/fleurs pl_pl validation", "audio_downloads": 0,
                "speech_ai_requests": 0,
                "approximate_seconds": round(sum(c["expected_seconds"] for c in candidates), 2),
                "ready_to_stage": True, "review_required": True,
                "planned_batch_name": args.batch_name,
            }
    except (ValueError, RuntimeError, OSError) as error:
        p.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.download:
        print("PREVIEW ONLY — no candidate WAVs downloaded or saved; no speech AI calls.")
    else:
        print("STOP — every clip remains UNVERIFIED, no provider upload approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
