# app/__init__.py
import os
import re
from urllib.parse import urlparse, urlunparse, unquote
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS

# Optional Flask-Migrate
try:
    from flask_migrate import Migrate  # type: ignore
except Exception:  # pragma: no cover
    Migrate = None  # type: ignore[assignment]

from .config import Config
from .models import db


def _normalize_db_url(u: str | None) -> str | None:
    if not u:
        return None

    # normalize scheme and driver
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql://", 1)
    if u.startswith("postgresql://") and "+" not in u.split(":", 1)[0]:
        u = u.replace("postgresql://", "postgresql+psycopg://", 1)

    parsed = urlparse(u)
    if not parsed.scheme.startswith("postgresql"):
        return u  # don't touch sqlite or others

    # decode percent-encoded DB names (e.g. "Path%20to%20Polish%20DB")
    path = parsed.path
    if "%" in path:
        try:
            path = unquote(path)
        except Exception:
            pass

    # ensure sslmode=require unless provided
    query = parsed.query
    if "sslmode=" not in query:
        query = (query + "&" if query else "") + "sslmode=require"

    return urlunparse(parsed._replace(path=path, query=query))


def _resolve_db_url() -> str | None:
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
        default = getattr(Config, "SQLALCHEMY_DATABASE_URI", "")
        if default:
            normalized = _normalize_db_url(default)
            return normalized or default
    except Exception:
        pass
    return None


