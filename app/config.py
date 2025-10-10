# config.py
import os, secrets
from urllib.parse import urlparse

# ---------- helpers ----------
def _origin(url: str) -> str | None:
    """Return scheme://host[:port] or None if invalid."""
    try:
        p = urlparse(url or "")
        if not p.scheme or not p.hostname:
            return None
        port = f":{p.port}" if p.port else ""
        return f"{p.scheme}://{p.hostname}{port}"
    except Exception:
        return None

# ---------- environment detection ----------
APP_ENV = os.getenv("APP_ENV", "development")  # development | staging | production
IN_RENDER = bool(os.getenv("RENDER"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") if IN_RENDER else ""

# ---------- base URLs ----------
# Your published GH Pages site (public)
GITHUB_PAGES_SITE = "https://andrewdionne.github.io/LearnPolish"
GITHUB_PAGES_ORIGIN = "https://andrewdionne.github.io"

if IN_RENDER:
    # API lives on Render; frontend on GitHub Pages by default (overridable via env)
    API_BASE_URL = RENDER_URL or os.getenv("API_BASE_URL", "https://path-to-polish.onrender.com")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", GITHUB_PAGES_SITE)
elif os.getenv("GITHUB_ACTIONS"):
    API_BASE_URL = os.getenv("API_BASE_URL", "")
    FRONTEND_BASE_URL = GITHUB_PAGES_SITE
else:
    # Local dev: API + static are served by Flask on the same origin
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5000")

# Origins for CORS (no paths)
FRONTEND_ORIGIN = _origin(FRONTEND_BASE_URL) or "http://localhost:5000"
API_ORIGIN = _origin(API_BASE_URL) or "http://localhost:5000"

# ---------- CORS ----------
# Base allow-list (you can extend with env below)
DEFAULT_CORS = [
    FRONTEND_ORIGIN,
    API_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    GITHUB_PAGES_ORIGIN,
    "https://polishpath.com",
    "https://www.polishpath.com",
]

def _merge_origins(*lists):
    """Normalize to origins, drop blanks/dupes, preserve order."""
    out = []
    for lst in lists:
        for o in lst:
            if not o:
                continue
            v = _origin(o.strip())
            if v and v not in out:
                out.append(v)
    return out

# Optional: comma-separated list in env
EXTRA_CORS = [s.strip() for s in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if s.strip()]

# Final allow-list used by the app / CORS setup
CORS_ALLOWED_ORIGINS = _merge_origins(DEFAULT_CORS, EXTRA_CORS)

# Back-compat: if CORS_ORIGINS env is provided, use it literally
_ENV_CORS = [s.strip() for s in os.getenv("CORS_ORIGINS", "").split(",") if s.strip()]
CORS_ORIGINS = _ENV_CORS or CORS_ALLOWED_ORIGINS or ["*"]  # last-resort wide-open for dev

# ---------- admin ----------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

# ---------- azure (support both legacy and current var names) ----------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_REGION")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# ---------- Cloudflare R2 ----------
R2_BUCKET = os.getenv("R2_BUCKET", "")
R2_S3_ENDPOINT = os.getenv("R2_S3_ENDPOINT", "")
R2_CDN_BASE = os.getenv("R2_CDN_BASE", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")

# ---------- email ----------
# Provider can be: "ses_smtp", "gmail", or "console"
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "ses_smtp")

# SES over SMTP (recommended in production)
SES_REGION = os.getenv("SES_REGION", "eu-north-1")
SES_SMTP_USER = os.getenv("SES_SMTP_USER", "")
SES_SMTP_PASS = os.getenv("SES_SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@polishpath.com")
FROM_NAME  = os.getenv("FROM_NAME",  "Path to POLISH")

# Gmail (optional legacy)
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")

# ---------- legacy/optional ----------
MODES = ["flashcards", "practice", "reading", "listening", "test"]

# ---------- canonical Config used by Flask ----------
class Config:
    # Secrets
    SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-" + secrets.token_urlsafe(32))
    JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY

    # Base URLs
    FRONTEND_BASE_URL = FRONTEND_BASE_URL
    APP_BASE_URL = API_BASE_URL  # some code reads APP_BASE_URL; map to API base

    # CORS (read by app/__init__.py when initializing Flask-CORS)
    CORS_ORIGINS = CORS_ORIGINS
    CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS

    # SQLAlchemy/general
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True

    # Email (for reference/logging; emailer.py reads env directly)
    EMAIL_PROVIDER = EMAIL_PROVIDER
    SES_REGION = SES_REGION
    SES_SMTP_USER = SES_SMTP_USER
    SES_SMTP_PASS = SES_SMTP_PASS
    FROM_EMAIL = FROM_EMAIL
    FROM_NAME  = FROM_NAME
    GMAIL_USER = GMAIL_USER
    GMAIL_APP_PASSWORD = GMAIL_APP_PASSWORD

    # Azure
    AZURE_OPENAI_API_KEY = AZURE_OPENAI_API_KEY
    AZURE_OPENAI_ENDPOINT = AZURE_OPENAI_ENDPOINT
    AZURE_SPEECH_KEY = AZURE_SPEECH_KEY
    AZURE_SPEECH_REGION = AZURE_SPEECH_REGION
    AZURE_STORAGE_CONNECTION_STRING = AZURE_STORAGE_CONNECTION_STRING

    # Cloudflare R2
    R2_BUCKET = R2_BUCKET
    R2_S3_ENDPOINT = R2_S3_ENDPOINT
    R2_CDN_BASE = R2_CDN_BASE
    R2_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY

