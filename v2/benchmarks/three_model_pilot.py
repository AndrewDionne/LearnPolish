#!/usr/bin/env python3
"""ONE bounded exploratory Polish speech comparison: both Whisper models + Azure.

This is a PUBLIC FLEURS dataset *technical smoke test*, not an independently
certified native gold-standard pronunciation benchmark. Deliberately does NOT
mutate source review approvals or bypass production Azure pilot's human gate.

Default: offline PREVIEW. Actual send needs explicit user flags, existing
Groq/Azure FREE plans, keys in LOCAL environment, and output in ignored folder.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from audio_quality_review import measure_wav
from azure_pilot import azure_scripted_assess
from benchmark import extract_azure_native, read_audio_metadata
from groq_pilot import MODELS, transcribe
from research_paths import check_research_location

MAX_SAMPLES = 2
REGION = "germanywestcentral"


def norm_words(value: str) -> list[str]:
    return re.sub(r"[^\wąćęłńóśźż]+", " ", value.casefold(), flags=re.UNICODE).split()


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Ordinary Levenshtein WER for transcripts, NOT pronunciation scoring."""
    a, b = norm_words(reference), norm_words(hypothesis)
    if not a:
        raise ValueError("Reference sentence is empty")
    distances = list(range(len(b) + 1))
    for i, token in enumerate(a, 1):
        next_row = [i]
        for j, word in enumerate(b, 1):
            next_row.append(min(next_row[j - 1] + 1,
                                distances[j] + 1,
                                distances[j - 1] + (token != word)))
        distances = next_row
    return round(distances[-1] / len(a), 4)


def choose_source(manifest: Path, sample_ids: tuple[str, ...] = (),
                  count: int = 2) -> list[dict]:
    check_research_location(manifest)
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Use existing real FLEURS private manifest")
    if stat.S_IMODE(manifest.parent.stat().st_mode) & 0o077:
        raise ValueError("Research folder must be chmod 700")
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Expected FLEURS manifest with 1–100 rows")
    if not 1 <= count <= MAX_SAMPLES or len(sample_ids) > count:
        raise ValueError("First exploratory run limited to ONE or TWO recordings")
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("Duplicate sample IDs")
    selected = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid manifest row")
        sid, filename, ref = row.get("id"), row.get("audio"), row.get("reference")
        if (not isinstance(sid, str) or not re.fullmatch(r"fleurs-pl-val-\d{5}", sid) or
                sid in seen or not isinstance(filename, str) or
                filename != sid + ".wav" or
                not isinstance(ref, str) or len(norm_words(ref)) < 4):
            raise ValueError("Only original full Polish FLEURS sentence rows are allowed")
        seen.add(sid)
        if (row.get("source_dataset"), row.get("source_config"), row.get("source_split")) != (
                "google/fleurs", "pl_pl", "validation"):
            raise ValueError("This experimental path is ONLY for known public FLEURS Polish validation clips")
        if row.get("source_license") != (
                "CC BY 4.0 — Google FLEURS (confirm third-party service use before upload)"):
            raise ValueError("Expected public CC BY 4.0 FLEURS source provenance")
        path = manifest.parent / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("FLEURS source WAV missing or symlink")
        audio = read_audio_metadata(path)
        if row.get("audio_sha256") != audio["audio_sha256"]:
            raise ValueError("FLEURS source checksum changed; stop without any uploads")
        # A weak candidate does not invalidate the other public recordings.
        # Skip it, never silently upload silence or wrong-duration media.
        if not audio["valid_signal"] or not 5 <= audio["seconds"] <= 15:
            continue
        acoustic = measure_wav(path)
        selected.append({
            "id": sid, "reference": ref, "path": path,
            "sha256": audio["audio_sha256"], "seconds": audio["seconds"],
            "acoustic": acoustic,
            "selection_quality_score": (
                -100 if "possible_clipping" in acoustic["flags"] else 0
            ) + (-50 if "low_signal_level" in acoustic["flags"] else 0
            ) + (-10 if "long_low_level_sections" in acoustic["flags"] else 0
            ) - abs(acoustic["rms_dbfs"] - (-21)),
        })
    if sample_ids:
        requested = set(sample_ids)
        if not requested.issubset(seen) or len(requested) != count:
            raise ValueError("Supply exactly --count valid unique FLEURS sample IDs")
        return [x for sample in sample_ids for x in selected if x["id"] == sample]
    good = sorted(selected, key=lambda x: x["selection_quality_score"], reverse=True)
    if len(good) < count:
        raise ValueError("Not enough source recordings")
    # Source technical ranking is NOT a pronunciation or microphone-quality
    # guarantee: the user heard poor audio even on clips with plausible RMS.
    return good[:count]


