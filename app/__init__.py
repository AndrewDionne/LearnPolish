# app/__init__.py
import os
from urllib.parse import urlparse
from flask import Flask, jsonify
from flask_cors import CORS

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
    origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
    if base:
        try:
            u = urlparse(base)
            if u.scheme and u.netloc:
                origins.add(f"{u.scheme}://{u.netloc}")
        except Exception:
            pass
        # Loosen slightly for GH Pages repos (optional; harmless if unused)
        if "github.io" in base:
            origins.add("https://*.github.io")

    return sorted(origins)


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
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed}, r"/ping": {"origins": allowed}},
        supports_credentials=True,
        expose_headers=["Content-Type", "Authorization"],
    )

    # --- Health route for Render ---
    @app.get("/ping")
    def ping():
        return jsonify({"ok": True})

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
