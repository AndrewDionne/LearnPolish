#!/usr/bin/env python3
"""Owner-private preview of one combined Azure + Whisper *experimental* estimate.

No new speech calls, no user recording submitted, no credentials imported.
Read the *already saved* owner Świętokrzyska WAV + Azure and two Whisper
evidence files; verify same source WAV and independently validate both
models' matching transcription proxies. Render a compact standalone HTML
preview: one blended overall number; colour-only syllable hints (never
numbers or acoustic scores for syllables). No production API/XP changes.

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
    colors = {"close": "closer match", "review": "worth reviewing",
              "focus": "possible mismatch", "uncertain": "uncertain"}
    html_parts = []
    for i, (label, part) in enumerate(zip(labels, parts)):
        if not isinstance(part, dict) or part.get("polish") != label or (
            part.get("hint") not in colors or not isinstance(part.get("englishCue"), str) or
            not part["englishCue"] or part.get("stress") is not (i == 2)
        ):
            raise ValueError("Syllable hint is missing or mismatched")
        category = part["hint"]
        html_parts.append(
            '<span class="sound '+category+'" aria-label="'+html.escape(label+', '+colors[category],quote=True)+'">'
            '<span class="polish">'+html.escape(label)+'</span>'
            '<span class="cue" lang="en">'+html.escape(part["englishCue"])+( ' · stress' if i==2 else '')+'</span>'
            '</span>'
        )
    blend = result.get("experimental_blended_overall")
    azure = _point(result.get("azure_word_estimate"))
    whisper = _point(result.get("whisper_transcript_similarity"))
    if type(blend) is not int or not 0 <= blend <= 100 or azure is None or whisper is None or (
        blend != round((azure + whisper)/2)
    ):
        raise ValueError("Blended estimate was not derived from the documented scores")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Path to Polish · Combined feedback experiment</title>
<style>
:root{{font-family:system-ui,-apple-system,sans-serif;background:#f6f9f7;color:#183d41}}
*{{box-sizing:border-box}}body{{max-width:760px;margin:0 auto;padding:clamp(18px,4vw,42px);line-height:1.45}}
header p{{font-size:12px;letter-spacing:.07em;font-weight:750;color:#526a71}}
h1{{font-size:clamp(1.4rem,3vw,1.9rem);margin:0 0 6px}}
.description{{font-size:14px;color:#546d71;margin:0 0 22px}}
.card{{background:#fff;border:1px solid #d8e8df;border-radius:20px;padding:clamp(16px,4vw,30px);box-shadow:0 10px 40px #164b3410}}
.guide-label{{font-size:12px;display:flex;align-items:center;gap:8px;justify-content:flex-end;margin-bottom:26px;cursor:pointer;font-weight:650}}
#guide{{width:18px;height:18px;accent-color:#237365}}
.word{{display:flex;justify-content:center;gap:0;max-width:100%;margin:12px 0 26px;align-items:flex-start}}
.sound{{display:inline-flex;flex-direction:column;align-items:center;min-width:0;text-align:center}}
.sound .polish{{font-size:clamp(26px,5.6vw,48px);font-weight:750;letter-spacing:-1.3px;line-height:1.18;
white-space:nowrap;border-radius:6px;padding:3px 1px}}
.sound .cue{{display:none;font-size:clamp(10px,1.8vw,13px);white-space:nowrap;color:#47656a;font-weight:650;padding:6px 2px 0}}
.card:has(#guide:checked) .word .cue{{display:inline}}
.sound.close .polish{{background:#cee9d9;color:#195f3c}}
.sound.review .polish{{background:#ffebbb;color:#754b10}}
.sound.focus .polish{{background:#f7cbca;color:#882e31}}
.sound.uncertain .polish{{background:#e2e7ec;color:#43545b}}
.score-heading{{font-size:13px;color:#425e62;font-weight:700;text-align:center;margin:0}}
.score{{text-align:center;font-size:clamp(56px,12vw,74px);font-weight:800;letter-spacing:-.055em;line-height:1.15;
font-variant-numeric:tabular-nums}}
.score small{{font-size:20px;letter-spacing:0;color:#577074;font-weight:550}}
.caveat{{text-align:center;max-width:425px;margin:10px auto 26px;color:#587075;font-size:12px}}
details{{border-top:1px solid #e4eee8;padding-top:13px;font-size:13px;color:#425d62}}
summary{{cursor:pointer;font-weight:700;min-height:34px}}
summary:focus-visible,#guide:focus-visible{{outline:3px solid #19816d;outline-offset:3px}}
details dl{{display:grid;grid-template-columns:1fr auto;gap:8px;margin:11px 0 0}}
details dt,details dd{{margin:0}}
details dd{{font-variant-numeric:tabular-nums;font-weight:700}}
.legend{{font-size:12px;color:#4b636a;display:flex;flex-wrap:wrap;gap:9px 16px;margin:18px 0 0}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:4px;vertical-align:middle}}
.dot.close{{background:#6fad89}}.dot.review{{background:#e6b55c}}
.dot.focus{{background:#db8080}}.dot.uncertain{{background:#a3b0bb}}
footer{{font-size:12px;color:#5b757a;margin-top:20px}}
@media(max-width:380px){{.card{{padding:16px 9px}}.sound .polish{{font-size:clamp(21px,6.6vw,29px)}}.sound .cue{{font-size:9px;padding-inline:1px}}}}
</style>
</head>
<body>
<header><p>PATH TO POLISH · PRIVATE UX EXPERIMENT</p>
<h1>Combined pronunciation feedback</h1>
<p class="description">One overall estimate, plus colour-only hints from Whisper.</p></header>
<main><section class="card">
<label for="guide" class="guide-label">Pronunciation guide <input id="guide" type="checkbox"></label>
<div class="word" role="group" aria-label="Świętokrzyska. Colours suggest possible transcript mismatches.">
{''.join(html_parts)}
</div>
<p class="score-heading">Combined estimate · experimental</p>
<div class="score" aria-label="Experimental blend {blend} out of 100">{blend}<small>/100</small></div>
<p class="caveat">Equal parts Azure accuracy and Whisper text similarity. Not a verified pronunciation grade.</p>
<details><summary>How this estimate was calculated</summary>
<dl><dt>Azure word accuracy (recording)</dt><dd>{azure:g}/100</dd>
<dt>Whisper text similarity (transcription)</dt><dd>{whisper:g}/100</dd>
<dt>Combined 50/50 average</dt><dd>{blend}/100</dd></dl>
<p>Both inputs assess different things. This average is a UX experiment, not a calibrated acoustic score.</p>
<p>Coloured syllables are reading-based practice hints, not measured syllable grades. No segment percentages are shown.</p>
</details>
</section>
<p class="legend"><span><i class="dot close"></i>Closer match</span>
<span><i class="dot review"></i>Worth reviewing</span>
<span><i class="dot focus"></i>Possible mismatch</span>
<span><i class="dot uncertain"></i>Uncertain</span></p>
</main>
<footer>Same saved adult recording and provider results. No new Azure, Whisper, recording, transcript or network request. The ordinary Speak experience is unchanged.</footer>
</body></html>"""


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
        output = folder / "blended-preview-01.html"
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
