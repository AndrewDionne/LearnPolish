"""Same-origin V2 web host. Render serves no frontend shell until its family API is ready.

This is intentionally NOT the legacy Flask application. A persistent family
SQLite path and explicit trusted browser origin are mandatory in production.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

from flask import jsonify, make_response, send_from_directory
from family_api import create_app as create_family_app
from recovery_mail import configured_sender


def _trusted_origin(value: str) -> str:
    parsed = urlparse(value)
    local = parsed.hostname in {"localhost", "127.0.0.1"}
    if (not parsed.hostname or (parsed.scheme != "https" and
        not (local and parsed.scheme == "http")) or
        parsed.path not in {"", "/"} or parsed.query or parsed.fragment or
        parsed.username or parsed.password or "*" in value):
        raise RuntimeError("PTP_PUBLIC_ORIGIN must be an exact HTTPS origin (or local loopback)")
    return parsed.scheme + "://" + parsed.netloc


def create_render_app(*, dist_path: str | Path | None = None,
                      database_path: str | None = None,
                      public_origin: str | None = None,
                      require_email: bool | None = None):
    root = Path(__file__).resolve().parents[1]
    dist = Path(dist_path) if dist_path is not None else root / "frontend" / "dist"
    dist = dist.resolve()
    catalog = dist / "generated" / "lessons.json"
    if not (dist / "index.html").is_file() or not catalog.is_file() or not (dist / "sw.js").is_file():
        raise RuntimeError("Canonical V2 production build is missing")
    database = database_path or os.getenv("PTP_FAMILY_DB", "")
    if not database or not Path(database).is_absolute():
        raise RuntimeError("A persistent absolute PTP_FAMILY_DB is required")
    origin = _trusted_origin(public_origin or os.getenv("PTP_PUBLIC_ORIGIN", ""))
    email_required = os.getenv("PTP_RENDER_REQUIRE_EMAIL", "1") == "1" if require_email is None else require_email
    if email_required and (configured_sender("verification") is None or
                           configured_sender("recovery") is None):
        raise RuntimeError("Live V2 account verification/recovery SMTP must be configured before serving the app")

    # The same application and worker handle family endpoints AND its frontend.
    app = create_family_app(database_path=database, catalog_path=str(catalog),
                            allowed_origins=(origin,))

    def storage_ready() -> bool:
        # Read-only probe; never create a new DB in a health request.
        path = Path(database)
        if not path.is_file() or path.is_symlink() or not catalog.is_file():
            return False
        try:
            # SQLite's read-only URI is only used for this harmless health probe.
            from urllib.parse import quote
            with sqlite3.connect("file:" + quote(str(path), safe="/") + "?mode=ro",
                                 uri=True, timeout=2) as con:
                return con.execute(
                    "SELECT count(*) FROM sqlite_master "
                    "WHERE type='table' AND name IN ('users','activities')"
                ).fetchone()[0] == 2
        except (sqlite3.Error, OSError):
            return False

    @app.get("/health/ready")
    def ready():
        ok = storage_ready()
        response = jsonify(ready=ok)
        response.status_code = 200 if ok else 503
        response.headers["Cache-Control"] = "no-store"
        if not ok:
            response.headers["Retry-After"] = "5"
        return response

    @app.get("/")
    def index():
        if not storage_ready():
            response = make_response("Path to Polish is starting. Please try again.", 503)
            response.headers["Retry-After"] = "5"
            return response
        response = send_from_directory(dist, "index.html")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/<path:asset>")
    def asset(asset: str):
        if (asset.startswith(("api/", "health/")) or
            any(part in {"", ".", ".."} or part.startswith(".") for part in asset.split("/"))):
            return "", 404
        if not storage_ready():
            return "Path to Polish is starting. Please try again.", 503
        candidate = dist / asset
        if not candidate.is_file():
            return "", 404
        response = send_from_directory(dist, asset)
        if asset == "sw.js":
            response.headers["Cache-Control"] = "no-cache"
        elif asset.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    return app
