#!/usr/bin/env python3
"""Offline three-engine model fit evidence, never inference or an automatic grade.

Works on existing private three_model_pilot JSONL (or later same-shaped adult
learner runs). Checks paired SHA/reference before reporting model outcomes.
Human labels are optional, but without them pronunciation suitability cannot
be established. No keys, voice/transcripts or raw provider JSON in output.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from three_model_pilot import word_error_rate

V3 = "groq-whisper-large-v3"
TURBO = "groq-whisper-large-v3-turbo"
AZURE = "azure-pl-PL-scripted"
ENGINES = (V3, TURBO, AZURE)


def review(rows: list[dict], labels: list[dict] | None = None) -> dict:
    if not isinstance(rows, list) or not rows or len(rows) > 300:
        raise ValueError("Expected 1-300 private provider result rows")
    groups: dict[str, dict[str, dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid provider result")
        sid, engine = row.get("sample_id"), row.get("engine")
        sha, reference = row.get("audio_sha256"), row.get("reference")
        if not isinstance(sid, str) or not sid or engine not in ENGINES:
            raise ValueError("Unknown sample or provider engine")
        if (not isinstance(sha, str) or len(sha) != 64 or
                any(c not in "0123456789abcdef" for c in sha)):
            raise ValueError("Missing or malformed original WAV SHA-256")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Missing Polish reference")
        if row.get("status") not in ("ok", "inconclusive"):
            raise ValueError("Invalid provider outcome")
        group = groups.setdefault(sid, {})
        if engine in group:
            raise ValueError("Duplicated provider/sample result")
        group[engine] = row
    if len(groups) > 100:
        raise ValueError("Maximum 100 paired recordings")
    for sid, group in groups.items():
        if len({r["audio_sha256"] for r in group.values()}) != 1:
            raise ValueError("Different audio bytes used for sample " + sid)
        if len({r["reference"] for r in group.values()}) != 1:
            raise ValueError("Different reference texts used for sample " + sid)

    label_by_id: dict[str, dict] = {}
    if labels is not None:
        if not isinstance(labels, list) or len(labels) != len(groups):
            raise ValueError("Human reviewer must label every compared recording")
        for label in labels:
            if not isinstance(label, dict) or not isinstance(label.get("id"), str):
                raise ValueError("Invalid independent listener label")
            sid = label["id"]
            if sid not in groups or sid in label_by_id:
                raise ValueError("Unknown or duplicate human label")
            first = next(iter(groups[sid].values()))
            if label.get("audio_sha256") != first["audio_sha256"]:
                raise ValueError("Human label WAV fingerprint mismatch")
            if (type(label.get("intelligible")) is not bool or
                    type(label.get("target_correct")) is not bool or
                    not isinstance(label.get("heard_without_reference"), str) or
                    label.get("capture_quality") not in ("clear", "noisy", "clipped", "silence")):
                raise ValueError("Complete blinded intelligibility, target and audio-quality review required")
            label_by_id[sid] = label

    result = {}
    for engine in ENGINES:
        available = [g[engine] for g in groups.values() if engine in g]
        successful = [r for r in available if r["status"] == "ok"]
        entry: dict = {
            "paired_samples_available": len(available),
            "successful_results": len(successful),
            "inconclusive_results": len(available) - len(successful),
            "missing_results": len(groups) - len(available),
        }
        if engine in (V3, TURBO):
            ref_wer = []
            human_wer = []
            for sid, group in groups.items():
                row = group.get(engine)
                if not row or row["status"] != "ok":
                    continue
                transcript = row.get("transcript")
                if not isinstance(transcript, str):
                    raise ValueError("Missing Whisper transcript in successful result")
                ref_wer.append(word_error_rate(row["reference"], transcript))
                label = label_by_id.get(sid)
                if label and label["heard_without_reference"].strip():
                    human_wer.append(word_error_rate(label["heard_without_reference"], transcript))
            entry["mean_wer_vs_intended_text_asr_only"] = _mean(ref_wer)
            entry["mean_wer_vs_blind_human_transcript_asr_only"] = _mean(human_wer)
            entry["human_transcript_pairs"] = len(human_wer)
            entry["pronunciation_quality_score"] = None
        else:
            measures: list[float] = []
            by_human: dict[str, list[float]] = {"target_correct": [], "target_not_correct": []}
            for sid, group in groups.items():
                row = group.get(AZURE)
                if not row or row["status"] != "ok":
                    continue
                raw = row.get("azure_native")
                scores = raw.get("scores") if isinstance(raw, dict) else None
                score = scores.get("AccuracyScore") if isinstance(scores, dict) else None
                if score is None:
                    continue
                if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100:
                    raise ValueError("Malformed native Azure accuracy score")
                measures.append(float(score))
                label = label_by_id.get(sid)
                if label and label["capture_quality"] == "clear":
                    by_human["target_correct" if label["target_correct"] else "target_not_correct"].append(float(score))
            entry["raw_accuracy_mean_uncalibrated"] = _mean(measures)
            entry["raw_accuracy_mean_human_target_correct_clear"] = _mean(by_human["target_correct"])
            entry["raw_accuracy_mean_human_target_incorrect_clear"] = _mean(by_human["target_not_correct"])
            entry["named_polish_phoneme_diagnosis_certified"] = False
        result[engine] = entry
    enough_humans = len(label_by_id) >= 12
    return {
        "status": "human_labelled_preliminary" if enough_humans else "insufficient_evidence_for_final_model_selection",
        "distinct_audio_samples": len(groups),
        "complete_three_engine_triplets": sum(set(g) == set(ENGINES) for g in groups.values()),
        "independent_human_labels": len(label_by_id),
        "model_results": result,
        "provisional_roles": {
            "scripted_pronunciation": AZURE,
            "accuracy_oriented_recognition": V3,
            "latency_cost_oriented_recognition": TURBO,
        },
        "decision_constraints": [
            "Whisper WER measures recognized words, never Polish phonetic quality",
            "Azure numbers are raw provider scores, not human-calibrated learner grades",
            "Use matched adult learner errors and native controls before threshold/UX grading",
            "Measure wall-clock latency and free-tier/production cost separately; neither is in these result files",
            "No automatic provider winner or background inference is selected",
        ],
    }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description="OFFLINE model-fit report. NEVER contacts Azure/Groq.")
    parser.add_argument("--results", required=True, type=Path,
                        help="Existing private three-engine JSONL; NO keys or WAV upload")
    parser.add_argument("--human-labels", type=Path, help="Optional private blind-listener labels JSON")
    args = parser.parse_args()
    try:
        rows = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
        labels = json.loads(args.human_labels.read_text(encoding="utf-8")) if args.human_labels else None
        output = review(rows, labels)
    except (OSError, ValueError, TypeError) as e:
        parser.error(str(e))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