def preview(manifest: Path, *, sample_ids: tuple[str, ...] = (),
            count: int = 2, max_requests: int = 6,
            max_groq_billed_seconds: float = 60,
            max_azure_audio_seconds: float = 30) -> tuple[list[dict], dict]:
    clips = choose_source(manifest, sample_ids=sample_ids, count=count)
    calls = len(clips) * 3
    groq_billed = sum(max(10.0, c["seconds"]) * 2 for c in clips)
    azure_seconds = sum(c["seconds"] for c in clips)
    if (max_requests < calls or max_requests > 6 or
            groq_billed > max_groq_billed_seconds or
            azure_seconds > max_azure_audio_seconds or
            max_azure_audio_seconds > 30):
        raise ValueError("Three-model preview exceeds bounded request/Groq/Azure audio budgets")
    return clips, {
        "status": "PREVIEW_ONLY",
        "purpose": "exploratory_3_model_comparison_NOT_NATIVE_CERTIFICATION",
        "models": [*MODELS, "azure-pl-PL-scripted"],
        "sample_ids": [c["id"] for c in clips],
        "source_audio_sha256": {c["id"]: c["sha256"] for c in clips},
        "acoustic_hints": {c["id"]: c["acoustic"] for c in clips},
        "source_human_verified": False,
        "planned_calls": calls,
        "planned_groq_billed_seconds": round(groq_billed, 2),
        "planned_azure_audio_seconds": round(azure_seconds, 2),
        "network_calls_performed": 0,
        "what_it_can_test": "ASR transcripts/WER; Azure raw scores on identical unprocessed audio",
        "what_it_cannot_prove": "native pronunciation accuracy, phoneme diagnosis, calibrated grading",
    }


def _output(path: Path, source_dir: Path):
    check_research_location(path)
    if path.parent.resolve() != source_dir.resolve() or path.suffix != ".jsonl":
        raise ValueError("Result must be a new .jsonl DIRECTLY inside existing private source folder")
    if path.is_symlink() or path.exists():
        raise ValueError("Output exists. Pick a NEW private filename; never overwrite partial tests")
    if path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
        raise ValueError("Private output parent must be chmod 700")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    return os.fdopen(fd, "w", encoding="utf-8")


