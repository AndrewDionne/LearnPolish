"""Curl transport for Groq research; never put the API key in argv.

The owner's Mac demonstrated curl GET /models HTTP 200 where Python urllib
GET /models returned HTTP 403. This is a transport choice, NOT a permission
bypass or evidence that Whisper inference is authorized.

No retries, redirects, provider-response logging, or implicit upload.
Secrets pass as a curl config through stdin, never a CLI argument.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Callable

MAX_RESPONSE_BYTES = 262144


def request_json(url: str, api_key: str, *, audio: Path | None = None,
                 model: str | None = None, timeout: int = 15,
                 runner: Callable | None = None) -> tuple[int, object]:
    """One request only. Returns HTTP status and decoded JSON; never prints body.

    The caller must enforce manifest integrity, budget, upload permission,
    account state, and model allowlist BEFORE selecting an audio request.
    """
    if url not in (
        "https://api.groq.com/openai/v1/models",
        "https://api.groq.com/openai/v1/audio/transcriptions",
    ):
        raise ValueError("Only documented Groq endpoints are allowed")
    if not isinstance(api_key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", api_key):
        raise ValueError("GROQ_API_KEY must be a non-empty normal API key; do not paste it")
    if not 1 <= timeout <= 60:
        raise ValueError("Invalid curl timeout")
    if (audio is None) != (url.endswith("/models")):
        raise ValueError("GET /models cannot upload audio; transcription requires a WAV")
    if audio is not None and model not in ("whisper-large-v3", "whisper-large-v3-turbo"):
        raise ValueError("Only approved Whisper model names may be sent")
    args = [
        "curl", "--silent", "--show-error", "--max-time", str(timeout),
        "--connect-timeout", "10", "--max-redirs", "0",
        "--proto", "=https",
        "--write-out", "\n%{http_code}",
        "--config", "-", "--header", "Accept: application/json",
    ]
    if audio is None:
        args += ["--request", "GET"]
    else:
        args += [
            "--request", "POST",
            "--form", "file=@" + str(audio) + ";filename=recording.wav;type=audio/wav",
            "--form", "model=" + model,
            "--form", "language=pl",
            "--form", "response_format=json",
            "--form", "temperature=0",
        ]
    args.append(url)
    # Keep Authorization out of process arguments, GitHub logs, error
    # messages, environment overrides and result JSON. Curl reads config
    # from its stdin. Key grammar prevents injection into the config format.
    config = ('header = "Authorization: Bearer ' + api_key + '"\n').encode("ascii")
    try:
        process = (runner or subprocess.run)(
            args, input=config, capture_output=True, timeout=timeout + 3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Groq curl transport failed before HTTP response; no retry") from None
    if process.returncode != 0:
        # Curl's stderr is untrusted and may include sensitive information.
        raise RuntimeError("Groq curl transport failed (no HTTP result); no retry") from None
    try:
        body, status_raw = process.stdout.rsplit(b"\n", 1)
        status = int(status_raw)
        if not (100 <= status <= 599):
            raise ValueError("invalid HTTP status")
    except (AttributeError, ValueError):
        raise RuntimeError("Groq curl transport returned an invalid HTTP status") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Groq response exceeded permitted local size") from None
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        if status >= 400:
            payload = {}  # Status is still useful without revealing WAF error HTML.
        else:
            raise RuntimeError("Groq returned malformed JSON") from None
    return status, payload
