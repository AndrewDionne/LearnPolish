#!/usr/bin/env python3
"""Owner-private preview of one combined Azure + Whisper *experimental* estimate.

No new speech calls, no user recording submitted, no credentials imported.
Read the *already saved* owner Świętokrzyska WAV + Azure and two Whisper
evidence files; verify same source WAV and independently validate both
models' matching transcription proxies. Render a minimal standalone HTML preview: colour-coded *text* of one word
and a single blended score only. No description, boxes, legend, syllable
numbers or acoustic scores. No production API/XP changes.

The arithmetic average of non-equivalent measures is NOT a calibrated
pronunciation probability. This is explicitly a product UX experiment.
"""
from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

from phonetic_similarity import SCHEMA as PROXY_SCHEMA, from_saved, write_private_html
from swietokrzyska_whisper import report as verified_source
from swietokrzyska_latency import WORD

SCHEMA = "ptp-experimental-azure-whisper-blend-preview-v1"
CLASSES = frozenset(("close", "review", "focus", "uncertain"))


def _point(value: object) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100 else None


def build_blend(proxy: object, comparison: object) -> dict:
    """Reject mismatched, incomplete or discordant provider evidence.

    Only the combined score is displayed. Internal syllable sound-unit
    estimates are mapped to *categorical* colour hints, never exposed
    as numerical syllable 'grades'.
    """
    if not isinstance(proxy, dict) or proxy.get("schema") != PROXY_SCHEMA or (
        proxy.get("reference") != WORD or not isinstance(comparison, dict) or
        comparison.get("status") != "WHISPER_PAIRED_RESULT" or
        comparison.get("reference") != WORD or comparison.get("same_audio_verified") is not True
    ):
        raise ValueError("Expected matching historic Świętokrzyska evidence")
    azure = comparison.get("azure_baseline")
    if not isinstance(azure, list) or len(azure) != 2:
        raise ValueError("Expected two prior checked Azure estimates")
    originals = []
    for row in azure:
        if not isinstance(row, dict) or not isinstance(row.get("scores"), dict):
            raise ValueError("Prior Azure accuracy missing")
        value = _point(row["scores"].get("AccuracyScore"))
        if value is None:
            raise ValueError("Prior Azure accuracy invalid")
        originals.append(value)
    if originals[0] != originals[1]:
        raise ValueError("Cannot choose between inconsistent prior Azure word estimates")
    range_ = proxy.get("overall_estimate_range")
    if not isinstance(range_, list) or len(range_) != 2:
        raise ValueError("Transcription proxy has no comparable estimates")
    low, high = [_point(v) for v in range_]
    if low is None or high is None or low != high:
        raise ValueError("Whisper models disagree: no automatic blended number")
    parts = proxy.get("syllables")
    guide = proxy.get("english_guide")
    if not isinstance(parts, list) or not isinstance(guide, dict) or (
        len(parts) != 4 or guide.get("polish") != WORD or
        not isinstance(guide.get("syllables"), list) or len(guide["syllables"]) != 4 or
        guide.get("stressIndex") != 2
    ):
        raise ValueError("Reference syllables and English guide do not match")
    labels = ("Świę", "to", "krzy", "ska")
    areas = []
    for index, (part, cue) in enumerate(zip(parts, guide["syllables"])):
        if (not isinstance(part, dict) or not isinstance(cue, dict) or
            part.get("syllable") != labels[index] or
            cue.get("polish") != labels[index] or
            not isinstance(cue.get("englishCue"), str) or not cue["englishCue"] or
            part.get("status") not in CLASSES or
            part.get("transcription_proxy_agreement") is not True):
            raise ValueError("Whisper hint alignment is ambiguous")
        areas.append({
            "polish": labels[index],
            "englishCue": cue["englishCue"],
            "hint": part["status"],
            "stress": index == 2,
        })
    if not isinstance(proxy.get("model_hypotheses"), list) or len(proxy["model_hypotheses"]) != 2:
        raise ValueError("Expected two confirmed Whisper transcriptions")
    if proxy.get("kind") != "UNVALIDATED_TRANSCRIPT_DERIVED_SOUND_UNIT_SIMILARITY":
        raise ValueError("Proxy label missing or misrepresented")
    azure_score, whisper_proxy = originals[0], low
    return {
        "schema": SCHEMA,
        "reference": WORD,
        "experimental_blended_overall": round((azure_score + whisper_proxy)/2),
        "azure_word_estimate": azure_score,
        "whisper_transcript_similarity": whisper_proxy,
        "blend_method": "equal_weight_mean_of_non_equivalent_metrics_not_calibrated",
        "syllable_hints": areas,
        "syllable_numeric_scores": None,
        "syllable_hint_basis": "Whisper transcript matching only, not acoustic syllable grading",
        "same_original_audio_verified": True,
        "new_provider_requests": 0,
        "can_publish_as_validated_pronunciation_grade": False,
        "affects_xp_or_progression": False,
    }


def load_existing(wav: Path, azure_result: Path, whisper_result: Path) -> dict:
    """Reuse existing SHA/permissions/provider-row checks without new inference."""
    proxy = from_saved(wav, azure_result, whisper_result)
    comparative = verified_source(wav, azure_result, whisper_result)
    return build_blend(proxy, comparative)


