#!/usr/bin/env python3
"""Re-evaluate saved Groq JSONL against an immutable WAV manifest, offline.

No API keys, Groq calls, storage mutations or invented pronunciation grades.
`recognized_expected_words` is the OLD strict whole-reference equality
field; use separate `reference_present` for contiguous target-word presence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark import (load_manifest, polish_match, polish_target_present,
                       read_audio_metadata)

MODELS = ("whisper-large-v3", "whisper-large-v3-turbo")


def review(manifest: Path, result_path: Path) -> dict:
    samples = load_manifest(manifest)
    if len(samples) > 100:
        raise ValueError("Too many source files for offline review")
    expected = {}
    for sample in samples:
        if sample.audio_sha256 is None:
            raise ValueError("Immutable manifest WAV SHA-256 is required: " + sample.id)
        if sample.audio.is_symlink():
            raise ValueError("Symlinked WAVs are not permitted")
        audio = read_audio_metadata(sample.audio)
        if audio["audio_sha256"] != sample.audio_sha256:
            raise ValueError("Source WAV content differs from locked manifest: " + sample.id)
        expected[sample.id] = (sample, audio)

    rows = []
    seen = set()
    for line_number, line in enumerate(result_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("Each JSONL row must be an object")
        sample_id, model = row.get("id"), row.get("model")
        if sample_id not in expected or model not in MODELS:
            raise ValueError("Unknown sample id or model on result line " + str(line_number))
        key = (sample_id, model)
        if key in seen:
            raise ValueError("Duplicate model/sample result: " + str(key))
        seen.add(key)
        sample, metadata = expected[sample_id]
        if (row.get("engine") != "groq-" + model or
                row.get("audio_sha256") != metadata["audio_sha256"] or
                row.get("reference") != sample.reference or
                abs(float(row.get("audio_seconds", -100)) - metadata["seconds"]) > 0.001):
            raise ValueError("Result does not match locked source audio/reference: " + str(key))
        if row.get("status") not in ("ok", "inconclusive"):
            raise ValueError("Unknown result status on line " + str(line_number))
        transcript = row.get("transcript")
        if not isinstance(transcript, str):
            raise ValueError("Missing provider transcript on line " + str(line_number))
        if row.get("pronunciation_score", None) is not None:
            raise ValueError("Groq ASR results cannot carry a pronunciation grade")
        exact = polish_match(sample.reference, transcript) if transcript else None
        present = polish_target_present(sample.reference, transcript) if transcript else None
        rows.append({
            "id": sample_id, "reference": sample.reference, "model": model,
            "status": row["status"], "transcript": transcript,
            "reference_exact_match": exact,
            "reference_present": present,
            "legacy_recognized_expected_words": row.get("recognized_expected_words"),
        })

    model_stats = []
    for model in MODELS:
        subset = [x for x in rows if x["model"] == model]
        model_stats.append({
            "model": model,
            "responses": len(subset),
            "reference_present": sum(x["reference_present"] is True for x in subset),
            "reference_exact_match": sum(x["reference_exact_match"] is True for x in subset),
            "missing_responses": len(samples) - len(subset),
        })

    return {
        "status": "offline-ASR-evidence-only",
        "expected_samples": len(samples),
        "processed_results": len(rows),
        "complete_matrix": len(rows) == len(samples) * len(MODELS),
        "models": model_stats,
        "samples": rows,
        "interpretation": [
            "reference_exact_match compares the FULL transcript with the written reference.",
            "reference_present checks for contiguous exact word(s) within additional recognized text, without fuzzy spelling or pronunciation inference.",
            "A reference word in a transcript does NOT prove native or learner pronunciation quality.",
            "The saved recordings are exceptionally short native speech controls; model selection requires longer real audio and independent human evidence.",
        ],
        "network_requests": 0,
        "new_audio_uploads": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review saved Groq Polish transcripts offline")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = review(args.manifest, args.results)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
