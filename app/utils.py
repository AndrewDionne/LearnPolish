# app/utils.py
"""
Lightweight utilities used by the API:

- get_azure_token(): fetch short-lived Azure Speech token (used by /api/token)
- open_browser(): tiny dev helper (optional)

All set creation/deletion and page generation logic now lives in:
  - app/sets_utils.py  (create_set, delete_set_file, etc.)
  - app/flashcards.py, app/practice.py, app/reading.py (generators)

This file intentionally has no Jinja/template exports anymore.
"""

import os
import logging
from flask import jsonify
import requests

# Configure logging level if not set elsewhere
logging.basicConfig(level=logging.INFO)


def open_browser():
    """Open local dev server in a browser (optional convenience)."""
    import webbrowser, threading
    threading.Timer(1.2, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()


def get_azure_token():
    """
    Request a temporary Azure Speech token.

    Looks for:
      - AZURE_SPEECH_KEY   (required)
      - AZURE_REGION       (default: canadaeast)

    Returns JSON: { "token": "<jwt>", "region": "<region>" }
    """
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    AZURE_REGION = os.getenv("AZURE_REGION", "canadaeast")

    # Do NOT print secrets. Only log presence.
    if not AZURE_SPEECH_KEY:
        logging.error("❌ AZURE_SPEECH_KEY missing")
        return jsonify({"error": "AZURE_SPEECH_KEY missing"}), 500

    if not AZURE_REGION:
        logging.error("❌ AZURE_REGION missing")
        return jsonify({"error": "AZURE_REGION missing"}), 500

    url = f"https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Length": "0",
    }

    try:
        # Short timeout to avoid hanging the UI
        res = requests.post(url, headers=headers, timeout=10)
        res.raise_for_status()
        return jsonify({"token": res.text, "region": AZURE_REGION})
    except requests.HTTPError as e:
        body = e.response.text if getattr(e, "response", None) else "No response"
        logging.error("❌ Azure HTTPError: %s | Response: %s", e, body)
        return jsonify({"error": "token_request_failed", "detail": str(e)}), 502
    except requests.RequestException as e:
        logging.error("❌ Azure RequestException: %s", e)
        return jsonify({"error": "token_request_failed", "detail": str(e)}), 502
    except Exception as e:
        logging.error("❌ Unexpected Azure token error: %s", e)
        return jsonify({"error": "unexpected_error", "detail": str(e)}), 500

# --- Mode landing page builders (docs/<mode>/index.html) --------------------
from pathlib import Path

# Map classic folders → Learn page filter
_LEARN_MODE_MAP = {
    "flashcards": "vocab",
    "practice":   "speak",
    "reading":    "read",
    "listening":  "listen",
    "test":       "all",   # send to Learn with no specific filter
}

def _mode_label(mode: str) -> str:
    return {
        "flashcards": "Vocabulary",
        "practice":   "Speak",
        "reading":    "Read",
        "listening":  "Listen",
        "test":       "Learn",
    }.get(mode, mode.capitalize())

_REDIRECT_TMPL = """<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta http-equiv="refresh" content="0; url=../learn.html?view=my&mode={mode}">
  <script>location.replace('../learn.html?view=my&mode={mode}');</script>
</head><body>
  <p>Redirecting to <a href="../learn.html?view=my&mode={mode}">Learn • {label}</a>…</p>
</body></html>
"""

def build_mode_index(mode: str) -> Path:
    """
    Write docs/<mode>/index.html as a redirect to the shared Learn page
    with the appropriate filter. Keeps legacy links working.
    """
    outdir = Path("docs") / mode
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "index.html"

    target_mode = _LEARN_MODE_MAP.get(mode, "all")
    html = _REDIRECT_TMPL.format(title=_mode_label(mode), mode=target_mode, label=_mode_label(mode))
    outfile.write_text(html, encoding="utf-8")
    print(f"↪︎ Wrote redirect index for '{mode}' → learn.html?view=my&mode={target_mode}")
    return outfile

def build_all_mode_indexes() -> None:
    # Keep the same set of modes you previously generated
    for mode in ["flashcards", "practice", "reading", "listening", "test"]:
        try:
            build_mode_index(mode)
        except Exception as e:
            print(f"⚠️ Skipped {mode} index: {e}")

