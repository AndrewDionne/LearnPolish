# config.py
import os, secrets
from urllib.parse import urlparse

# Comma-separated list; e.g. "http://localhost:5000,https://andrewdionne.github.io"
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
] or ["*"]  # default wide-open for dev

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
    API_BASE_URL = RENDER_URL or os.getenv("API_BASE_URL", "https://flashcards-5c95.onrender.com")
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

# Allow-list; extend with CORS_ALLOWED_ORIGINS env (comma-separated)
CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    API_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    GITHUB_PAGES_ORIGIN,
] + [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if _origin(o.strip())]

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
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail")
GMAIL_USER = os.getenv("GMAIL_USER")
# store app password without spaces; some UIs display with spaces
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

    # SQLAlchemy/general
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True

    # Email
    EMAIL_PROVIDER = EMAIL_PROVIDER
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
