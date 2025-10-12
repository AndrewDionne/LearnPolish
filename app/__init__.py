# app/__init__.py
import os
import re
from urllib.parse import urlparse
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from .config import Config
from .models import db


def _normalize_db_url(u: str | None) -> str | None:
    if not u:
        return None

    scheme = u.split(":", 1)[0]
    is_postgres = scheme.startswith("postgres")

    # psycopg3 prefers the explicit driver marker.  Normalize the
    # DATABASE_URL so we always end up with postgresql+psycopg:// which
    # works with the psycopg package already listed in requirements.
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql://", 1)
    if u.startswith("postgresql://") and "+" not in u.split(":", 1)[0]:
        u = u.replace("postgresql://", "postgresql+psycopg://", 1)

    # Enforce SSL defaults for postgres connections (Render et al). Avoid
    # touching sqlite or other schemes which do not understand sslmode.
    if is_postgres and "sslmode=" not in u:
        sep = "&" if "?" in u else "?"
        u = f"{u}{sep}sslmode=require"

    return u


def _resolve_db_url() -> str | None:
    """Return the first configured database URL with Render-friendly tweaks."""

    candidates = [
        "DATABASE_URL",
        "DATABASE_CONNECTION_STRING",
        "DATABASE_INTERNAL_URL",
        "DATABASE_URL_INTERNAL",
        "DB_URL",
        "POSTGRES_URL",
        "POSTGRESQL_URL",
    ]

    for name in candidates:
        raw = os.getenv(name)
        if raw:
            normalized = _normalize_db_url(raw)
            if normalized:
                return normalized

    fallback = os.getenv("SQLALCHEMY_DATABASE_URI")
    if fallback:
        return _normalize_db_url(fallback) or fallback

    try:
        from .config import Config

        default = getattr(Config, "SQLALCHEMY_DATABASE_URI", "")
        if default:
            normalized = _normalize_db_url(default)
            return normalized or default
    except Exception:
        pass

    return None


