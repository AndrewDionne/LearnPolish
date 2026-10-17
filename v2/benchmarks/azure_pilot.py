#!/usr/bin/env python3
"""Polish Azure scripted pronunciation pilot — preview first, no spend by default.

A real send is possible ONLY with four explicit owner controls:
  --send --approve-voice-upload --confirm-resource-f0 --confirm-no-paid-billing

Always submit the *original* 1× human-verified WAV, never tempo-derived audio.
Azure pl-PL can provide pronunciation accuracy/fluency/word/phoneme scores,
but NOT named Polish phoneme diagnostics or prosody. Preserve raw SDK evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from benchmark import read_audio_metadata
from research_paths import check_research_location


def checked_recording(manifest: Path, sample_id: str) -> tuple[dict, Path, dict]:
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("Explicit --sample-id is required; never upload a batch by default")
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("Manifest must be a real file")
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Manifest must contain reviewed recordings")
    matches = [r for r in rows if isinstance(r, dict) and r.get("id") == sample_id]
    if len(matches) != 1:
        raise ValueError("Exactly one approved sample-id must match")
    row = matches[0]
    if row.get("reference_verified_by_human") is not True or row.get("audio_audited_unclipped") is not True:
        raise ValueError("Human reference/audio review is mandatory before Azure")
    if row.get("provider_upload_approved") is not True:
        raise ValueError("Selected source has not been approved for provider upload")
    if row.get("artificially_stretched") is not False or row.get("speed_factor") != 1.0:
        raise ValueError("Azure pronunciation assessment requires original 1.0x unprocessed audio")
    if row.get("speaker_role") not in ("adult_learner", "native_control"):
        raise ValueError("Only adult learner or separately approved native controls permitted")
    if row["speaker_role"] == "adult_learner" and row.get("adult_consent_confirmed") is not True:
        raise ValueError("Adult learner informed recording consent is required")
    reference = row.get("reference")
    if not isinstance(reference, str) or len(reference.split()) < 4:
        raise ValueError("A verified complete sentence reference is required")
    filename = row.get("audio")
    if (not isinstance(filename, str) or Path(filename).is_absolute()
            or filename != Path(filename).name or not filename.endswith(".wav")):
        raise ValueError("Audio must be a local manifest-relative WAV name")
    audio = manifest.parent / filename
    if audio.is_symlink() or not audio.is_file():
        raise ValueError("WAV must be a non-symlink regular file")
    metadata = read_audio_metadata(audio)
    if not metadata["valid_signal"] or not 5 <= metadata["seconds"] <= 15.1:
        raise ValueError("Only 5-15 second clearly spoken natural audio may be assessed")
    if row.get("audio_sha256") != metadata["audio_sha256"]:
        raise ValueError("Audio changed since original manifest SHA lock")
    if row.get("original_sha256") != metadata["audio_sha256"]:
        raise ValueError("Azure input must be the unaltered original SHA-256 WAV")
    return row, audio, metadata


def azure_scripted_assess(audio: Path, reference: str, key: str, region: str) -> dict:
    """One SDK recognize_once call; never echoes provider exception internals."""
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        raise RuntimeError("Missing optional Azure Speech SDK; install azure-cognitiveservices-speech locally") from None
    try:
        config = speechsdk.SpeechConfig(subscription=key, region=region)
        config.speech_recognition_language = "pl-PL"
        config.output_format = speechsdk.OutputFormat.Detailed
        audio_config = speechsdk.audio.AudioConfig(filename=str(audio))
        assessment = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
        assessment.apply_to(recognizer)
        result = recognizer.recognize_once()
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return {"status": "inconclusive", "reason": "Azure did not recognize complete speech"}
        text = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        if not isinstance(text, str) or not text:
            return {"status": "inconclusive", "reason": "Azure returned no detailed response"}
        raw = json.loads(text)
        if not isinstance(raw, dict):
            return {"status": "inconclusive", "reason": "Azure response was not a JSON object"}
        return {"status": "ok", "raw_azure_json": raw}
    except (RuntimeError, ImportError):
        raise
    except Exception:
        # The Azure SDK might embed identifiers or voice text in cancellation
        # details. Never print exception, detailed provider body, key or audio.
        raise RuntimeError("Azure recognition failed; inspect resource settings privately. No retry.") from None


def _new_private_file(path: Path):
    check_research_location(path)
    if path.is_symlink() or path.exists():
        raise ValueError("Choose a NEW output filename; Azure results are never overwritten")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise ValueError("Azure result parent must exist and be chmod 700")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    return os.fdopen(os.open(path, flags, 0o600), "w", encoding="utf-8")


def run(manifest: Path, sample_id: str, *, send: bool = False,
        approve_voice_upload: bool = False, confirm_resource_f0: bool = False,
        confirm_no_paid_billing: bool = False, output: Path | None = None,
        key: str | None = None, region: str | None = None,
        max_requests: int = 1, max_audio_seconds: float = 15.0,
        assessor: Callable = azure_scripted_assess) -> dict:
    if max_requests != 1:
        raise ValueError("Azure research gate allows EXACTLY one assessed recording per invocation")
    if not 5 <= max_audio_seconds <= 15:
        raise ValueError("Azure study hard cap must be between 5 and 15 audio seconds")
    row, audio, metadata = checked_recording(manifest, sample_id)
    if metadata["seconds"] > max_audio_seconds:
        raise ValueError("Audio duration exceeds owner's Azure allowance cap")
    preview = {"sample_id": sample_id, "locale": "pl-PL", "assessment": "scripted",
               "source_sha256": metadata["audio_sha256"],
               "audio_seconds": round(metadata["seconds"], 3),
               "planned_requests": 1, "planned_audio_seconds": round(metadata["seconds"], 3),
               "network_requests_performed": 0,
               "voice_uploaded": False,
               "not_a_pronunciation_grade": True}
    if not send:
        return preview
    if not (approve_voice_upload and confirm_resource_f0 and confirm_no_paid_billing):
        raise ValueError("Live Azure needs --approve-voice-upload --confirm-resource-f0 and --confirm-no-paid-billing")
    if not key or not region or not re.fullmatch(r"[a-z][a-z0-9-]{2,35}", region):
        raise ValueError("Set AZURE_SPEECH_KEY and valid AZURE_SPEECH_REGION in local shell")
    if output is None:
        raise ValueError("A new private --output JSON file is required for live Azure")
    # Reserve the result file before the one allowed request; fail on collisions.
    stream = _new_private_file(output)
    stamp = os.fstat(stream.fileno())
    try:
        with stream:
            payload = assessor(audio, row["reference"], key, region)
            if not isinstance(payload, dict) or payload.get("status") not in ("ok", "inconclusive"):
                raise ValueError("Azure SDK returned an unrecognized result")
            report = dict(preview, network_requests_performed=1, voice_uploaded=True,
                          status=payload["status"])
            output_row = {
                "id": row["id"], "reference": row["reference"],
                "engine": "azure-pl-PL-scripted", "audio_sha256": metadata["audio_sha256"],
                "audio_seconds": round(metadata["seconds"], 3),
                "locale": "pl-PL", "speed_factor": 1.0,
                "status": payload["status"],
                "raw_azure_json": payload.get("raw_azure_json"),
                "reason": payload.get("reason"),
                "assessment_is_human_calibrated": False,
            }
            json.dump(output_row, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return report
    except Exception:
        try:
            current = os.stat(output, follow_symlinks=False)
            if (current.st_ino == stamp.st_ino and current.st_dev == stamp.st_dev
                    and current.st_size == 0):
                os.unlink(output)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Azure pl-PL adult pronunciation pilot — PREVIEW ONLY by default")
    parser.add_argument("--manifest", required=True, type=Path, help="Frozen original (not tempo) manifest")
    parser.add_argument("--sample-id", required=True, help="Exactly ONE independently verified audio sample")
    parser.add_argument("--max-requests", type=int, default=1)
    parser.add_argument("--max-audio-seconds", type=float, default=15)
    parser.add_argument("--send", action="store_true", help="Permit one real Azure request")
    parser.add_argument("--approve-voice-upload", action="store_true", help="Informed speaker consent and provider policy reviewed")
    parser.add_argument("--confirm-resource-f0", action="store_true", help="I verified my Azure Speech resource actually has F0 tier and feature")
    parser.add_argument("--confirm-no-paid-billing", action="store_true", help="I verified no chargeable resource or usage is enabled")
    parser.add_argument("--output", type=Path, help="NEW private raw Azure evidence JSON; never overwrite")
    args = parser.parse_args()
    try:
        result = run(args.manifest, args.sample_id,
                     max_requests=args.max_requests, max_audio_seconds=args.max_audio_seconds,
                     send=args.send, approve_voice_upload=args.approve_voice_upload,
                     confirm_resource_f0=args.confirm_resource_f0,
                     confirm_no_paid_billing=args.confirm_no_paid_billing,
                     output=args.output,
                     key=os.environ.get("AZURE_SPEECH_KEY"),
                     region=os.environ.get("AZURE_SPEECH_REGION"))
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    if not args.send:
        print("PREVIEW ONLY — no Azure SDK import, no network, no audio uploads, no charges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
