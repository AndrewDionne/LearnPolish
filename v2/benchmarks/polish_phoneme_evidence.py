#!/usr/bin/env python3
"""Offline, privacy-preserving inspection of Azure pl-PL score STRUCTURE.

This is NOT a syllable scoring algorithm. Polish Azure supports word and
phoneme accuracy but does not publish Polish phoneme names/syllable groups.
Before authoring any alignment scheme, inspect the actual SDK result from
an already explicitly approved private local benchmark. The command never
imports Azure, opens a socket, uploads audio or prints transcript/phonemes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat


def _score(value: object) -> float | None:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return float(value)


def inspect_raw(raw: object) -> dict:
    """Allowlisted numerical/structural evidence, no guessed syllable scores."""
    no = {"status": "insufficient_evidence", "syllable_scores": None,
          "phoneme_score_count": 0, "has_ordered_phoneme_scores": False,
          "native_syllable_score_count": 0,
          "can_publish_syllable_scores": False}
    if not isinstance(raw, dict):
        return no
    nbest = raw.get("NBest")
    if not isinstance(nbest, list) or len(nbest) < 1 or not isinstance(nbest[0], dict):
        return no
    words = nbest[0].get("Words")
    if not isinstance(words, list) or len(words) != 1 or not isinstance(words[0], dict):
        return dict(no, reason="single_word_alignment_not_available")
    word = words[0]
    phones = word.get("Phonemes")
    syllables = word.get("Syllables")
    scores = []
    if isinstance(phones, list) and 2 <= len(phones) <= 64:
        for unit in phones:
            pa = unit.get("PronunciationAssessment") if isinstance(unit, dict) else None
            score = pa.get("AccuracyScore") if isinstance(pa, dict) else None
            if _score(score) is None:
                break
            scores.append(float(score))
    has_phones = isinstance(phones, list) and 2 <= len(phones) <= 64 and len(scores) == len(phones)
    native_count = 0
    if isinstance(syllables, list) and 1 <= len(syllables) <= 12 and all(
        isinstance(v, dict) and isinstance(v.get("PronunciationAssessment"), dict)
        and _score(v["PronunciationAssessment"].get("AccuracyScore")) is not None
        for v in syllables
    ):
        native_count = len(syllables)
    # Azure's published en-US-only locale contract prevents treating native
    # syllable group fields as validated pl-PL reference-aligned teaching units.
    return {
        "status": "structural_evidence_only" if has_phones or native_count else "insufficient_evidence",
        "phoneme_score_count": len(scores) if has_phones else 0,
        "has_ordered_phoneme_scores": has_phones,
        "has_named_phonemes": bool(has_phones and all(
            isinstance(unit.get("Phoneme"), str) and bool(unit["Phoneme"])
            for unit in phones
        )),
        "native_syllable_score_count": native_count,
        "can_publish_syllable_scores": False,
        "syllable_scores": None,
        "reason": "requires_reviewed_alignment_and_human_calibration",
    }


def inspect_private_result(path: Path) -> dict:
    """Only read already-owned private ignored benchmark files; no overwrites."""
    real = path.absolute()
    if path.is_symlink() or not path.is_file() or path.suffix != ".json" or path.stat().st_size > 400_000:
        raise ValueError("Choose an existing private non-symlink Azure result JSON (max 400 KB)")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private evidence file must be chmod 600")
    if path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
        raise ValueError("Private evidence directory must be chmod 700")
    if "/PathToPolish-Private-AI/" not in str(real):
        raise ValueError("Use only the locally ignored PathToPolish-Private-AI directory")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("engine") != "azure-pl-PL-scripted" or data.get("locale") != "pl-PL":
        raise ValueError("Result is not a private pl-PL Azure scripted assessment")
    return inspect_raw(data.get("raw_azure_json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="OFFLINE ONLY: inspect Azure Polish phoneme score structure")
    parser.add_argument("--saved-private-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = inspect_private_result(args.saved_private_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(evidence, indent=2))
    print("OFFLINE ONLY: 0 audio uploads, 0 Azure/Groq requests, 0 syllable grades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
