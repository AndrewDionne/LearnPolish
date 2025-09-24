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
from .sets_utils import list_global_sets
from .modes import modes_for_type

_INDEX_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8f9fa; padding: 2rem; }}
    h1 {{ text-align: center; margin-bottom: 2rem; }}
    .card-link a {{
      display: block; background: #ffffff; border: 1px solid #ddd; padding: 12px;
      margin: 10px auto; border-radius: 8px; text-decoration: none; color: #333;
      width: 90%; max-width: 500px; transition: background 0.2s;
    }}
    .card-link a:hover {{ background: #eef3ff; }}
    .back {{ text-align: center; margin-top: 2rem; }}
  </style>
</head>
<body>
  <h1>{heading}</h1>
  {items}
  <div class="back"><a href="/">← Back to Learning Modes</a></div>
</body>
</html>
"""

def _mode_title(mode: str) -> str:
    return {
        "flashcards": "🧠 Flashcards – Choose a Set",
        "practice":   "🎤 Pronunciation – Choose a Set",
        "reading":    "📖 Reading – Choose a Set",
        "listening":  "🎧 Listening – Choose a Set",
        "test":       "🎓 Test – Choose a Set",
    }.get(mode, f"{mode.capitalize()} – Choose a Set")

def _mode_heading(mode: str) -> str:
    return _mode_title(mode)

def build_mode_index(mode: str) -> Path:
    """
    Generate docs/<mode>/index.html listing all sets that imply this mode.
    """
    outdir = Path("docs") / mode
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "index.html"

    all_sets = list_global_sets()
    # Filter to sets whose type implies `mode`
    matches = []
    for meta in all_sets:
        implied = set(modes_for_type(meta.get("type", "unknown")))
        if mode in implied:
            matches.append(meta)

    # Build links: /<mode>/<set_name>/
    items_html = []
    for m in sorted(matches, key=lambda s: s["name"].lower()):
        name = m["name"]
        count = m.get("count", "?")
        items_html.append(
            f'<div class="card-link"><a href="{name}/">▶ {name} ({count} items)</a></div>'
        )

    html = _INDEX_TMPL.format(
        title=_mode_title(mode),
        heading=_mode_heading(mode),
        items="\n  ".join(items_html) if items_html else "<p>No sets yet.</p>",
    )
    outfile.write_text(html, encoding="utf-8")
    print(f"✅ Built mode index: {outfile}")
    return outfile

def build_all_mode_indexes() -> None:
    # Only include modes that actually exist in your codebase
    for mode in ["flashcards", "practice", "reading", "listening", "test"]:
        try:
            build_mode_index(mode)
        except Exception as e:
            print(f"⚠️ Skipped {mode} index: {e}")
