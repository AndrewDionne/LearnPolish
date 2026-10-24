"""Canonical V2 single-process Render host.

FREE mode (default) serves offline-first V2 with no server-side user database.
Render Free filesystem is ephemeral: enabling SQLite family accounts on a free
instance would lose private accounts/progress on idle spin-down. Never do that.
An explicitly enabled family deployment still requires independent durable DB,
verified origin, and live SMTP. It is NOT enabled by the free Blueprint.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import sqlite3
from threading import Lock
from time import monotonic
from urllib.parse import quote, urlparse

from flask import Flask, jsonify, make_response, send_from_directory

from family_api import create_app as create_family_app
from postgres_storage import postgres_ready
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
                      postgres_url: str | None = None,
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
    neon = ""

    if family_enabled:
        database = database_path or os.getenv("PTP_FAMILY_DB", "")
        neon = postgres_url or os.getenv("PTP_FAMILY_DATABASE_URL", "")
        # Render Free cannot persist SQLite. Never turn on ephemeral hosted users.
        if os.getenv("RENDER") == "true" and not neon:
            raise RuntimeError("Hosted family accounts require durable restricted Neon")
        # The public endpoint is intentionally closed to new signups unless an
        # operator independently configures a small, explicit adult test list.
        signup_mode = os.getenv("PTP_FAMILY_SIGNUP_MODE", "closed")
        if signup_mode not in {"closed", "adult-pilot"}:
            raise RuntimeError("Public/minor family signup is not authorized")
        raw_pilot = os.getenv("PTP_FAMILY_PILOT_EMAILS", "")
        pilot_emails = tuple(x.strip().lower() for x in raw_pilot.split(",") if x.strip())
        if len(pilot_emails) > 12 or len(pilot_emails) != len(set(pilot_emails)) or any(
                not x or not re.fullmatch(r"[^@\s]{1,100}@[^@\s]{1,100}\.[^@\s]{2,30}",x)
                for x in pilot_emails):
            raise RuntimeError("Invalid adult pilot email allowlist")
        if signup_mode == "adult-pilot" and not pilot_emails:
            raise RuntimeError("Adult pilot enrollment requires an email allowlist")
        approved_pilot = pilot_emails if signup_mode == "adult-pilot" else ()
        # The Neon Console/API creates highly privileged DB roles by default;
        # require the separately created SQL role with only ptp_v2 access.
        if neon and urlparse(neon).username != "ptp_v2_runtime":
            raise RuntimeError("V2 production requires the least-privilege Neon runtime role")
        if bool(database) == bool(neon):
            raise RuntimeError("Configure exactly one durable V2 database: Neon or private SQLite")
        if database and not Path(database).is_absolute():
            raise RuntimeError("A persistent absolute PTP_FAMILY_DB is required")
        origin = _trusted_origin(public_origin or os.getenv("PTP_PUBLIC_ORIGIN", ""))
        email_required = (os.getenv("PTP_RENDER_REQUIRE_EMAIL", "1") == "1"
                          if require_email is None else require_email)
        if email_required and (configured_sender("verification") is None or
                               configured_sender("recovery") is None):
            raise RuntimeError("Live V2 account verification/recovery SMTP must be configured")
        app = create_family_app(database_path=database or None,
                                postgres_url=neon or None,
                                catalog_path=str(catalog),
                                allowed_origins=(origin,),
                                pilot_adult_emails=approved_pilot)
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

    # Shared readiness snapshot: static V2 assets must not create a new Neon
    # connection per CSS/JS/audio request (or keep a free DB awake unnecessarily).
    # A failed probe is retried promptly; a healthy probe has a bounded TTL.
    readiness_cache = {"checked_at": float("-inf"), "ok": False}
    readiness_lock = Lock()

    def storage_ready() -> bool:
        if not (dist / "index.html").is_file() or not catalog.is_file() or not (dist / "sw.js").is_file():
            return False
        if not family_enabled:
            return True
        if neon:
            with readiness_lock:
                now = monotonic()
                ttl = 30 if readiness_cache["ok"] else 5
                if now - readiness_cache["checked_at"] >= ttl:
                    readiness_cache["ok"] = postgres_ready(neon)
                    readiness_cache["checked_at"] = now
                return readiness_cache["ok"]
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
