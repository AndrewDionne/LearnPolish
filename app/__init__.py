# app/__init__.py
from __future__ import annotations
import os
from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

from .models import db

def _as_list(x):
    if not x:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]

def create_app():
    app = Flask(__name__)
    # Load config object
    app.config.from_object("config.Config")

    # Respect Render’s proxy headers so url_for / scheme are correct
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # --- CORS ---
    # Accept frontends from GitHub Pages + any configured origins
    # You can control the list with env var CORS_ORIGINS or CORS_ALLOWED_ORIGINS (comma-separated).
    # We support both, using values computed in config.py if present.
    try:
        # If you added CORS_ORIGINS to Config, use it; otherwise import from module-level in config.py
        origins = _as_list(app.config.get("CORS_ORIGINS"))
        if not origins:
            from config import CORS_ORIGINS as _cfg_origins  # type: ignore
            origins = _as_list(_cfg_origins)
    except Exception:
        origins = []

    if not origins:
        # Last-resort dev default (fine locally; avoid in prod)
        origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5000",
                   "https://andrewdionne.github.io"]

    cors_resources = {
        r"/api/*":  {"origins": origins},
        r"/auth/*": {"origins": origins},
    }
    CORS(
        app,
        resources=cors_resources,
        supports_credentials=True,  # harmless even if you use Authorization header
        expose_headers=["Content-Type", "Authorization"],
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    # --- DB ---
    db.init_app(app)

    @app.teardown_appcontext
    def shutdown_session(_exc=None):
        # Ensure pooled connections are returned and sessions are cleared
        try:
            db.session.remove()
        except Exception:
            pass

    # --- Blueprints ---
    # API endpoints
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # Auth endpoints (login/register/refresh etc.) if you have them
    try:
        from .auth import auth_bp  # make sure your auth blueprint is named auth_bp
        app.register_blueprint(auth_bp, url_prefix="/auth")
    except Exception:
        # If you don't have an auth blueprint, this is fine.
        pass

    # Simple root and healthz (root is nice to verify the service is up)
    @app.get("/healthz")
    def root_health():
        return jsonify({"ok": True})

    @app.get("/")
    def index():
        return jsonify({
            "ok": True,
            "service": "Path to POLISH API",
            "docs": "See /api/healthz and /auth/*",
        })

    # --- JSON error handlers (so the frontend never sees HTML error pages) ---
    def _json_err(status: int, message: str):
        return jsonify({"error": message, "status": status, "path": request.path}), status

    @app.errorhandler(400)
    def _bad_request(e): return _json_err(400, "bad_request")

    @app.errorhandler(401)
    def _unauth(e): return _json_err(401, "unauthorized")

    @app.errorhandler(403)
    def _forbidden(e): return _json_err(403, "forbidden")

    @app.errorhandler(404)
    def _not_found(e): return _json_err(404, "not_found")

    @app.errorhandler(405)
    def _method_not_allowed(e): return _json_err(405, "method_not_allowed")

    @app.errorhandler(500)
    def _server_err(e): return _json_err(500, "server_error")

    return app


# For gunicorn: `gunicorn "app.__init__:app"`
# or Render’s default: `app` must be a module-global
app = create_app()
