"""Canonical V2 single-process Render host.

FREE mode (default) serves offline-first V2 with no server-side user database.
Render Free filesystem is ephemeral: enabling SQLite family accounts on a free
instance would lose private accounts/progress on idle spin-down. Never do that.
An explicitly enabled family deployment still requires independent durable DB,
verified origin, and live SMTP. It is NOT enabled by the free Blueprint.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from urllib.parse import quote, urlparse

from flask import Flask, jsonify, make_response, send_from_directory

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
                      require_email: bool | None = None,
                      family_mode: str | None = None):
    root = Path(__file__).resolve().parents[1]
    dist = (Path(dist_path) if dist_path is not None else root / "frontend" / "dist").resolve()
    catalog = dist / "generated" / "lessons.json"
    if not (dist / "index.html").is_file() or not catalog.is_file() or not (dist / "sw.js").is_file():
        raise RuntimeError("Canonical V2 production build is missing")

    mode = family_mode if family_mode is not None else os.getenv("PTP_RENDER_FAMILY_MODE", "disabled")
    if mode not in {"disabled", "enabled"}:
        raise RuntimeError("PTP_RENDER_FAMILY_MODE must be explicitly disabled or enabled")
    family_enabled = mode == "enabled"
    database = ""

    if family_enabled:
        database = database_path or os.getenv("PTP_FAMILY_DB", "")
        if not database or not Path(database).is_absolute():
            raise RuntimeError("A persistent absolute PTP_FAMILY_DB is required")
        origin = _trusted_origin(public_origin or os.getenv("PTP_PUBLIC_ORIGIN", ""))
        email_required = (os.getenv("PTP_RENDER_REQUIRE_EMAIL", "1") == "1"
                          if require_email is None else require_email)
        if email_required and (configured_sender("verification") is None or
                               configured_sender("recovery") is None):
            raise RuntimeError("Live V2 account verification/recovery SMTP must be configured")
        app = create_family_app(database_path=database, catalog_path=str(catalog),
                                allowed_origins=(origin,))
    else:
        # The Free plan has NO durable private SQLite. Don't initialize family
        # routes or issue accounts that vanish on the next Render sleep/restart.
        app = Flask(__name__)

        @app.route("/api/v2/family/<path:unused>", methods=["GET", "POST", "OPTIONS"])
        def unavailable(unused: str):
            response = jsonify(error="family_service_not_connected")
            response.status_code = 503
            response.headers["Cache-Control"] = "no-store"
            return response

    def storage_ready() -> bool:
        if not (dist / "index.html").is_file() or not catalog.is_file() or not (dist / "sw.js").is_file():
            return False
        if not family_enabled:
            return True
        path = Path(database)
        if not path.is_file() or path.is_symlink():
            return False
        try:
            # Read-only probe; never create a DB to satisfy a health request.
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
        response = jsonify(ready=ok, family_available=family_enabled and ok)
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
            response.headers["Cache-Control"] = "no-store"
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
            response = make_response("Path to Polish is starting. Please try again.", 503)
            response.headers["Retry-After"] = "5"
            response.headers["Cache-Control"] = "no-store"
            return response
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
