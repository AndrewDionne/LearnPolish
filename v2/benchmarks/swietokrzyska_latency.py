#!/usr/bin/env python3
"""One adult Świętokrzyska WAV: ordinary vs preconnected Azure SDK latency.

No recording is provided by this code; a genuine adult's own WAV must first be
exported by V2 Speak. Preview, validation and offline review make ZERO calls.
Owner's private Azure F0 is the only possible provider; no Groq/TTS/child data.

The preconnection case still creates its OWN recognizer, with a separately
applied reference and isolated file. Never reuse a recognizer across learners.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import threading
import time
from typing import Callable

from azure_pilot import azure_recognition_diagnostic
from benchmark import read_audio_metadata, extract_azure_native
from corpus import parse_capture_name
from research_paths import check_research_location
from speech_env import speech_credentials
from three_model_pilot import _output

WORD = "Świętokrzyska"
ITEM_ID = "speak_swietokrzyska:0"
REGION = "germanywestcentral"
VARIANTS = ("ordinary", "preconnect")
PRECONNECT_WAIT_SECONDS = 3.0
SCORE_NAMES = ("AccuracyScore", "FluencyScore", "CompletenessScore")
MAX_AUDIO_BYTES = 360_000


def checked_audio(path: Path) -> dict:
    check_research_location(path)
    if (path.is_symlink() or not path.is_file() or
            path.parent.is_symlink() or
            stat.S_IMODE(path.parent.stat().st_mode) & 0o077 or
            path.stat().st_size > MAX_AUDIO_BYTES):
        raise ValueError("Use a private, original <=10s V2 Speak WAV in a chmod-700 folder")
    # The existing Speak export filename cryptographically identifies neither
    # a person nor correctness; it does lock the exact authoritative item ID.
    item, _ = parse_capture_name(path.name)
    if item != ITEM_ID:
        raise ValueError("Recording must be the exported Świętokrzyska Speak item")
    audio = read_audio_metadata(path)
    # The V2 Speak WAV encoder writes a strict 44-byte header plus exactly
    # the declared PCM frames. A truncated file can otherwise still have
    # plausible WAV metadata/peak from its first few samples.
    expected_bytes = 44 + round(audio["seconds"] * 16000) * 2
    if path.stat().st_size != expected_bytes:
        raise ValueError("Original exported V2 WAV is incomplete or altered")
    if not audio["valid_signal"] or not .6 <= audio["seconds"] <= 10:
        raise ValueError("WAV is silent, too short or longer than ten seconds")
    return {"sample_id": ITEM_ID, "reference": WORD, "wav_sha256": audio["audio_sha256"],
            "wav_seconds": round(audio["seconds"], 3)}


def preview(audio: Path) -> dict:
    checked = checked_audio(audio)
    return {"status": "PREVIEW_ONLY", **checked, "provider_calls": 0,
            "planned_azure_requests": 2, "planned_groq_requests": 0,
            "sequence": list(VARIANTS), "preconnection_wait_cap_seconds": PRECONNECT_WAIT_SECONDS,
            "critical": "These are the same adult WAV bytes, not a calibration study or a production p95"}


def safe_scores(raw: object) -> dict[str, float] | None:
    native = extract_azure_native(raw) if isinstance(raw, dict) else None
    scores = native.get("scores") if isinstance(native, dict) else None
    if not isinstance(scores, dict):
        return None
    if any(type(scores.get(name)) not in (float, int) or
           not math.isfinite(scores[name]) or not 0 <= scores[name] <= 100 for name in SCORE_NAMES):
        return None
    return {name: float(scores[name]) for name in SCORE_NAMES}


def sdk_assess(audio: Path, reference: str, key: str, region: str,
               variant: str) -> dict:
    """Actual SDK; no raw text, tokens or exception details escape."""
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        raise RuntimeError("Azure Speech SDK not installed in the private venv") from None
    t0 = time.monotonic()
    try:
        config = speechsdk.SpeechConfig(subscription=key, region=region)
        config.speech_recognition_language = "pl-PL"
        config.output_format = speechsdk.OutputFormat.Detailed
        input_audio = speechsdk.audio.AudioConfig(filename=str(audio))
        assessment = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=input_audio)
        assessment.apply_to(recognizer)
        connected_before = False
        connection_wait_ms = 0.0
        connection = None
        if variant == "preconnect":
            ready = threading.Event()
            connection = speechsdk.Connection.from_recognizer(recognizer)
            # Never log the ConnectionEventArgs (session IDs, service details).
            connection.connected.connect(lambda *_: ready.set())
            wait_started = time.monotonic()
            connection.open(False)
            connected_before = ready.wait(timeout=PRECONNECT_WAIT_SECONDS)
            connection_wait_ms = round((time.monotonic() - wait_started) * 1000, 1)
        recognize_start = time.monotonic()
        result = recognizer.recognize_once()
        recognize_ms = round((time.monotonic() - recognize_start) * 1000, 1)
        total_ms = round((time.monotonic() - t0) * 1000, 1)
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            diag = azure_recognition_diagnostic(result,speechsdk)
            return {"status":"inconclusive", "timing_ms":{
                "total":total_ms,"preconnection":connection_wait_ms,"recognition":recognize_ms},
                "connected_before_recognition":connected_before,
                "sdk_result_reason":diag.get("azure_result_reason","Other"),
                "scores":None}
        text = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        raw = json.loads(text) if text else None
        scores = safe_scores(raw)
        return {"status":"ok" if scores is not None else "unscored",
                "timing_ms":{"total":total_ms,"preconnection":connection_wait_ms,
                             "recognition":recognize_ms},
                "connected_before_recognition":connected_before,"scores":scores,
                "sdk_result_reason":None}
    except Exception:
        # SDK exceptions can contain private URLs/headers/transcripts.
        return {"status":"error","timing_ms":{
            "total":round((time.monotonic()-t0)*1000,1),
            "preconnection":None,"recognition":None},
            "connected_before_recognition":False,"scores":None,
            "sdk_result_reason":None}


def clean_payload(variant: str, i: int, metadata: dict, payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("status") not in ("ok","unscored","inconclusive","error"):
        raise ValueError("Invalid SDK outcome")
    timing=payload.get("timing_ms")
    if not isinstance(timing,dict):
        raise ValueError("Invalid timing payload")
    cleaned={}
    for k in ("total","preconnection","recognition"):
        v=timing.get(k)
        if v is not None and (type(v) not in (float,int) or not math.isfinite(v) or not 0 <= v <= 120000):
            raise ValueError("Invalid measured SDK timing")
        cleaned[k]=round(v,1) if v is not None else None
    scores=payload.get("scores")
    if scores is not None:
        if not isinstance(scores,dict) or any(type(scores.get(k)) not in (float,int)
               or not math.isfinite(scores[k]) or not 0 <= scores[k] <= 100 for k in SCORE_NAMES):
            raise ValueError("Invalid Azure score evidence")
        scores={k:float(scores[k]) for k in SCORE_NAMES}
    if payload["status"]=="ok" and scores is None:
        raise ValueError("Successful Azure assessment requires actual native scores")
    status=payload["status"]
    reason=payload.get("sdk_result_reason")
    if reason not in (None,"Canceled","NoMatch","Other"):
        reason="Other"
    return {"schema":"ptp-swietokrzyska-latency-v1","attempt":i,"planned_attempts":2,
            "variant":variant, "sample_id":ITEM_ID,"reference":WORD,
            "audio_sha256":metadata["wav_sha256"],"audio_seconds":metadata["wav_seconds"],
            "status":status,"timing_ms":cleaned,"scores_uncalibrated":scores,
            "connected_before_recognition":payload.get("connected_before_recognition") is True,
            "sdk_result_reason":reason}


def summary(audio: Path, output: Path) -> dict:
    original=checked_audio(audio)
    if (output.parent.resolve()!=audio.parent.resolve() or output.is_symlink()
            or not output.is_file() or output.suffix!=".jsonl" or
            stat.S_IMODE(output.stat().st_mode)&0o077 or
            output.stat().st_size>40000):
        raise ValueError("Review only a saved private non-symlink 0600 JSONL next to the source WAV")
    rows=[json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    if not 1<=len(rows)<=2:
        raise ValueError("Expect one or two saved assessment rows")
    for idx,row in enumerate(rows):
        if (not isinstance(row,dict) or row.get("schema")!="ptp-swietokrzyska-latency-v1"
             or row.get("attempt")!=idx+1 or row.get("planned_attempts")!=2
             or row.get("variant")!=VARIANTS[idx] or row.get("reference")!=WORD
             or row.get("sample_id")!=ITEM_ID
             or row.get("audio_sha256")!=original["wav_sha256"]
             or row.get("status") not in ("ok","unscored","inconclusive","error")):
            raise ValueError("Saved study result mismatched original WAV or requested reference")
    return {"status":"PARTIAL" if len(rows)<2 else "PAIRED_RESULT",
            "reference":WORD,"same_audio_verified":True,
            "audio_sha256":original["wav_sha256"],
            "actual_provider_attempts_saved":len(rows),"groq_calls":0,
            "observations":[{"variant":r["variant"],"status":r["status"],
                "timing_ms":r["timing_ms"],"connected_before_recognition":r["connected_before_recognition"],
                "scores_uncalibrated":r["scores_uncalibrated"]} for r in rows],
            "note":"Ordinary vs preconnect is two sequential attempts, NOT a measured production p95 or guaranteed latency optimization"}


def run(audio: Path, output: Path | None = None, *, send: bool = False,
        approve_adult_audio_upload: bool = False,
        confirm_azure_f0: bool = False,
        confirm_no_paid_billing: bool = False,
        azure_key: str | None = None, azure_region: str | None = None,
        assessor: Callable = sdk_assess) -> dict:
    metadata=checked_audio(audio)
    if not send:
        return preview(audio)
    if not (approve_adult_audio_upload and confirm_azure_f0 and confirm_no_paid_billing):
        raise ValueError("Consent to adult voice upload, existing F0 and no-paid-billing must be confirmed")
    # The owner may be returning after a completed or partial run. Never
    # start another provider call before identifying an existing result.
    if output is not None and (output.is_symlink() or output.exists()):
        raise ValueError("Output already exists; preserve it. Use --summarize to review saved attempts before considering another call")
    if not azure_key:
        raise ValueError("AZURE_SPEECH_KEY is not exported in this Terminal. Restore it privately; never print or paste the key")
    if (not azure_key.isascii() or not azure_key.isprintable()
            or azure_key != azure_key.strip() or "\u2026" in azure_key):
        raise ValueError("AZURE_SPEECH_KEY has an invalid shape or placeholder; reset it privately without printing the value")
    if azure_region != REGION:
        raise ValueError("AZURE_SPEECH_REGION must be germanywestcentral in this Terminal")
    if output is None:
        raise ValueError("Choose a NEW owner-private output filename")
    if output.resolve()==audio.resolve():
        raise ValueError("Results must not overwrite original voice recording")
    with _output(output,audio.parent) as f:
        for idx,variant in enumerate(VARIANTS,1):
            try:
                outcome=assessor(audio,WORD,azure_key,azure_region,variant)
                row=clean_payload(variant,idx,metadata,outcome)
            except Exception:
                row=clean_payload(variant,idx,metadata,{"status":"error",
                    "timing_ms":{"total":0.0,"preconnection":None,"recognition":None},
                    "connected_before_recognition":False,"scores":None})
            f.write(json.dumps(row,ensure_ascii=False)+"\n")
            f.flush()
            os.fsync(f.fileno())
            print("Azure %d/2: %s %s" % (idx,variant,row["status"]),flush=True)
            if row["status"]=="error":
                break
    return summary(audio,output)


# Only these EXACT owner-authored errors may be printed by the CLI.
# Exception text from the SDK, WAV parser and OS is deliberately excluded,
# because it can contain private filesystem paths, HTTP headers or tokens.
_SAFE_CLI_MESSAGES = frozenset((
    "Output already exists; preserve it. Use --summarize to review saved attempts before considering another call",
    "AZURE_SPEECH_KEY is not exported in this Terminal. Restore it privately; never print or paste the key",
    "AZURE_SPEECH_KEY has an invalid shape or placeholder; reset it privately without printing the value",
    "AZURE_SPEECH_REGION must be germanywestcentral in this Terminal",
    "Choose a NEW owner-private output filename",
    "Results must not overwrite original voice recording",
    "Consent to adult voice upload, existing F0 and no-paid-billing must be confirmed",
    "Output exists. Pick a NEW private filename; never overwrite partial tests",
    "Private output parent must be chmod 700",
    "Result must be a new .jsonl DIRECTLY inside existing private source folder",
    "Offline summary cannot be combined with provider send",
))


def main() -> int:
    p=argparse.ArgumentParser(description="Two opt-in Świętokrzyska Azure checks (ordinary/preconnected) from ONE real adult Speak WAV")
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--send",action="store_true")
    p.add_argument("--approve-adult-audio-upload",action="store_true")
    p.add_argument("--confirm-azure-f0",action="store_true")
    p.add_argument("--confirm-no-paid-billing",action="store_true")
    p.add_argument("--output",type=Path)
    p.add_argument("--summarize",type=Path,help="Offline report from earlier private result")
    args=p.parse_args()
    try:
        if args.summarize:
            if args.send or args.output:
                raise ValueError("Offline summary cannot be combined with provider send")
            result=summary(args.wav,args.summarize)
        else:
            key, region = speech_credentials() if args.send else (None, None)
            result=run(args.wav,args.output,send=args.send,
                approve_adult_audio_upload=args.approve_adult_audio_upload,
                confirm_azure_f0=args.confirm_azure_f0,
                confirm_no_paid_billing=args.confirm_no_paid_billing,
                azure_key=key,
                azure_region=region)
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except ValueError as exc:
        # Allowlisted preflight messages are safe; do not echo untrusted
        # errors from WAV parsing, Azure SDK or arbitrary Python exceptions.
        message = str(exc)
        p.error(message if message in _SAFE_CLI_MESSAGES else
                "Local validation failed; check your original private WAV and 0700 folder")
    except (OSError,TypeError,RuntimeError,json.JSONDecodeError):
        p.error("Private WAV/provider operation failed; preserve existing output and do not automatically retry")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
