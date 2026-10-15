#!/usr/bin/env python3
"""Offline-first, replayable Polish ASR/pronunciation benchmark. No remote API calls."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import wave
from array import array
from dataclasses import asdict, dataclass

MAX_FREE_SECONDS = 600.0
MAX_FREE_RECORDINGS = 100


@dataclass(frozen=True)
class Sample:
    id: str
    audio: pathlib.Path
    reference: str
    azure_result: pathlib.Path | None = None


def load_manifest(path: pathlib.Path) -> list[Sample]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Manifest must be a nonempty JSON list")
    ids = set()
    samples = []
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("Every recording requires a stable id")
        if row["id"] in ids:
            raise ValueError("Duplicate sample id: " + row["id"])
        ids.add(row["id"])
        reference, audio = row.get("reference"), row.get("audio")
        if not isinstance(reference, str) or not reference.strip() or not isinstance(audio, str) or not audio:
            raise ValueError("Every recording needs reference text and an audio path")
        if pathlib.Path(audio).is_absolute():
            raise ValueError("Audio paths must be relative to the manifest")
        az = row.get("azure_result")
        if az is not None and (not isinstance(az, str) or pathlib.Path(az).is_absolute()):
            raise ValueError("Azure result path must be relative")
        samples.append(Sample(
            id=row["id"],
            reference=reference,
            audio=(path.parent / audio).resolve(),
            azure_result=(path.parent / az).resolve() if az else None,
        ))
    return samples


def read_audio_metadata(path: pathlib.Path) -> dict:
    with wave.open(str(path), "rb") as file:
        channels, width, rate = file.getnchannels(), file.getsampwidth(), file.getframerate()
        if (channels, width, rate) != (1, 2, 16000) or file.getcomptype() != "NONE":
            raise ValueError(str(path) + ": expected mono 16-kHz PCM16 WAV")
        frames = file.getnframes()
        samples = array("h", file.readframes(frames))
        if sys.byteorder != "little":
            samples.byteswap()
        peak = max(map(abs, samples), default=0)
        return {"seconds": frames / rate, "sample_rate": rate, "peak": peak, "valid_signal": peak >= 120}


def polish_match(reference: str, prediction: str) -> bool:
    def norm(text: str) -> str:
        return re.sub(r"[^\wąćęłńóśźż]+", " ", text.casefold(), flags=re.UNICODE).strip()
    return norm(reference) == norm(prediction)


def extract_azure_native(raw: dict) -> dict:
    """Preserve native scores as reported; NO legacy duration/word-error multipliers."""
    top = (raw.get("NBest") or [{}])[0]
    assessment = top.get("PronunciationAssessment") or raw.get("PronunciationAssessment") or {}
    if not assessment:
        return {"status": "inconclusive", "reason": "no Azure assessment"}
    fields = ("AccuracyScore", "FluencyScore", "CompletenessScore", "ProsodyScore")
    scores = {key: assessment[key] for key in fields if isinstance(assessment.get(key), (int, float))}
    words = []
    for word in top.get("Words", raw.get("Words", [])):
        if not isinstance(word, dict):
            continue
        pronunciation = word.get("PronunciationAssessment") or {}
        words.append({
            "word": word.get("Word"),
            "accuracy": pronunciation.get("AccuracyScore"),
            "error_type": pronunciation.get("ErrorType"),
            "phonemes": [
                {"phoneme": p.get("Phoneme"), "accuracy": (p.get("PronunciationAssessment") or {}).get("AccuracyScore")}
                for p in word.get("Phonemes", [])
            ],
        })
    return {"status": "ok", "scores": scores, "words": words, "transcript": top.get("Lexical") or top.get("Display") or raw.get("DisplayText")}


def run(manifest: pathlib.Path, engine: str, model_path: str | None, seconds_limit: float = MAX_FREE_SECONDS, recordings_limit: int = MAX_FREE_RECORDINGS) -> list[dict]:
    samples = load_manifest(manifest)
    if len(samples) > recordings_limit:
        raise ValueError("Recording cap exceeded (" + str(recordings_limit) + ")")
    checked = []
    duration = 0.0
    for item in samples:
        audio = read_audio_metadata(item.audio)
        duration += audio["seconds"]
        checked.append((item, audio))
    if duration > seconds_limit:
        raise ValueError("Audio time cap exceeded (" + str(seconds_limit) + "s)")
    model = None
    if engine == "whisper-local":
        # Explicit local path avoids downloads or surprise API spending.
        if not model_path or not pathlib.Path(model_path).is_dir():
            raise ValueError("--model must be an existing local Whisper large-v3 model directory")
        from faster_whisper import WhisperModel  # Optional; not installed for the smoke test.
        model = WhisperModel(model_path, device="auto", compute_type="auto", local_files_only=True)
    elif engine not in ("dry-run", "azure-raw"):
        raise ValueError("Unsupported engine: " + engine)
    results = []
    for item, audio in checked:
        result = {"id": item.id, "reference": item.reference, "engine": engine, "audio_seconds": round(audio["seconds"], 3)}
        if not audio["valid_signal"]:
            result.update({"status": "inconclusive", "reason": "silent or very low-level recording"})
        elif engine == "dry-run":
            result.update({"status": "ready", "reason": "audio validated; no inference performed"})
        elif engine == "azure-raw":
            if not item.azure_result or not item.azure_result.is_file():
                result.update({"status": "inconclusive", "reason": "Azure raw response missing"})
            else:
                result.update(extract_azure_native(json.loads(item.azure_result.read_text(encoding="utf-8"))))
                if result.get("transcript"):
                    result["recognized_expected_words"] = polish_match(item.reference, result["transcript"])
        else:
            assert model is not None
            segments, info = model.transcribe(str(item.audio), language="pl", beam_size=5, vad_filter=False)
            result.update({
                "status": "ok", "transcript": " ".join(segment.text.strip() for segment in segments).strip(),
                "language": info.language,
            })
            result["recognized_expected_words"] = polish_match(item.reference, result["transcript"])
            # Whisper is ASR, NOT a phoneme quality assessor. No pronunciation score here.
        results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Polish pronunciation bench — zero remote API usage")
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--engine", choices=["dry-run", "whisper-local", "azure-raw"], default="dry-run")
    parser.add_argument("--model", help="Pre-downloaded local faster-whisper large-v3 model directory")
    parser.add_argument("--output", type=pathlib.Path, help="JSONL output path (default stdout)")
    parser.add_argument("--max-seconds", type=float, default=MAX_FREE_SECONDS)
    parser.add_argument("--max-recordings", type=int, default=MAX_FREE_RECORDINGS)
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.max_recordings <= 0:
        parser.error("Caps must be positive")
    try:
        results = run(args.manifest.resolve(), args.engine, args.model, args.max_seconds, args.max_recordings)
    except (OSError, ValueError, wave.Error) as error:
        parser.error(str(error))
    output = "".join(json.dumps(asdict(r) if hasattr(r, "__dataclass_fields__") else r, ensure_ascii=False) + "\n" for r in results)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
