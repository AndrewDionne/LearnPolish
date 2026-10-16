#!/usr/bin/env python3
"""Evidence-only comparison of saved Whisper/Azure predictions.

No inference, HTTP request, or pronunciation judgement is made here.
An independent human-labelled recording manifest is required to report error rates.
"""
from __future__ import annotations
import argparse
import json
import pathlib

def load_jsonl(path: pathlib.Path) -> dict[str, dict]:
    results = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in results:
            raise ValueError("Invalid or duplicate benchmark result id")
        results[row["id"]] = row
    return results

def compare(whisper: dict[str,dict], azure: dict[str,dict], labels: list[dict]) -> dict:
    if not isinstance(labels, list) or not labels:
        raise ValueError("Independent human-labelled records are required")
    ids = set()
    matched=[]
    for row in labels:
        if not isinstance(row, dict) or not isinstance(row.get("id"),str) or row["id"] in ids:
            raise ValueError("Invalid or repeated human label id")
        ids.add(row["id"])
        if row.get("intelligible") not in (True, False) or type(row.get("intelligible")) is not bool:
            raise ValueError("Each sample must have an independent human intelligibility label")
        wid=row["id"]
        w=whisper.get(wid)
        a=azure.get(wid)
        if not w or not a:
            raise ValueError("Missing provider result for labelled sample "+wid)
        if w.get("engine") != "whisper-local" or a.get("engine") != "azure-raw":
            raise ValueError("Wrong engine for sample "+wid)
        if w.get("reference") != a.get("reference"):
            raise ValueError("The engines must be compared against identical reference text")
        if abs(float(w.get("audio_seconds",-1))-float(a.get("audio_seconds",-2)))>0.001:
            raise ValueError("Different audio duration for sample "+wid)
        matched.append({"id":wid,"human_intelligible":row["intelligible"],
                        "whisper_transcript_match":w.get("recognized_expected_words") if w.get("status")=="ok" else None,
                        "azure_transcript_match":a.get("recognized_expected_words") if a.get("status")=="ok" else None,
                        "azure_native_accuracy":(a.get("scores") or {}).get("AccuracyScore") if a.get("status")=="ok" else None,
                        "azure_phoneme_count":sum(len(word.get("phonemes") or []) for word in (a.get("words") or [])),
                        "whisper_status":w.get("status"),"azure_status":a.get("status")})
    def recognized(field):
        available=[x for x in matched if isinstance(x[field],bool)]
        # ASR exact-match agreement with human intelligibility is only a research signal.
        return {"available":len(available),
                "agreement_with_human_intelligibility":
                    sum(x[field]==x["human_intelligible"] for x in available)/len(available) if available else None}
    return {
        "status":"evidence-comparison-only",
        "sample_count":len(matched),
        "whisper_word_recognition":recognized("whisper_transcript_match"),
        "azure_word_recognition":recognized("azure_transcript_match"),
        "azure_native_phoneme_data_count":sum(x["azure_phoneme_count"] for x in matched),
        "notes":["ASR match is not a phoneme pronunciation grade",
                 "Azure native scores are reported but never treated as calibrated without phoneme-level native human ratings",
                 "Absent provider output remains inconclusive and never becomes a 0% failure"],
        "samples":matched,
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--whisper-results",required=True,type=pathlib.Path)
    p.add_argument("--azure-results",required=True,type=pathlib.Path)
    p.add_argument("--human-labels",required=True,type=pathlib.Path)
    p.add_argument("--output",type=pathlib.Path)
    args=p.parse_args()
    try:
        human=json.loads(args.human_labels.read_text(encoding="utf-8"))
        result=compare(load_jsonl(args.whisper_results),load_jsonl(args.azure_results),human)
    except (OSError,ValueError,TypeError,KeyError) as error:
        p.error(str(error))
    value=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output: args.output.write_text(value,encoding="utf-8")
    else: print(value,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
