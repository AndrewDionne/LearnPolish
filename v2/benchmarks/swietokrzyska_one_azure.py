#!/usr/bin/env python3
"""ONE Azure pl-PL request on the existing consented adult Świętokrzyska WAV.

Default: inspect only; send requires explicit approval and pre-verified F0
free/no-paid account. Existing Azure latency results contain only aggregates,
so the old 84/100/100 cannot be split into phoneme scores.

Provider returns ordered, *unnamed* Polish phoneme scores. If the observed
sequence has exactly 13 valid, time-ordered phones, calculate a diagnostic
candidate using an independently authored (5,2,3,3) reference hypothesis.
These figures are NOT validated learner syllable grades. No server/UI changes.
Only sanitized numeric evidence is retained in a new private file.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time
import unicodedata
from typing import Callable

from speech_env import REGION, speech_credentials, _credentials_valid
from swietokrzyska_latency import checked_audio, safe_scores, WORD
from three_model_pilot import _output

_SERVER = Path(__file__).resolve().parents[1] / "server"
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))
from speech_assessment import azure_scripted_assess  # noqa: E402

LOCKED_ADULT_SHA = "0f4ff4b3d01165dc5e27fd9c10336f19aedf4aefdca430798c2b1777e5df1626"
SYLLABLES = ("Świę", "to", "krzy", "ska")
# Explicit hypothesis, NOT Azure's Polish phoneme alphabet. The first unit
# assumes /ɕ f j ɛ n/, then /t ɔ/, /k ʂ ɨ/, /s k a/. Exact counts and
# boundaries can change with nasalization/coarticulation and SDK output.
HYPOTHESIS_PHONE_COUNTS = (5, 2, 3, 3)
SCHEMA = "ptp-swietokrzyska-one-azure-phoneme-probe-v1"


def _numeric(value: object, low: float, high: float) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) and low <= value <= high else None


def _ticks(value: object, allow_zero: bool = True) -> int | None:
    if type(value) is int and (0 if allow_zero else 1) <= value <= 100_000_000:
        return value
    return None


def _is_word(text: object) -> bool:
    if not isinstance(text, str):
        return False
    normalized = unicodedata.normalize("NFC", text.strip(" \t\n.,!?;:")).casefold()
    return normalized == WORD.casefold()


def inspect_one_response(payload: object) -> dict:
    """Never return a transcript, Azure raw JSON or phoneme label.

    The four scores are a *candidate* only, never a reviewed or calibrated
    result. All 13 timed phones + exact reference word must agree before
    even publishing the tentative grouped means in private evidence.
    """
    report = {
        "status": "unavailable",
        "source": "azure-pl-PL-scripted-phoneme",
        "word_accuracy": None,
        "azure_accuracy": None,
        "fluency": None,
        "completeness": None,
        "observed_phone_count": 0,
        "phones_have_valid_scores": False,
        "phones_have_ordered_timing": False,
        "phone_name_count": 0,
        "hypothesized_counts": list(HYPOTHESIS_PHONE_COUNTS),
        "syllables": list(SYLLABLES),
        "candidate_unverified": None,
        "can_publish_learner_syllable_grades": False,
        "reason": "provider_no_result",
    }
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return report | {"reason": "provider_inconclusive"}
    raw = payload.get("raw")
    if not isinstance(raw, dict):
        return report | {"reason": "provider_no_detailed_json"}
    overall = safe_scores(raw)
    if overall is not None:
        report.update(azure_accuracy=overall["AccuracyScore"],
                      fluency=overall["FluencyScore"],
                      completeness=overall["CompletenessScore"])
    nbest = raw.get("NBest")
    if not isinstance(nbest, list) or not nbest or not isinstance(nbest[0], dict):
        return report | {"reason": "no_nbest"}
    words = nbest[0].get("Words")
    if not isinstance(words, list) or len(words) != 1 or not isinstance(words[0], dict):
        return report | {"reason": "not_exactly_one_word"}
    word = words[0]
    wa = word.get("PronunciationAssessment")
    if isinstance(wa, dict):
        report["word_accuracy"] = _numeric(wa.get("AccuracyScore"), 0, 100)
        if wa.get("ErrorType") in ("Omission", "Insertion"):
            return report | {"reason": "word_missing_or_extra"}
    if not _is_word(word.get("Word")):
        return report | {"reason": "recognized_word_mismatch"}
    phones = word.get("Phonemes")
    if not isinstance(phones, list):
        return report | {"reason": "phoneme_data_missing"}
    report["observed_phone_count"] = len(phones)
    if not (2 <= len(phones) <= 64):
        return report | {"reason": "invalid_phone_count"}

    scores = []
    intervals = []
    named = 0
    for phone in phones:
        if not isinstance(phone, dict):
            return report | {"reason": "malformed_phone"}
        assess = phone.get("PronunciationAssessment")
        score = _numeric(assess.get("AccuracyScore"), 0, 100) if isinstance(assess, dict) else None
        if score is None:
            return report | {"reason": "invalid_phone_score"}
        scores.append(score)
        if isinstance(phone.get("Phoneme"), str) and phone["Phoneme"]:
            named += 1
        offset, duration = _ticks(phone.get("Offset")), _ticks(phone.get("Duration"), False)
        if offset is None or duration is None:
            return report | {"phones_have_valid_scores": True,
                             "phone_name_count": named,
                             "reason": "phoneme_timing_missing"}
        intervals.append((offset, offset + duration))
    report["phones_have_valid_scores"] = True
    report["phone_name_count"] = named
    # Overlapping phoneme durations may occur naturally; check STARTS rather
    # than assuming gaps and transitions prove actual phone identities.
    if any(start < 0 or end > 110_000_000 or (
        i and start < intervals[i-1][0]) for i, (start, end) in enumerate(intervals)):
        return report | {"reason": "phone_timing_not_ordered"}
    report["phones_have_ordered_timing"] = True

    if len(scores) != sum(HYPOTHESIS_PHONE_COUNTS):
        return report | {"status": "phoneme_evidence_only",
                         "reason": "phone_count_differs_from_authored_hypothesis"}
    cursor = 0
    values = []
    for label, count in zip(SYLLABLES, HYPOTHESIS_PHONE_COUNTS):
        block = scores[cursor:cursor + count]
        values.append({"syllable": label,
                       "tentative_mean": round(sum(block)/len(block), 1),
                       "phone_count": count})
        cursor += count
    return report | {
        "status": "candidate_not_validated", "candidate_unverified": values,
        "reason": "unnamed_phones_cannot_validate_syllable_alignment",
    }


def _check_source(path: Path, expected_sha: str) -> dict:
    # Explicitly pin the original one adult utterance already authorized and
    # used for the 2026-10-19 tests, NOT a new recording or different speaker.
    info = checked_audio(path)
    if info["wav_sha256"] != expected_sha:
        raise ValueError("This is not the locked original Świętokrzyska recording")
    return info


def offline_review(audio: Path, saved: Path, *, expected_sha: str = LOCKED_ADULT_SHA) -> dict:
    info = _check_source(audio, expected_sha)
    if (saved.is_symlink() or not saved.is_file() or saved.suffix != ".jsonl" or
        saved.parent.resolve() != audio.parent.resolve() or
        stat.S_IMODE(saved.stat().st_mode) & 0o077 or saved.stat().st_size > 15000):
        raise ValueError("Choose an existing owner-private 0600 evidence JSONL next to the WAV")
    rows = saved.read_text(encoding="utf-8").splitlines()
    if len(rows) != 1:
        raise ValueError("Expected exactly one previously saved result")
    row = json.loads(rows[0])
    if (not isinstance(row, dict) or row.get("schema") != SCHEMA or
        row.get("audio_sha256") != info["wav_sha256"] or
        row.get("reference") != WORD or row.get("provider_requests") != 1):
        raise ValueError("Evidence does not match the exact original recording")
    return row


def run_one(
    audio: Path,
    output: Path | None = None,
    *,
    send: bool = False,
    approve_adult_audio_upload: bool = False,
    confirm_azure_f0: bool = False,
    confirm_no_paid_billing: bool = False,
    azure_key: str | None = None,
    azure_region: str | None = None,
    assessor: Callable[[bytes, str, str, str], dict] = azure_scripted_assess,
    expected_sha: str = LOCKED_ADULT_SHA,
) -> dict:
    info = _check_source(audio, expected_sha)
    if not send:
        return {
            "status": "PREVIEW_ONLY", "reference": WORD, "same_original_sha_verified": True,
            "audio_seconds": info["wav_seconds"], "azure_requests_sent": 0,
            "planned_azure_requests": 1, "groq_requests": 0,
            "note": "Only tentative syllable means if actual Azure reports exactly 13 ordered timed unnamed phones",
        }
    if not (approve_adult_audio_upload and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("One Azure upload needs adult consent, F0 and no-paid-billing confirmation")
    _credentials_valid(azure_key, azure_region)
    if output is None or output.suffix != ".jsonl" or output.parent.resolve() != audio.parent.resolve():
        raise ValueError("Choose a new private JSONL next to the original WAV")
    if output.is_symlink() or output.exists():
        raise ValueError("Output already exists; never repeat a paid/provider call to overwrite")
    with _output(output, audio.parent) as file:
        started = time.monotonic()
        try:
            payload = assessor(audio.read_bytes(), WORD, azure_key, azure_region)
            observation = inspect_one_response(payload)
        except Exception:
            observation = inspect_one_response({"status": "inconclusive"})
        elapsed = round((time.monotonic() - started) * 1000, 1)
        row = {
            "schema": SCHEMA, "reference": WORD, "audio_sha256": info["wav_sha256"],
            "audio_seconds": info["wav_seconds"], "engine": "azure-pl-PL-scripted-phoneme",
            "provider_requests": 1, "sdk_elapsed_ms": elapsed,
            "no_new_groq_or_tts_requests": True,
            **observation,
        }
        # No raw audio, transcripts, provider IDs, headers, phoneme arrays or
        # keys are saved or printed. Persist summary even if Azure is unscored.
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
        file.flush()
        os.fsync(file.fileno())
    return offline_review(audio, output, expected_sha=expected_sha)


_SAFE_ERRORS = frozenset({
    "This is not the locked original Świętokrzyska recording",
    "One Azure upload needs adult consent, F0 and no-paid-billing confirmation",
    "Choose a new private JSONL next to the original WAV",
    "Output already exists; never repeat a paid/provider call to overwrite",
    "Azure Speech key is missing or invalid; use the real regional resource key privately",
    "Azure Speech region must be germanywestcentral for this resource",
    "Choose an existing owner-private 0600 evidence JSONL next to the WAV",
    "Expected exactly one previously saved result",
    "Evidence does not match the exact original recording",
})


def main() -> int:
    p = argparse.ArgumentParser(description="ONE original Świętokrzyska Azure phoneme test, default ZERO network")
    p.add_argument("--wav", required=True, type=Path)
    p.add_argument("--report", type=Path, help="Review the already saved private one-request JSONL, no Azure call")
    p.add_argument("--send", action="store_true")
    p.add_argument("--approve-adult-audio-upload", action="store_true")
    p.add_argument("--confirm-azure-f0", action="store_true")
    p.add_argument("--confirm-no-paid-billing", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        if args.report:
            if args.send or args.output:
                p.error("--report is offline only; do not combine with --send/--output")
            result = offline_review(args.wav, args.report)
        else:
            key, region = speech_credentials() if args.send else (None, None)
            result = run_one(args.wav, args.output, send=args.send,
                approve_adult_audio_upload=args.approve_adult_audio_upload,
                confirm_azure_f0=args.confirm_azure_f0,
                confirm_no_paid_billing=args.confirm_no_paid_billing,
                azure_key=key, azure_region=region)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        message = str(exc)
        p.error(message if message in _SAFE_ERRORS else
                "Private original WAV/provider validation failed. No automatic retry; retain any saved evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