def run(manifest: Path, *, sample_ids: tuple[str, ...] = (),
        count: int = 2, max_requests: int = 6,
        max_groq_billed_seconds: float = 60, max_azure_audio_seconds: float = 30,
        send: bool = False, approve_public_audio_upload: bool = False,
        confirm_groq_free: bool = False, confirm_azure_f0: bool = False,
        confirm_no_paid_billing: bool = False, output: Path | None = None,
        groq_key: str | None = None, azure_key: str | None = None,
        azure_region: str | None = None,
        transcriber: Callable | None = None, assessor: Callable | None = None) -> dict:
    clips, report = preview(manifest, sample_ids=sample_ids, count=count,
                            max_requests=max_requests,
                            max_groq_billed_seconds=max_groq_billed_seconds,
                            max_azure_audio_seconds=max_azure_audio_seconds)
    if not send:
        return report
    if not (approve_public_audio_upload and confirm_groq_free
            and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("To SEND public FLEURS audio explicitly affirm: dataset rights/upload, Groq Free, Azure F0, no paid billing")
    if not groq_key or not azure_key or azure_region != REGION:
        raise ValueError("Set GROQ_API_KEY, AZURE_SPEECH_KEY and AZURE_SPEECH_REGION=germanywestcentral privately in your local shell")
    if output is None:
        raise ValueError("Choose a new private --output JSONL filename")
    if assessor is None:
        try:
            import azure.cognitiveservices.speech  # noqa: F401 - fail BEFORE Groq uploads
        except ImportError:
            raise RuntimeError("Install local Azure Speech SDK first: python3 -m pip install azure-cognitiveservices-speech") from None
        assessor = azure_scripted_assess
    if transcriber is None:
        transcriber = lambda path, model, key: transcribe(path, model, key, transport="curl")
    attempted = 0
    successes = 0
    # Each successful model result is immediately durable in private JSONL,
    # including Azure raw response. Stop on first provider failure. NO retries.
    with _output(output, manifest.parent) as stream:
        for clip in clips:
            for model in MODELS:
                attempted += 1
                transcript = transcriber(clip["path"], model, groq_key)
                if not isinstance(transcript, str):
                    raise ValueError("Groq returned no usable transcript")
                row = {
                    "sample_id": clip["id"], "engine": "groq-" + model,
                    "audio_sha256": clip["sha256"], "reference": clip["reference"],
                    "transcript": transcript, "wer": word_error_rate(clip["reference"], transcript),
                    "pronunciation_grade": None, "status": "ok" if transcript else "inconclusive",
                    "native_speech_human_verified": False,
                    "exploratory_only": True,
                }
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                successes += 1
            attempted += 1
            evidence = assessor(clip["path"], clip["reference"], azure_key, azure_region)
            if not isinstance(evidence, dict) or evidence.get("status") not in ("ok", "inconclusive"):
                raise ValueError("Azure assessment returned malformed evidence")
            raw = evidence.get("raw_azure_json")
            native = extract_azure_native(raw) if isinstance(raw, dict) else {
                "status": "inconclusive", "reason": evidence.get("reason")}
            row = {
                "sample_id": clip["id"], "engine": "azure-pl-PL-scripted",
                "audio_sha256": clip["sha256"], "reference": clip["reference"],
                "azure_native": native, "raw_azure_json": raw,
                "status": evidence["status"],
                "native_speech_human_verified": False,
                "exploratory_only": True,
                "assessment_is_human_calibrated": False,
            }
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            successes += 1
    return dict(report, status="EXPLORATORY_COMPLETE",
                network_calls_performed=attempted,
                persisted_result_rows=successes, output=str(output))


def summarize(output: Path) -> dict:
    """Summarize a partial or complete private JSONL without uploading it."""
    rows = [json.loads(x) for x in output.read_text(encoding="utf-8").splitlines() if x.strip()]
    result = []
    for row in rows:
        entry = {"sample_id": row["sample_id"], "engine": row["engine"], "status": row["status"]}
        if row["engine"].startswith("groq-"):
            entry["wer_recognition_only"] = row.get("wer")
            entry["transcript"] = row.get("transcript")
        else:
            native = row.get("azure_native") or {}
            entry["azure_scores_uncalibrated"] = native.get("scores") if isinstance(native, dict) else None
            entry["transcript"] = native.get("transcript") if isinstance(native, dict) else None
        result.append(entry)
    return {"completed_model_rows": len(rows), "comparison": result,
            "important": "ASR word error rate is NOT pronunciation accuracy; Azure scores NOT native-calibrated"}


def main() -> int:
    p = argparse.ArgumentParser(description="Exploratory same-file V3/Turbo/Azure Polish pilot; NO UPLOAD by default")
    p.add_argument("--manifest", type=Path, help="Existing private FLEURS sentences-source.json")
    p.add_argument("--sample-id", nargs="+", default=[], help="Optional exact FLEURS IDs; one or two")
    p.add_argument("--count", type=int, default=2, help="One or two unmodified WAVs, default two")
    p.add_argument("--max-requests", type=int, default=6)
    p.add_argument("--max-groq-billed-seconds", type=float, default=60)
    p.add_argument("--max-azure-audio-seconds", type=float, default=30)
    p.add_argument("--send", action="store_true", help="ACTUALLY submit selected public FLEURS audio to all 3 engines")
    p.add_argument("--approve-public-audio-upload", action="store_true", help="I reviewed rights and approve public dataset recordings being sent to both providers")
    p.add_argument("--confirm-groq-free", action="store_true", help="Groq Free Plan and remaining free usage checked")
    p.add_argument("--confirm-azure-f0", action="store_true", help="Existing Azure Speech resource is F0")
    p.add_argument("--confirm-no-paid-billing", action="store_true", help="I checked both providers are not in paid/auto-topup mode")
    p.add_argument("--output", type=Path, help="NEW private JSONL for raw model evidence")
    p.add_argument("--summarize", type=Path, help="Read results JSONL offline, no providers")
    args = p.parse_args()
    try:
        if args.summarize:
            result = summarize(args.summarize)
        else:
            if args.manifest is None:
                raise ValueError("Select --manifest or --summarize")
            result = run(args.manifest, sample_ids=tuple(args.sample_id), count=args.count,
                         max_requests=args.max_requests,
                         max_groq_billed_seconds=args.max_groq_billed_seconds,
                         max_azure_audio_seconds=args.max_azure_audio_seconds,
                         send=args.send, approve_public_audio_upload=args.approve_public_audio_upload,
                         confirm_groq_free=args.confirm_groq_free,
                         confirm_azure_f0=args.confirm_azure_f0,
                         confirm_no_paid_billing=args.confirm_no_paid_billing,
                         output=args.output, groq_key=os.environ.get("GROQ_API_KEY"),
                         azure_key=os.environ.get("AZURE_SPEECH_KEY"),
                         azure_region=os.environ.get("AZURE_SPEECH_REGION"))
            if args.send and args.output:
                result["summary"] = summarize(args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, RuntimeError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
