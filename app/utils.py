# app/utils.py
"""
Lightweight utilities used by the API:
- get_azure_token(): fetch short-lived Azure Speech token (used by /api/token)
- open_browser(): tiny dev helper (optional)
"""

import os
import logging
from urllib.parse import urlparse
from flask import jsonify
import requests
from pathlib import Path
from .constants import PAGES_DIR

logging.basicConfig(level=logging.INFO)

def asset_url(path: str) -> str | None:
    """
    Build a public CDN URL for an object key from env R2_CDN_BASE.
    Returns None if not configured.
    """
    base = (os.getenv("R2_CDN_BASE") or "").rstrip("/")
    if not base:
        return None
    return f"{base}/{path.lstrip('/')}"

def _norm_region(val: str | None) -> str | None:
    """Normalize Azure region strings like 'Germany West Central' -> 'germanywestcentral'."""
    if not val:
        return None
    s = val.strip().lower()
    # remove spaces and hyphens; keep letters/numbers (handles things like 'eastus2')
    return "".join(ch for ch in s if ch.isalnum())

def get_azure_token():
    """
    Request a temporary Azure Speech token.

    Env:
      - AZURE_SPEECH_KEY        (required)
      - AZURE_SPEECH_REGION     (preferred) or AZURE_REGION (fallback) e.g. 'germanywestcentral'
      - AZURE_SPEECH_ENDPOINT   (optional; e.g., 'https://germanywestcentral.api.cognitive.microsoft.com')
                                 If set, we'll use '<endpoint>/sts/v1.0/issueToken'

    Returns JSON: { "token": "<jwt>", "region": "<region>" }
    """
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    REGION_RAW = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_REGION")
    REGION = _norm_region(REGION_RAW)
    ENDPOINT = os.getenv("AZURE_SPEECH_ENDPOINT")

    # Do NOT print secrets. Only log presence.
    if not AZURE_SPEECH_KEY:
        logging.error("❌ AZURE_SPEECH_KEY missing")
        return jsonify({"error": "AZURE_SPEECH_KEY missing"}), 500

    if not REGION and not ENDPOINT:
        logging.error("❌ Neither AZURE_SPEECH_REGION/AZURE_REGION nor AZURE_SPEECH_ENDPOINT provided")
        return jsonify({"error": "AZURE_SPEECH_REGION missing"}), 500

    if ENDPOINT:
        base = ENDPOINT.rstrip("/")
        url = f"{base}/sts/v1.0/issueToken"
        # If REGION wasn't set but ENDPOINT was, infer region from host for the client
        if not REGION:
            try:
                host = urlparse(base).hostname or ""
                # hostname like 'germanywestcentral.api.cognitive.microsoft.com'
                REGION = host.split(".")[0] if host else None
            except Exception:
                REGION = None
    else:
        url = f"https://{REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Length": "0",
    }

    try:
        # Short timeout to avoid hanging the UI
        res = requests.post(url, headers=headers, timeout=10)
        res.raise_for_status()
        return jsonify({"token": res.text, "region": REGION})
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


def open_browser():
    """Open local dev server in a browser (optional convenience)."""
    import webbrowser, threading
    threading.Timer(1.2, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()


# --- Mode landing page builders (docs/<mode>/index.html) --------------------

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

_REDIRECT_TMPL = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=../learn.html?view=my&mode={mode}">
  <link rel="prefetch" href="../learn.html?view=my&mode={mode}">
  <link rel="stylesheet" href="../static/app.css">
  <script>location.replace('../learn.html?view=my&mode={mode}');</script>
</head>
<body>
  <main class="container" style="padding:16px">
    <p>Redirecting to <a href="../learn.html?view=my&mode={mode}">Learn • {label}</a>…</p>
    <noscript><p><strong>JavaScript is off.</strong> Use the link above.</p></noscript>
  </main>
</body>
</html>
"""

def build_mode_index(mode: str) -> Path:
    """
    Write docs/<mode>/index.html as a redirect to the shared Learn page
    with the appropriate filter. Keeps legacy links working.
    """
    outdir = PAGES_DIR / mode
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