def _derive_allowed_origins() -> list[str]:
    # If explicitly provided, honor it
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if env_origins.strip():
        return [o.strip() for o in env_origins.split(",") if o.strip()]

    # Otherwise, infer from FRONTEND_BASE_URL + localhost dev ports
    base = os.getenv("FRONTEND_BASE_URL", "").strip()
    app_base = os.getenv("APP_BASE_URL", "").strip()
    api_base = os.getenv("API_BASE_URL", "").strip()
    origins: list[object] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        "https://path-to-polish.onrender.com",
        "https://pathtopolish.com",
        "https://www.pathtopolish.com",
        "https://*.pathtopolish.com",
        "https://*.polishpath.com",
        "https://*.github.io",
        "https://andrewdionne.github.io",
    ]
    for candidate in filter(None, (base, app_base, api_base)):
        try:
            u = urlparse(candidate)
            if u.scheme and u.netloc:
                origin = f"{u.scheme}://{u.netloc}"
                if origin not in origins:
                    origins.append(origin)
        except Exception:
            continue
        # Loosen slightly for GH Pages repos (optional; harmless if unused)

        if "github.io" in candidate:
            if "https://*.github.io" not in origins:
                origins.append("https://*.github.io")

    # Preserve insertion order while deduplicating for readability in logs/tests.
    seen = set()
    deduped = []
    for item in origins:
        key = item.pattern if isinstance(item, re.Pattern) else item
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Secrets / misc ---
    secret = (
        os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET")  # fallback if you only set JWT_SECRET
        or app.config.get("SECRET_KEY")
        or "dev-secret-change-me"
    )
    app.config["SECRET_KEY"] = secret
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET") or secret

    # Bridge Cloudflare R2 endpoint naming:
    # prefer R2_ENDPOINT; fall back to your existing R2_S3_ENDPOINT
    if not os.getenv("R2_ENDPOINT") and os.getenv("R2_S3_ENDPOINT"):
        os.environ["R2_ENDPOINT"] = os.getenv("R2_S3_ENDPOINT")

    # --- Database ---
    db_url = _resolve_db_url()
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL not configured. Set one of: "
            "DATABASE_URL, DATABASE_CONNECTION_STRING, DATABASE_INTERNAL_URL."
        )
    app.config.update(
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
    )
    db.init_app(app)

    # --- CORS ---
    allowed = _derive_allowed_origins()
    strict_cors = os.getenv("CORS_STRICT", "0").lower() in ("1", "true", "yes", "on")
    cors_allow_list: list[object] = []
    for item in allowed:
        if isinstance(item, str) and item.startswith("regex:"):
            try:
                cors_allow_list.append(re.compile(item.split(":", 1)[1]))
            except re.error:
                continue
        else:
            cors_allow_list.append(item)
    cors_origins = cors_allow_list if (strict_cors and cors_allow_list) else "*"
    supports_credentials = bool(cors_origins != "*")

    resources = {
        r"/api/*": {"origins": cors_origins},
        r"/api/healthz": {"origins": cors_origins},
        r"/ping": {"origins": cors_origins},
    }

    CORS(
        app,
        origins=cors_origins,
        resources=resources,
        supports_credentials=supports_credentials,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        expose_headers=["Content-Type", "Authorization"],
        send_wildcard=(cors_origins == "*"),
        vary_header=True,
    )

    literal_origins = {
        o for o in allowed if isinstance(o, str) and "*" not in o and not o.startswith("regex:")
    }
    wildcard_patterns = []
    for item in allowed:
        if isinstance(item, str) and item.startswith("regex:"):
            try:
                wildcard_patterns.append(re.compile(item.split(":", 1)[1]))
            except re.error:
                continue
        elif isinstance(item, str) and "*" in item:
            pattern = "^" + re.escape(item).replace("\\*", ".*") + "$"
            wildcard_patterns.append(re.compile(pattern))
        elif hasattr(item, "match"):
            wildcard_patterns.append(item)

    def _origin_allowed(origin: str | None) -> bool:
        if not origin:
            return False
        if cors_origins == "*":
            return True
        if origin in literal_origins:
            return True
        return any(p.match(origin) for p in wildcard_patterns)

    from flask import request as flask_request

    @app.after_request
    def ensure_cors_headers(resp):
        origin = flask_request.headers.get("Origin")

        if _origin_allowed(origin):
            allow_origin = origin or "*"
            resp.headers.setdefault("Access-Control-Allow-Origin", allow_origin)
            resp.headers.setdefault(
                "Access-Control-Allow-Methods",
                "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
            )
            resp.headers.setdefault(
                "Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With"
            )
            if supports_credentials:
                resp.headers.setdefault("Access-Control-Allow-Credentials", "true")
            resp.headers.setdefault("Vary", "Origin")
        return resp
     
        # --- Fast CORS preflight for any /api/* route ---
    @app.route("/api/<path:_subpath>", methods=["OPTIONS"])
    def _cors_preflight(_subpath):
        return ("", 204)

    # --- Health routes (fast, no DB, no auth) ---
    @app.get("/api/healthz")
    def healthz():
        return jsonify(status="ok", time=datetime.now(timezone.utc).isoformat()), 200

    # Keep legacy /ping working by pointing it to the same handler
    app.add_url_rule("/ping", view_func=healthz, methods=["GET"])


    # --- Blueprints ---
    from .auth import auth_bp
    from .api import api_bp
    try:
        from .sets_api import sets_api as sets_bp
    except Exception:
        sets_bp = None
    try:
        from .routes import routes_bp
    except Exception:
        routes_bp = None

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(api_bp,  url_prefix="/api")
    if sets_bp:
        app.register_blueprint(sets_bp, url_prefix="/api")
    if routes_bp:
        app.register_blueprint(routes_bp)  # usually no prefix
    # --- Optional DB init (dev/local only) ---
    if os.getenv("AUTO_INIT_DB", "0").lower() in ("1", "true", "yes"):
        with app.app_context():
            db.create_all()

    # --- JSON for unexpected errors (keeps logs clean for Render) ---
    @app.errorhandler(Exception)
    def on_error(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e  # let Flask handle HTTP errors normally
        app.logger.exception("Unhandled error: %s", e)
        return jsonify({"ok": False, "error": "internal_error"}), 500

    return app
