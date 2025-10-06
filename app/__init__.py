# app/__init__.py
"""
Flask app factory for LearnPolish.

- Serves the static site from /docs (same layout as GitHub Pages).
- Exposes JSON APIs under /api (auth, scores, sets).
- Provides convenience routes so local dev mirrors GH Pages.
"""

import os
from pathlib import Path
from .config import CORS_ORIGINS
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from .constants import PAGES_DIR  # PAGES_DIR = Path("docs")
# Load .env for local dev (safe no-op in prod)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    import os

    ROOT = Path(__file__).resolve().parents[1]
    DOTENV = ROOT / ".env"

    IN_RENDER = bool(os.getenv("RENDER"))
    IS_DEV = (
        os.getenv("FLASK_ENV") == "development"
        or os.getenv("FLASK_DEBUG") == "1"
        or os.getenv("APP_ENV", "development") == "development"
    )
    # Allow manual override via env if needed
    FORCE = (os.getenv("DOTENV_OVERRIDE", "").lower() in {"1", "true", "yes"})

    # In dev (and not on Render) let .env win; otherwise let OS env win
    load_dotenv(dotenv_path=DOTENV, override=(FORCE or (IS_DEV and not IN_RENDER)))
except Exception:
    # Don't hard-fail if python-dotenv isn't installed
    pass



# ----------------------------
# Config
# ----------------------------
try:
    # Prefer a single canonical Config in app/config.py
    from .config import Config
except Exception as e:
    # Minimal fallback if config.py is missing; OK for dev only
    import secrets
    class Config:
        SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-" + secrets.token_urlsafe(32))
        JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY
        FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5000")
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        JSON_AS_ASCII = False
        TEMPLATES_AUTO_RELOAD = True

# CORS origins (from config.py if provided; else sensible defaults)
try:
    from .config import CORS_ALLOWED_ORIGINS
except Exception:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://andrewdionne.github.io",
    ]

# Global SQLAlchemy instance (imported by models.py)
db = SQLAlchemy()


def create_app():
    """Flask application factory."""
    # Resolve important paths
    root_dir = Path(__file__).resolve().parent.parent
    docs_dir = root_dir / "docs"

    # Serve the static site directly from /docs (parity with GH Pages)
    app = Flask(
        __name__,
        static_folder=str(docs_dir),
        static_url_path="",  # make docs content available at /
    )

    # Load base config first
    app.config.from_object(Config)

    # Instance folder & DB path
    os.makedirs(app.instance_path, exist_ok=True)
    db_uri = os.getenv("DATABASE_URL")
    if db_uri and db_uri.startswith("postgres://"):
        # SQLAlchemy requires postgresql://
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    if not db_uri:
        db_uri = f"sqlite:///{Path(app.instance_path) / 'learnpolish.db'}"

    # Apply/override runtime config
    app.config.update(
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_AS_ASCII=False,
        TEMPLATES_AUTO_RELOAD=True,
    )
    # Ensure FRONTEND_BASE_URL has a value even if Config omitted it
    app.config.setdefault("FRONTEND_BASE_URL", os.getenv("FRONTEND_BASE_URL", "http://localhost:5000"))
    # If JWT_SECRET missing, fall back to SECRET_KEY (keeps old behavior)
    app.config.setdefault("JWT_SECRET", app.config.get("SECRET_KEY"))

    # Kill static caching in dev to avoid stale HTML/JS
    if os.getenv("FLASK_DEBUG") == "1" or os.getenv("FLASK_ENV") == "development":
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    # Init DB
    db.init_app(app)

    # --- CORS setup (expanded for Safari/iOS) ---
    CORS(
        app,
        resources={r"/api/*": {"origins": CORS_ALLOWED_ORIGINS}},
        supports_credentials=False,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["Content-Type", "Content-Length", "ETag"],
        max_age=86400,
    )


    # ----------------------------
    # Blueprints
    # ----------------------------
    from .auth import auth_bp
    from .api import api_bp             # scores, groups, misc API
    from .sets_api import sets_api      # sets CRUD for user/global
    from .routes import routes_bp       # token endpoint, /custom_static, per-set pages

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(sets_api, url_prefix="/api")
    app.register_blueprint(routes_bp)  # top-level routes for per-set pages

    # ----------------------------
    # Convenience static routes (local dev parity)
    # ----------------------------
    @app.route("/")
    def docs_root():
        return send_from_directory(docs_dir, "index.html")

    @app.route("/docs/<path:filename>")
    def docs_files(filename: str):
        return send_from_directory(docs_dir, filename)

    @app.route("/manage_sets/")
    def docs_manage_sets_index():
        p = docs_dir / "manage_sets" / "index.html"
        return send_from_directory(p.parent, p.name) if p.exists() \
            else send_from_directory(docs_dir, "manage_sets.html")

    @app.route("/create_page")
    def docs_create_index():
        p = docs_dir / "create" / "index.html"
        return send_from_directory(p.parent, p.name) if p.exists() \
            else send_from_directory(docs_dir, "create.html")

    # Auth pages served from /docs
    @app.route("/login.html")
    def docs_login():
        return send_from_directory(docs_dir, "login.html")

    @app.route("/register.html")
    def docs_register():
        return send_from_directory(docs_dir, "register.html")

    @app.route("/reset.html")
    def docs_reset():
        return send_from_directory(docs_dir, "reset.html")

    @app.route("/reset_confirm.html")
    def docs_reset_confirm():
        return send_from_directory(docs_dir, "reset_confirm.html")

    # ---------- Mode landing pages (docs/<mode>/index.html) ----------
    def _serve_mode_index(mode: str):
        p = docs_dir / mode / "index.html"
        if not p.exists():
            # Optional: auto-build if missing
            try:
                from .utils import build_mode_index
                build_mode_index(mode)
            except Exception as e:
                print(f"⚠️ Couldn't auto-build {mode} index: {e}")
        return send_from_directory(p.parent, p.name)

    def _register_mode_index_routes(app: Flask):
        routes = {
            "docs_flashcards_index": ("/flashcards/",  lambda: _serve_mode_index("flashcards")),
            "docs_practice_index":   ("/practice/",   lambda: _serve_mode_index("practice")),
            "docs_reading_index":    ("/reading/",    lambda: _serve_mode_index("reading")),
            "docs_listening_index":  ("/listening/",  lambda: _serve_mode_index("listening")),
            "docs_test_index":       ("/test/",       lambda: _serve_mode_index("test")),
        }
        for endpoint, (rule, view) in routes.items():
            if endpoint not in app.view_functions:   # guard prevents duplicates
                app.add_url_rule(rule, endpoint, view)

    _register_mode_index_routes(app)

    # Healthcheck
    @app.route("/ping")
    def ping():
        return "✅ LearnPolish API is running"

    # Optional debug prints (don’t print actual secret values)
    print("🔑 AZURE_SPEECH_KEY set:", bool(os.getenv("AZURE_SPEECH_KEY")))
    print("🌎 AZURE_SPEECH_REGION:", os.getenv("AZURE_SPEECH_REGION"))

    return app