def render_html_preview(result: dict) -> str:
    """Exactly one colour-coded word and one overall score, no visible extras.

    Keep full source/provenance and numeric-vs-category validation behind the
    page; do not turn guessed Whisper sound matches into syllable grades.
    """
    if result.get("schema") != SCHEMA or result.get("reference") != WORD or (
        result.get("syllable_numeric_scores") is not None or
        result.get("can_publish_as_validated_pronunciation_grade") is not False or
        result.get("new_provider_requests") != 0
    ):
        raise ValueError("Only a zero-provider, unvalidated word-only blended prototype may render")
    parts = result.get("syllable_hints")
    if not isinstance(parts, list) or len(parts) != 4:
        raise ValueError("Expected four categorical hints")
    labels = ("Świę", "to", "krzy", "ska")
    categories = {
        "close": "closer transcription match",
        "review": "possible transcription difference",
        "focus": "transcription suggests review",
        "uncertain": "uncertain transcription match",
    }
    segments = []
    for i, (label, part) in enumerate(zip(labels, parts)):
        if not isinstance(part, dict) or part.get("polish") != label or (
            part.get("hint") not in categories or not isinstance(part.get("englishCue"), str) or
            not part["englishCue"] or part.get("stress") is not (i == 2)
        ):
            raise ValueError("Syllable hint is missing or mismatched")
        category = part["hint"]
        segments.append(
            '<span class="syllable '+category+'" aria-label="' +
            html.escape(label+', '+categories[category], quote=True) +
            '">' + html.escape(label) + '</span>'
        )
    blend = result.get("experimental_blended_overall")
    azure = _point(result.get("azure_word_estimate"))
    whisper = _point(result.get("whisper_transcript_similarity"))
    if type(blend) is not int or not 0 <= blend <= 100 or azure is None or whisper is None or (
        blend != round((azure + whisper)/2)
    ):
        raise ValueError("Blended estimate was not derived from the documented scores")
    # This is intentionally a visual review with NO visible methodology,
    # controls, footnotes, labels, cards, badges or syllable percentages.
    # Experimental method remains in the validated private JSON report.
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Świętokrzyska · pronunciation preview</title>
<style>
:root{{font-family:system-ui,-apple-system,sans-serif;color:#1c3436;background:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100svh;display:grid;place-items:center;padding:20px}}
main{{display:flex;flex-direction:column;align-items:center;gap:26px;max-width:100%}}
.word{{display:flex;justify-content:center;align-items:baseline;white-space:nowrap;margin:0;
font-size:clamp(24px,6.4vw,54px);line-height:1.16;font-weight:750;letter-spacing:-.025em}}
.syllable{{display:inline;color:#1c3436}}
.syllable.close{{color:#237451}}
.syllable.review{{color:#ae740e}}
.syllable.focus{{color:#bf3d49}}
.syllable.uncertain{{color:#667784}}
.score{{display:block;font-size:clamp(42px,8vw,64px);line-height:1.1;font-weight:770;
letter-spacing:-.045em;font-variant-numeric:tabular-nums;color:#1c3436}}
</style>
</head>
<body><main aria-label="Experimental blended pronunciation preview">
<h1 class="word" aria-label="Świętokrzyska, syllables colour-coded using Whisper transcript hints">{''.join(segments)}</h1>
<output class="score" aria-label="Experimental combined score: {blend} out of 100">{blend}/100</output>
</main></body></html>"""

def main() -> int:
    p = argparse.ArgumentParser(description="Private 50/50 Azure + Whisper UX preview from ALREADY SAVED Świętokrzyska results; zero calls")
    p.add_argument("--existing-sample", action="store_true",
                   help="Use the already assessed 2026-10-19 adult Świętokrzyska evidence; make one private HTML preview")
    p.add_argument("--wav", type=Path)
    p.add_argument("--azure-result", type=Path)
    p.add_argument("--whisper-result", type=Path)
    p.add_argument("--html-output", type=Path, help="NEW private, local .html preview; never overwrites")
    args = p.parse_args()
    if args.existing_sample:
        if any((args.wav, args.azure_result, args.whisper_result, args.html_output)):
            p.error("--existing-sample cannot be combined with manual paths")
        folder = Path(__file__).resolve().parents[2] / "PathToPolish-Private-AI" / "swietokrzyska-01"
        wav = folder / "ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav"
        azure_result = folder / "azure-compare-01.jsonl"
        whisper_result = folder / "whisper-01.jsonl"
        output = folder / "blended-preview-02.html"
    else:
        if not all((args.wav, args.azure_result, args.whisper_result)):
            p.error("Supply --wav, --azure-result and --whisper-result, or use --existing-sample")
        wav,azure_result,whisper_result,output = (
            args.wav, args.azure_result, args.whisper_result, args.html_output
        )
    try:
        result = load_existing(wav, azure_result, whisper_result)
        if output:
            write_private_html(output, wav, render_html_preview(result))
            result["private_preview_created"] = True
            result["preview_name"] = output.name
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError):
        p.error("Private original audio/evidence does not match, models disagree, or preview output already exists; no provider called")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
