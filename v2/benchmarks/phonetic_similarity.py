#!/usr/bin/env python3
"""Offline Polish sound-unit similarity and clickable syllable-highlighted review.

A reproducible ORTHOGRAPHIC/TRANSCRIPTION proxy, never an acoustic phoneme
measurement. A Whisper hypothesis is NOT a phonetic transcript. The estimated
substitutions do not establish which sounds a speaker actually articulated.

Inputs: immutable private Świętokrzyska WAV, saved two-call Azure evidence,
saved two-call Groq Whisper evidence. Zero inference/network always.
Results can be displayed as private, standalone, interactive HTML with
keyboard-accessible <details>; no JS, analytics, audio or third-party assets.
No score affects lesson progression or XP.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
from pathlib import Path
import stat
from typing import Sequence

from swietokrzyska_whisper import report as compare_providers

WORD = "Świętokrzyska"
# This first validated spelling segmentation is deliberately explicit. No
# generic Polish syllabification claims until a separately reviewed lexicon.
SYLLABLES = ("Świę", "to", "krzy", "ska")
SOUND_GROUPS = (
    ("ś", "w / v", "ię"),
    ("t", "o"),
    ("k", "rz", "y"),
    ("s", "k", "a"),
)
SCHEMA = "ptp-transcript-phonetic-proxy-v1"
CONTRASTS: dict[frozenset[str], float] = {
    frozenset(("ś", "s")): 0.55,
    frozenset(("ć", "cz")): 0.55,
    frozenset(("ź", "ż")): 0.55,
    frozenset(("ż", "sz")): 0.50,
    frozenset(("ę", "e")): 0.45,
    frozenset(("ą", "o")): 0.45,
    frozenset(("i", "y")): 0.60,
    frozenset(("j", "i")): 0.40,
    frozenset(("cz", "sz")): 0.55,
}
ALLOWED = frozenset("aąbcćdeęfghijklłmnńoópqrsśtuvwxyzźż")
MULTIGRAPHS = ("dź", "dż", "dzi", "dz", "cz", "sz", "rz", "ch", "ci", "si", "zi", "ni")
PHONES = {"w": "v", "v": "v", "rz": "ż", "ż": "ż",
          "ó": "u", "ch": "h", "ci": "ć", "si": "ś",
          "zi": "ź", "ni": "ń", "dzi": "dź"}


def sound_units(text: str) -> list[str]:
    """Approximate Polish sound-grapheme units (NOT reliable IPA).

    Strip spaces between hypothesized words (ASR may split one target).
    v/w share one value. Only a few ubiquitous Polish digraphs are
    normalized; unfamiliar or mixed-language transcriptions are uncertain.
    """
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError("Expected a short nonempty Polish hypothesis")
    clean = text.casefold().strip().replace(" ", "").replace("-", "")
    if not clean or any(char not in ALLOWED for char in clean):
        raise ValueError("Unsupported letters in Polish sound-unit proxy")
    result: list[str] = []
    pos = 0
    while pos < len(clean):
        group = next((g for g in MULTIGRAPHS if clean.startswith(g, pos)), clean[pos])
        unit = PHONES.get(group, group)
        # After voiceless consonants in standard Polish, written rz is
        # devoiced; the same lexical spelling gets the same proxy every time.
        if group == "rz" and result and result[-1] in ("k", "p", "t", "f", "h"):
            unit = "sz"
        result.append(unit)
        pos += len(group)
    return result


def substitution(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return CONTRASTS.get(frozenset((a, b)), 1.0)


def align(expected: Sequence[tuple[str, int]], heard: Sequence[str]) -> list[dict]:
    """Global unit alignment, mapping deletions/substitutions to target syllables.

    Insertions attach to the adjacent reference segment; tie-breakers are
    deterministic. No audio timings or forced alignment are fabricated.
    """
    n, m = len(expected), len(heard)
    costs = [[0.0] * (m + 1) for _ in range(n + 1)]
    trace = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        costs[i][0] = i
        trace[i][0] = "delete"
    for j in range(1, m + 1):
        costs[0][j] = j
        trace[0][j] = "insert"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = substitution(expected[i-1][0], heard[j-1])
            candidates = ((costs[i-1][j-1] + sub, 0, "match" if sub == 0 else "substitute"),
                          (costs[i-1][j] + 1, 1, "delete"),
                          (costs[i][j-1] + 1, 2, "insert"))
            cost, _, action = min(candidates)
            costs[i][j], trace[i][j] = cost, action
    ops = []
    i, j = n, m
    while i or j:
        op = trace[i][j]
        if op in ("match", "substitute"):
            target_unit, section = expected[i-1]
            ops.append({"kind": op, "syllable": section, "expected": target_unit,
                        "heard": heard[j-1], "cost": round(substitution(target_unit, heard[j-1]), 3)})
            i -= 1
            j -= 1
        elif op == "delete":
            target_unit, section = expected[i-1]
            ops.append({"kind": op, "syllable": section, "expected": target_unit,
                        "heard": None, "cost": 1.0})
            i -= 1
        elif op == "insert":
            section = expected[i-1][1] if i else expected[0][1]
            ops.append({"kind": op, "syllable": section, "expected": None,
                        "heard": heard[j-1], "cost": 1.0})
            j -= 1
        else:
            raise ValueError("Invalid sound-unit alignment")
    return list(reversed(ops))


def per_syllable(target: str, hypothesis: str) -> list[dict]:
    if target.casefold() != WORD.casefold():
        raise ValueError("Only the syllable-reviewed Świętokrzyska item is supported in v1")
    original = [sound_units(s) for s in SYLLABLES]
    sequence = [(unit, i) for i, segment in enumerate(original) for unit in segment]
    ops = align(sequence, sound_units(hypothesis))
    result = []
    for i, syllable in enumerate(SYLLABLES):
        aligned = [op for op in ops if op["syllable"] == i]
        length = len(original[i])
        edit_cost = sum(op["cost"] for op in aligned)
        raw_score = max(0.0, (1.0 - edit_cost / length) * 100.0)
        score = round(raw_score)
        if score >= 80:
            level = "close"
        elif score >= 50:
            level = "review"
        else:
            level = "focus"
        differences = [op for op in aligned if op["kind"] != "match"]
        result.append({
            "syllable": syllable,
            "target_units": original[i],
            "hypothesized_units": [op["heard"] for op in aligned if op["heard"] is not None],
            "target_letter_groups": list(SOUND_GROUPS[i]),
            "estimate": score,
            "level": level,
            "edits": differences,
        })
    return result


def estimate(target: str, hypotheses: Sequence[tuple[str, str]]) -> dict:
    if target.casefold() != WORD.casefold() or not hypotheses or len(hypotheses) > 2:
        raise ValueError("Only the recorded Świętokrzyska dual-model comparison is supported")
    if any(not name or not transcript for name, transcript in hypotheses):
        raise ValueError("An incomplete Whisper comparison cannot produce a phonetic proxy")
    analyses = [{"model": name, "transcript": hypothesis,
                 "syllables": per_syllable(target, hypothesis)}
                for name, hypothesis in hypotheses]
    combined = []
    for i, syllable in enumerate(SYLLABLES):
        parts = [analysis["syllables"][i] for analysis in analyses]
        low, high = min(p["estimate"] for p in parts), max(p["estimate"] for p in parts)
        # Never turn model disagreement into a confident average. If it differs,
        # label a range. Likewise, nothing is acoustically verified here.
        is_stable = all(
            p["hypothesized_units"] == parts[0]["hypothesized_units"] for p in parts
        )
        band = ("uncertain" if not is_stable else
                "close" if low >= 80 else "review" if low >= 50 else "focus")
        combined.append({
            "syllable": syllable, "target_units": parts[0]["target_units"],
            "target_letter_groups": parts[0]["target_letter_groups"],
            "min_estimate": low, "max_estimate": high,
            "status": band, "transcription_proxy_agreement": is_stable,
            "comparisons": [{"model": a["model"],
                             "hypothesized_units": a["syllables"][i]["hypothesized_units"],
                             "edits": a["syllables"][i]["edits"]}
                            for a in analyses],
        })
    # The overall score uses all aligned operations, not a simple
    # arithmetic mean of percentages for syllables of unequal lengths.
    target_total = sum(len(sound_units(s)) for s in SYLLABLES)
    overall_scores = []
    for a in analyses:
        total_cost = sum(
            len(x["target_units"]) * (100.0-x["estimate"]) / 100.0
            for x in a["syllables"]
        )
        overall_scores.append(round(max(0.0, 100.0 * (1 - total_cost / target_total))))
    return {
        "schema": SCHEMA, "reference": WORD,
        "kind": "UNVALIDATED_TRANSCRIPT_DERIVED_SOUND_UNIT_SIMILARITY",
        "overall_estimate_range": [min(overall_scores), max(overall_scores)],
        "model_hypotheses": [{"model": a["model"], "transcript": a["transcript"]}
                             for a in analyses],
        "syllables": combined,
        "scoring_contract": {
            "method": "weighted sound-unit edit alignment; costs 0 for matches, up to 1 per edit",
            "normalizations": "w/v equivalent in hypotheses; spaces ignored; common Polish digraphs grouped",
            "not_measured": "actual spoken phonemes, syllable timestamps, accent/stress, human-graded pronunciation",
            "warning": "Word colors indicate transcript-derived hypotheses, not verified speaker errors or XP grades.",
        },
        "network_calls": 0,
    }


def from_saved(wav: Path, azure_result: Path, whisper_result: Path) -> dict:
    previous = compare_providers(wav, azure_result, whisper_result)
    if previous["status"] != "WHISPER_PAIRED_RESULT":
        raise ValueError("Use the completed owner-private two-model Whisper evidence")
    if any(row["status"] != "ok" or not row["transcript"] for row in previous["whisper"]):
        raise ValueError("Cannot score failed or blank Whisper transcriptions")
    out = estimate(previous["reference"], [
        (row["model"], row["transcript"]) for row in previous["whisper"]
    ])
    out["same_original_audio_verified"] = previous["same_audio_verified"]
    out["prior_azure_calls"] = 2
    out["prior_whisper_calls"] = 2
    return out


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _describe_edit(edit: dict) -> str:
    name = edit["kind"]
    if name == "substitute":
        return f"Possible sound-unit replacement: {_esc(edit['expected'])} → {_esc(edit['heard'])}"
    if name == "delete":
        return f"Unit not represented in Whisper spelling: {_esc(edit['expected'])}"
    if name == "insert":
        return f"Additional unit in Whisper spelling: {_esc(edit['heard'])}"
    return "No inferred difference"


def render_html(result: dict) -> str:
    if result.get("schema") != SCHEMA:
        raise ValueError("Unexpected private phonetic report")
    parts = []
    classes = {"close": "close", "review": "review", "focus": "focus", "uncertain": "uncertain"}
    for seg in result["syllables"]:
        status = classes[seg["status"]]
        bound = (f"{seg['min_estimate']}%" if seg["min_estimate"] == seg["max_estimate"]
                 else f"{seg['min_estimate']}–{seg['max_estimate']}%")
        evaluations = []
        for comp in seg["comparisons"]:
            edits = comp["edits"]
            hints = "<li>"+"</li><li>".join(_describe_edit(e) for e in edits)+"</li>" if edits else "<li>No differences in the transcript proxy</li>"
            evaluations.append(
                f"<section><h4>{_esc(comp['model'])}</h4>"
                f"<p>Estimated recognized units: <code>{_esc(' · '.join(comp['hypothesized_units']) or '—')}</code></p>"
                f"<ul>{hints}</ul></section>")
        parts.append(
            f'<details class="segment {status}"><summary><span lang="pl">{_esc(seg["syllable"])}</span>'
            f'<span class="score">{bound}</span><small>{status}</small></summary>'
            f'<div class="details"><p>Practice letter combination: '
            f'<strong>{_esc(" / ".join(seg["target_letter_groups"]))}</strong></p>'
            f'<p>Target sound units: <code>{_esc(" · ".join(seg["target_units"]))}</code></p>'
            + "".join(evaluations) +
            '<p class="caution">Suggestions inferred from written ASR output, not verified sounds in the original recording.</p>'
            '</div></details>')
    overall = result["overall_estimate_range"]
    score = str(overall[0]) if overall[0] == overall[1] else f"{overall[0]}–{overall[1]}"
    transcripts = " / ".join(_esc(m["transcript"]) for m in result["model_hypotheses"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Path to Polish · Phonetic similarity preview</title>
<style>
:root{{font-family:system-ui,-apple-system,sans-serif;color-scheme:light dark}}
body{{max-width:800px;margin:0 auto;padding:clamp(16px,4vw,38px);line-height:1.45}}
h1{{font-size:1.6rem;margin-bottom:.35rem}}
.subtitle,.caution{{color:CanvasText;opacity:.78}}
.review-panel{{border:1px solid GrayText;border-radius:18px;padding:20px;margin:20px 0}}
.target{{font-size:1.4rem;font-weight:700}}
.row{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}}
.segment{{flex:1 1 100px;border:2px solid transparent;border-radius:13px;min-width:98px;overflow:hidden}}
.segment.close{{--accent:#08764a;--tint:#d7f4e2}}
.segment.review{{--accent:#9b5900;--tint:#fff0c9}}
.segment.focus{{--accent:#a42936;--tint:#ffe0e2}}
.segment.uncertain{{--accent:#505c6d;--tint:#e8edf2}}
.segment{{border-color:var(--accent);color:#20242a;background:var(--tint)}}
.segment summary{{list-style:none;display:flex;flex-direction:column;gap:3px;padding:12px;cursor:pointer;min-height:70px}}
.segment summary::-webkit-details-marker{{display:none}}
.segment summary:focus-visible{{outline:3px solid #134cbd;outline-offset:-3px}}
.segment summary span:first-child{{font-size:1.5rem;font-weight:750}}
.segment small{{font-size:.76rem;text-transform:capitalize}}
.segment .score{{font-weight:700}}
.details{{padding:14px;background:#fff;color:#1b2630;border-top:1px solid var(--accent);font-size:.89rem}}
.details section{{padding-block:8px;border-top:1px solid #ddd}}
.details h4{{font-size:.89rem;margin:4px 0}}
.details ul{{padding-left:20px}}
code{{overflow-wrap:anywhere}}
@media(max-width:460px){{.segment{{flex-basis:44%}}}}
</style></head>
<body><header><p>PATH TO POLISH / PRIVATE RESEARCH REVIEW</p>
<h1>Where did the sounds differ?</h1>
<p class="subtitle">Tap or click a coloured syllable to see a candidate sound-unit difference.
This preview is not an acoustic measurement or pronunciation grade.</p></header>
<main><section class="review-panel">
<div class="target" lang="pl">{_esc(result["reference"])}</div>
<p>Transcript-based similarity estimate: <strong>{_esc(score)} / 100</strong></p>
<div class="row">{"".join(parts)}</div>
<p>Whisper's written interpretations: <strong>{transcripts}</strong></p>
</section><p class="caution">Green = closer transcription match; amber = review; red = focus;
grey = conflicting model readings. Every percentage is provisional. Spoken sound differences
must be checked against the recording; W/V spelling may represent the same sound.
No voice is embedded, no external scripts are loaded, and nothing is uploaded.</p></main>
</body></html>"""


def write_private_html(output: Path, wav: Path, text: str) -> None:
    if (output.suffix != ".html" or output.parent.resolve() != wav.parent.resolve()
            or output.exists() or output.is_symlink() or output.parent.is_symlink()
            or stat.S_IMODE(output.parent.stat().st_mode) & 0o077):
        raise ValueError("Choose a new owner-private .html alongside the original WAV")
    from research_paths import check_research_location
    check_research_location(output)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


def main() -> int:
    p = argparse.ArgumentParser(description="OFFLINE sound-unit syllable review of existing owner Whisper/Azure recordings; zero network")
    p.add_argument("--wav", required=True, type=Path)
    p.add_argument("--azure-result", required=True, type=Path)
    p.add_argument("--whisper-result", required=True, type=Path)
    p.add_argument("--html-output", type=Path, help="NEW private standalone clickable syllable review .html")
    args = p.parse_args()
    try:
        report = from_saved(args.wav, args.azure_result, args.whisper_result)
        if args.html_output:
            write_private_html(args.html_output, args.wav, render_html(report))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError, json.JSONDecodeError):
        p.error("Private audio or saved evidence invalid, or output already exists. No provider called; do not overwrite evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
