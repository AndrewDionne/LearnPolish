#!/usr/bin/env python3
"""Azure Speech F0 regional token authorization check WITHOUT audio inference.

One POST to Microsoft's documented regional STS issueToken endpoint.
Never prints the key, bearer token, headers, remote response body or SDK
error details. A successful 200 proves this key can request a regional
token, NOT that Speech websocket/pronunciation assessment works or is free.
"""
from __future__ import annotations

import json
import os
from typing import Callable
import urllib.error
import urllib.request

REGION = "germanywestcentral"
HOST = "germanywestcentral.api.cognitive.microsoft.com"
URL = "https://" + HOST + "/sts/v1.0/issueToken"


def probe(key: str, region: str, opener: Callable = urllib.request.urlopen) -> dict:
    if not isinstance(key, str) or not key:
        raise ValueError("AZURE_SPEECH_KEY missing; do not paste it into chat")
    if region != REGION:
        raise ValueError("AZURE_SPEECH_REGION must match germanywestcentral")
    req = urllib.request.Request(
        URL, data=b"", method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
    status = None
    try:
        with opener(req, timeout=15) as resp:
            status = resp.status
            # Do NOT read: the response body is a bearer token.
    except urllib.error.HTTPError as err:
        status = err.code
        err.close()  # never examine response body (may contain details)
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"status": "connection_failed", "no_audio_uploaded": True,
                "speech_inference_requests": 0, "key_and_token_never_printed": True}
    return {
        "status": ("token_issuer_authorized" if status == 200 else "token_issuer_rejected"),
        "http_status": status if status in (200, 400, 401, 403, 404, 429, 500, 502, 503, 504) else "other",
        "no_audio_uploaded": True,
        "speech_inference_requests": 0,
        "key_and_token_never_printed": True,
        "note": "A token check is not a Speech SDK websocket/pronunciation assessment test.",
    }


def main() -> int:
    try:
        result = probe(os.environ.get("AZURE_SPEECH_KEY", ""),
                       os.environ.get("AZURE_SPEECH_REGION", ""))
    except ValueError as exc:
        print(json.dumps({"status": "config_missing", "reason": str(exc),
                          "speech_inference_requests": 0}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "token_issuer_authorized" else 1


if __name__ == "__main__":
    raise SystemExit(main())
