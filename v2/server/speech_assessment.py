"""Opt-in, server-side Azure Polish pronunciation assessment for V2 learners.

Network SDK invocation is disabled unless the parent family API explicitly enables
Speech F0 and already has an authenticated, email-verified learner session.
No recording, transcript, raw SDK JSON, key, or provider exception is persisted.
The raw score is intentionally NOT calibrated, certified, or evidence for XP.
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import tempfile
import wave

MAX_WAV_BYTES = 360_000
MIN_SECONDS = 0.6
MAX_SECONDS = 10.0


class InvalidAudio(ValueError):
    pass


def checked_wav(blob: bytes) -> tuple[float, bytes]:
    """Accept only original mono 16k PCM16 WAV, bounded by runtime and size."""
    if not isinstance(blob, bytes) or not 44 <= len(blob) <= MAX_WAV_BYTES:
        raise InvalidAudio("invalid_audio")
    try:
        with wave.open(io.BytesIO(blob), "rb") as reader:
            if (reader.getnchannels(), reader.getframerate(), reader.getsampwidth(),
                    reader.getcomptype()) != (1, 16000, 2, "NONE"):
                raise InvalidAudio("unsupported_audio_format")
            frames = reader.getnframes()
            seconds = frames / 16000
            if not MIN_SECONDS <= seconds <= MAX_SECONDS:
                raise InvalidAudio("invalid_audio_duration")
            pcm = reader.readframes(frames)
            if len(pcm) != frames * 2:
                raise InvalidAudio("invalid_audio")
    except (EOFError, wave.Error, OSError, struct_error()):
        raise InvalidAudio("invalid_audio") from None
    # Client checks are not authoritative; reject empty/distorted inputs before
    # consuming an external provider request. audioop was removed in Python 3.13.
    samples = memoryview(pcm).cast("B")
    # Avoid platform native-endian dependence when decoding PCM16.
    power = 0
    clipped = 0
    for i in range(0, len(samples), 2):
        raw = samples[i] | (samples[i + 1] << 8)
        signed = raw if raw < 32768 else raw - 65536
        power += signed * signed
        if abs(signed) >= 32500:
            clipped += 1
    rms = math.sqrt(power / frames) / 32768
    if rms < 0.008 or clipped / frames > 0.02:
        raise InvalidAudio("audio_quality_inconclusive")
    return seconds, blob


def struct_error():
    # stdlib wave occasionally raises struct.error on truncated headers.
    import struct
    return struct.error


def _score(value: object) -> float | None:
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return round(float(value), 1)


def assessment_from_sdk(payload: dict) -> dict:
    """Only provider-measured scalar scores; never fill absent values with zero."""
    if payload.get("status") != "ok":
        return {"status": "inconclusive", "reason": payload.get("reason", "provider_inconclusive")
                if payload.get("reason") in ("no_match", "canceled", "no_assessment")
                else "provider_inconclusive"}
    raw = payload.get("raw")
    try:
        pa = raw["NBest"][0]["PronunciationAssessment"]
        scores = {label: _score(pa[label]) for label in
                  ("AccuracyScore", "FluencyScore", "CompletenessScore")}
        if any(value is None for value in scores.values()):
            raise ValueError("Incomplete scores")
    except (TypeError, KeyError, IndexError, ValueError):
        return {"status": "inconclusive", "reason": "no_assessment"}
    return {"status": "ok", "scores": {
        "accuracy": scores["AccuracyScore"],
        "fluency": scores["FluencyScore"],
        "completeness": scores["CompletenessScore"],
    }, "calibration": "uncalibrated", "supports_polish_phoneme_diagnosis": False}


def azure_scripted_assess(wav: bytes, reference: str, key: str, region: str) -> dict:
    """One Azure Speech SDK call. Temporary owner-private WAV removed even on failure."""
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        return {"status": "inconclusive", "reason": "provider_unavailable"}
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", prefix="ptp-speak-", delete=False) as file:
            path = Path(file.name)
            file.write(wav)
        config = speechsdk.SpeechConfig(subscription=key, region=region)
        config.speech_recognition_language = "pl-PL"
        config.output_format = speechsdk.OutputFormat.Detailed
        audio_config = speechsdk.audio.AudioConfig(filename=str(path))
        rubric = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
        rubric.apply_to(recognizer)
        result = recognizer.recognize_once()
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            kind = ("no_match" if result.reason == speechsdk.ResultReason.NoMatch
                    else "canceled")
            return {"status": "inconclusive", "reason": kind}
        response = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        raw = json.loads(response) if response else None
        if not isinstance(raw, dict):
            return {"status": "inconclusive", "reason": "no_assessment"}
        return {"status": "ok", "raw": raw}
    except Exception:
        # Never return or log exception/error_details, which may include voice
        # transcription, customer IDs, endpoints or access tokens.
        return {"status": "inconclusive", "reason": "provider_unavailable"}
    finally:
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
