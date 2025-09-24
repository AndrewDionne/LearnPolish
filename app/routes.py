# app/routes.py
from pathlib import Path
from flask import Blueprint, jsonify, send_from_directory

from .utils import get_azure_token  # your existing helper

routes_bp = Blueprint("routes", __name__)

# Path to the docs directory that we serve as the static site
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


# ----------------------------
# Azure Speech Token endpoint
# ----------------------------
@routes_bp.route("/api/token", methods=["GET"])
def azure_token():
    try:
        return get_azure_token()
    except Exception as e:
        routes_bp.logger.error(f"Azure token endpoint error: {e}", exc_info=True)
        return jsonify({"error": "endpoint_failed", "detail": str(e)}), 500


# ----------------------------
# Local static (dev) for audio, etc.
#   e.g. /custom_static/<set>/audio/<file>.mp3
# ----------------------------
@routes_bp.route("/custom_static/<path:filename>")
def custom_static(filename):
    static_root = DOCS_DIR / "static"
    target = static_root / filename
    if not target.exists():
        routes_bp.logger.warning("Static not found: %s", target)
        return "Not found", 404
    return send_from_directory(static_root, filename)


# ----------------------------
# Directory index helpers for mode pages in dev
#   so /flashcards/<set>/ serves docs/flashcards/<set>/index.html
#   (GitHub Pages does this automatically)
# ----------------------------
def _serve_mode_index(mode: str, set_name: str):
    idx = DOCS_DIR / mode / set_name / "index.html"
    if not idx.exists():
        return f"❌ {mode.capitalize()} set '{set_name}' not found", 404
    return send_from_directory(idx.parent, idx.name)


@routes_bp.route("/flashcards/<set_name>/")
def flashcards_set(set_name):
    return _serve_mode_index("flashcards", set_name)


@routes_bp.route("/practice/<set_name>/")
def practice_set(set_name):
    return _serve_mode_index("practice", set_name)


@routes_bp.route("/reading/<set_name>/")
def reading_set(set_name):
    return _serve_mode_index("reading", set_name)


@routes_bp.route("/listening/<set_name>/")
def listening_set(set_name):
    return _serve_mode_index("listening", set_name)


@routes_bp.route("/test/<set_name>/")
def test_set(set_name):
    return _serve_mode_index("test", set_name)
