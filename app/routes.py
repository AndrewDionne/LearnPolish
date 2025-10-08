# app/routes.py
from pathlib import Path
from flask import Blueprint, jsonify, send_from_directory, abort
from .utils import get_azure_token
from .sets_utils import sanitize_filename  # ← fallback to slug when needed

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
# Listening audio (dev): serve docs/listening/<set>/audio/<file>
# ----------------------------
@routes_bp.route("/listening/<path:set_name>/audio/<path:fname>")
def listening_audio(set_name, fname):
    d = DOCS_DIR / "listening" / set_name / "audio"
    f = d / fname
    if not f.exists():
        routes_bp.logger.warning("Listening audio not found: %s", f)
        return "Not found", 404
    return send_from_directory(d, fname)


# ----------------------------
# Helpers that try exact path, then sanitized fallback
# ----------------------------
def _serve_mode_index(mode: str, set_name: str):
    """Serve docs/<mode>/<set>/index.html, with sanitized fallback."""
    base = DOCS_DIR / mode

    idx = base / set_name / "index.html"
    if idx.exists():
        return send_from_directory(idx.parent, idx.name)

    # fallback: sanitize whatever came in the URL
    alt = base / sanitize_filename(set_name) / "index.html"
    if alt.exists():
        return send_from_directory(alt.parent, alt.name)

    routes_bp.logger.warning("Set index not found: %s or %s", idx, alt)
    return f"❌ {mode.capitalize()} set '{set_name}' not found", 404


def _serve_set_json(set_name: str):
    """Serve docs/sets/<set>.json, with sanitized fallback."""
    base = DOCS_DIR / "sets"

    p = base / f"{set_name}.json"
    if p.exists():
        return send_from_directory(base, p.name)

    alt = base / f"{sanitize_filename(set_name)}.json"
    if alt.exists():
        return send_from_directory(base, alt.name)

    routes_bp.logger.warning("Set JSON not found: %s or %s", p, alt)
    abort(404)


# ----------------------------
# Per-mode pages (accept any unicode/path-ish name)
# ----------------------------
@routes_bp.route("/flashcards/<path:set_name>/")
def flashcards_set(set_name):
    return _serve_mode_index("flashcards", set_name)

@routes_bp.route("/practice/<path:set_name>/")
def practice_set(set_name):
    return _serve_mode_index("practice", set_name)

@routes_bp.route("/reading/<path:set_name>/")
def reading_set(set_name):
    return _serve_mode_index("reading", set_name)

@routes_bp.route("/listening/<path:set_name>/")
def listening_set(set_name):
    return _serve_mode_index("listening", set_name)

@routes_bp.route("/test/<path:set_name>/")
def test_set(set_name):
    return _serve_mode_index("test", set_name)


# ----------------------------
# Canonical JSON accessor (helps when UI asks by display name)
# ----------------------------
@routes_bp.route("/sets/<path:set_name>.json")
def set_json(set_name):
    return _serve_set_json(set_name)