def _derive_allowed_origins() -> list[str]:
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if env_origins.strip():
        return [o.strip() for o in env_origins.split(",") if o.strip()]

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
        if "github.io" in candidate and "https://*.github.io" not in origins:
            origins.append("https://*.github.io")

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

    # --- Secrets ---
    secret = (
        os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET")
        or app.config.get("SECRET_KEY")
        or "dev-secret-change-me"
    )
    app.config["SECRET_KEY"] = secret
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET") or secret

    # Bridge Cloudflare R2 env var rename if needed
    if not os.getenv("R2_ENDPOINT") and os.getenv("R2_S3_ENDPOINT"):
        os.environ["R2_ENDPOINT"] = os.getenv("R2_S3_ENDPOINT")

    # --- Database config ---
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

    # Optional Flask-Migrate init
    if Migrate is not None:
        migrate = Migrate()
        migrate.init_app(app, db)

    # --- Bootstrap DB (one-time) ---
    from werkzeug.security import generate_password_hash

    def _bootstrap_db():
        if os.environ.get("AUTO_BOOTSTRAP_DB") != "1":
            return
        with app.app_context():
            used_migrations = False
            # Try migrations if flask_migrate is installed
            try:
                from flask_migrate import upgrade  # type: ignore
                upgrade()
                used_migrations = True
            except Exception:
                used_migrations = False

            if not used_migrations:
                # Ensure all model classes are imported, then create tables
                import app.models as _all_models  # noqa: F401
                db.create_all()

            from .models import User
            email = os.environ.get("ADMIN_EMAIL", "andrewdionne@gmail.com")
            pw = os.environ.get("ADMIN_PASSWORD")
            if pw and not User.query.filter_by(email=email).first():
                db.session.add(
                    User(
                        email=email,
                        password_hash=generate_password_hash(pw),
                        name="Andrew",
                        is_admin=True,
                    )
                )
                db.session.commit()

    _bootstrap_db()

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

    from flask import request as flask_request

    @app.after_request
    def ensure_cors_headers(resp):
        origin = flask_request.headers.get("Origin")
        if cors_origins == "*":
            resp.headers.setdefault("Access-Control-Allow-Origin", "*")
            resp.headers.setdefault(
                "Access-Control-Allow-Methods",
                "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
            )
            resp.headers.setdefault(
                "Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With"
            )
            resp.headers.setdefault("Vary", "Origin")
            return resp

        # strict allow-list mode
        literal = {
            o for o in allowed if isinstance(o, str) and "*" not in o and not o.startswith("regex:")
        }
        patterns = []
        for item in allowed:
            if isinstance(item, str) and item.startswith("regex:"):
                try:
                    patterns.append(re.compile(item.split(":", 1)[1]))
                except re.error:
                    continue
            elif isinstance(item, str) and "*" in item:
                pattern = "^" + re.escape(item).replace("\\*", ".*") + "$"
                patterns.append(re.compile(pattern))
            elif hasattr(item, "match"):
                patterns.append(item)

        if origin and (origin in literal or any(p.match(origin) for p in patterns)):
            resp.headers.setdefault("Access-Control-Allow-Origin", origin)
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

    @app.route("/api/<path:_subpath>", methods=["OPTIONS"])
    def _cors_preflight(_subpath):
        return ("", 204)

    # --- Health ---
    @app.get("/api/healthz")
    def healthz():
        return jsonify(status="ok", time=datetime.now(timezone.utc).isoformat()), 200

    app.add_url_rule("/ping", view_func=healthz, methods=["GET"])
        
    # --- Azure Speech: token + diagnostics ---
    import time, requests
    from flask import current_app, request as flask_request

    def _azure_env():
        key = (
            os.getenv("AZURE_SPEECH_KEY")
            or os.getenv("AZURE_TTS_KEY")
            or os.getenv("SPEECH_KEY")
            or os.getenv("AZURE_COG_KEY")
            or os.getenv("COGNITIVE_SERVICES_KEY")
        )
        region = (
            os.getenv("AZURE_SPEECH_REGION")
            or os.getenv("SPEECH_REGION")
            or os.getenv("AZURE_REGION")
            or os.getenv("REGION")
        )
        endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")  # optional
        return key, region, endpoint

    def _azure_issue_token():
        key, region, endpoint = _azure_env()
        if not key or not region:
            raise RuntimeError("missing_key_or_region")
        token_url = (
            (endpoint.rstrip("/") + "/sts/v1.0/issuetoken")
            if endpoint else f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
        )
        r = requests.post(token_url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=10)
        r.raise_for_status()
        return r.text.strip(), region, int(time.time()) + 540  # ~9 minutes

    @app.get("/api/azure/diag")
    def azure_diag():
        key, region, endpoint = _azure_env()
        ok = bool(key and region)
        resp = {"ok": ok, "has_key": bool(key), "region": region or None, "endpoint": endpoint or None}
        # Attempt a real token call when query ?probe=1
        if flask_request.args.get("probe") == "1" and ok:
            try:
                _tok, _reg, _exp = _azure_issue_token()
                resp["probe"] = {"ok": True}
            except Exception as e:
                current_app.logger.error("Azure diag probe failed: %s", e)
                resp["probe"] = {"ok": False, "error": "token_request_failed"}
        return jsonify(resp), (200 if ok else 500)

    @app.get("/api/azure/token")
    @app.get("/api/token/azure")
    def azure_token():
        try:
            token, region, expires_at = _azure_issue_token()
            current_app.logger.info("Issued Azure token (region=%s)", region)
            # Return the minimal fields the frontend typically needs.
            return jsonify({"token": token, "region": region, "expires_at": expires_at})
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", 500)
            current_app.logger.error("Azure token HTTP error: %s", e)
            return jsonify({"ok": False, "error": "azure_token_http_error", "status": status}), 502
        except Exception as e:
            current_app.logger.error("Azure token error: %s", e)
            return jsonify({"ok": False, "error": "azure_token_error"}), 500

    # --- Blueprints ---
    from .auth import auth_bp
    from .api import api_bp
    from .admin_debug import admin_debug
    from .debug_trace import debug_api

    app.register_blueprint(debug_api, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_debug)

    try:
        from .sets_api import sets_api as sets_bp
        app.register_blueprint(sets_bp, url_prefix="/api")
    except Exception:
        pass

    try:
        from .routes import routes_bp
        app.register_blueprint(routes_bp)  # usually no prefix
    except Exception:
        pass

    # Optional local-only init
    if os.getenv("AUTO_INIT_DB", "0").lower() in ("1", "true", "yes"):
        with app.app_context():
            import app.models as _all_models  # ensure models loaded
            db.create_all()

    @app.errorhandler(Exception)
    def on_error(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Unhandled error: %s", e)
        return jsonify({"ok": False, "error": "internal_error"}), 500

    return app
