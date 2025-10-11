# config.py
import os, secrets
from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qsl, urlencode

# ---------- helpers ----------
def _origin(url: str) -> str | None:
    try:
        p = urlparse(url or "")
        if not p.scheme or not p.hostname:
            return None
        port = f":{p.port}" if p.port else ""
        return f"{p.scheme}://{p.hostname}{port}"
    except Exception:
        return None

def _add_query_params(url: str, extra: dict[str, str]) -> str:
    if not url:
        return url
    p = urlsplit(url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    for k, v in extra.items():
        q.setdefault(k, v)
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))

def _canon_db_url(url: str) -> str:
    """
    Render gives postgres://; prefer postgresql:// and append SSL & keepalives.
    Avoid forcing +psycopg unless the driver is guaranteed installed.
    """
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    url = _add_query_params(
        url,
        {
            "sslmode": "require",
            "connect_timeout": os.getenv("DB_CONNECT_TIMEOUT", "10"),
            "keepalives": "1",
            "keepalives_idle": "30",
            "keepalives_interval": "10",
            "keepalives_count": "3",
        },
    )
    return url

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")

# ---------- environment detection ----------
APP_ENV   = os.getenv("APP_ENV", "development")  # development | staging | production
IN_RENDER = bool(os.getenv("RENDER"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") if IN_RENDER else ""

# ---------- base URLs ----------
GITHUB_PAGES_SITE   = "https://andrewdionne.github.io/LearnPolish"
GITHUB_PAGES_ORIGIN = "https://andrewdionne.github.io"

if IN_RENDER:
    API_BASE_URL = RENDER_URL or os.getenv("API_BASE_URL", "https://path-to-polish.onrender.com")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", GITHUB_PAGES_SITE)
elif os.getenv("GITHUB_ACTIONS"):
    API_BASE_URL = os.getenv("API_BASE_URL", "")
    FRONTEND_BASE_URL = GITHUB_PAGES_SITE
else:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5000")

FRONTEND_ORIGIN = _origin(FRONTEND_BASE_URL) or "http://localhost:5000"
API_ORIGIN      = _origin(API_BASE_URL)      or "http://localhost:5000"

# ---------- CORS ----------
DEFAULT_CORS = [
    FRONTEND_ORIGIN,
    API_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    GITHUB_PAGES_ORIGIN,       # exact origin; wildcard subdomains won't match
    "https://polishpath.com",
    "https://www.polishpath.com",
]
def _merge_origins(*lists):
    out = []
    for lst in lists:
        for o in lst or []:
            v = _origin(o.strip()) if o else None
            if v and v not in out:
                out.append(v)
    return out

EXTRA_CORS = [s.strip() for s in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if s.strip()]
CORS_ALLOWED_ORIGINS = _merge_origins(DEFAULT_CORS, EXTRA_CORS)
_ENV_CORS = [s.strip() for s in os.getenv("CORS_ORIGINS", "").split(",") if s.strip()]
CORS_ORIGINS = _ENV_CORS or CORS_ALLOWED_ORIGINS or ["*"]

# ---------- admin ----------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

# ---------- Azure ----------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION") or os.getenv("AZURE_REGION")
AZURE_SPEECH_ENDPOINT = os.getenv("AZURE_SPEECH_ENDPOINT")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# ---------- Cloudflare R2 ----------
R2_BUCKET = os.getenv("R2_BUCKET", "")
# Prefer R2_ENDPOINT; fall back to your existing R2_S3_ENDPOINT env var.
R2_ENDPOINT = os.getenv("R2_ENDPOINT") or os.getenv("R2_S3_ENDPOINT", "")
R2_S3_ENDPOINT = R2_ENDPOINT  # keep for older code that still reads this name
R2_CDN_BASE = os.getenv("R2_CDN_BASE", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")

# ---------- email ----------
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console")  # console | gmail | ses_smtp
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", GMAIL_USER or "no-reply@localhost")
FROM_NAME  = os.getenv("FROM_NAME", "Path to POLISH")

SES_REGION    = os.getenv("SES_REGION", "eu-north-1")
SES_SMTP_HOST = os.getenv("SES_SMTP_HOST", f"email-smtp.{SES_REGION}.amazonaws.com")
SES_SMTP_PORT = int(os.getenv("SES_SMTP_PORT", "587"))
SES_SMTP_USER = os.getenv("SES_SMTP_USER", "")
SES_SMTP_PASS = os.getenv("SES_SMTP_PASS", "")
SMTP_TIMEOUT  = int(os.getenv("SMTP_TIMEOUT", "30"))

# ---------- Git / publish ----------
DISABLE_GIT_PUSH = _env_bool("DISABLE_GIT_PUSH", False)
GIT_REMOTE = os.getenv("GIT_REMOTE", "")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "Path to Polish Bot")
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "bot@pathtopolish.app")
GH_TOKEN = os.getenv("GH_TOKEN", "")

# ---------- database ----------
DATABASE_URL = _canon_db_url(os.getenv("DATABASE_URL", ""))

# ---------- canonical Config used by Flask ----------
class Config:
    # Secrets
    SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-" + secrets.token_urlsafe(32))
    JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY

    # Base URLs
    FRONTEND_BASE_URL = FRONTEND_BASE_URL
    APP_BASE_URL = API_BASE_URL

    # SQLAlchemy/general
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True

    # DB URI + robust pool for Render Postgres over SSL
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///app.db"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,            # validate connections before use
        "pool_recycle": 280,              # recycle before many providers idle you out (~300s)
        "pool_use_lifo": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }

    # Email
    EMAIL_PROVIDER = EMAIL_PROVIDER
    GMAIL_USER = GMAIL_USER
    GMAIL_APP_PASSWORD = GMAIL_APP_PASSWORD
    FROM_EMAIL = FROM_EMAIL
    FROM_NAME = FROM_NAME
    SES_REGION = SES_REGION
    SES_SMTP_HOST = SES_SMTP_HOST
    SES_SMTP_PORT = SES_SMTP_PORT
    SES_SMTP_USER = SES_SMTP_USER
    SES_SMTP_PASS = SES_SMTP_PASS
    SMTP_TIMEOUT = SMTP_TIMEOUT

    # Azure
    AZURE_OPENAI_API_KEY = AZURE_OPENAI_API_KEY
    AZURE_OPENAI_ENDPOINT = AZURE_OPENAI_ENDPOINT
    AZURE_SPEECH_KEY = AZURE_SPEECH_KEY
    AZURE_SPEECH_REGION = AZURE_SPEECH_REGION
    AZURE_SPEECH_ENDPOINT = AZURE_SPEECH_ENDPOINT
    AZURE_STORAGE_CONNECTION_STRING = AZURE_STORAGE_CONNECTION_STRING

    # R2 / CDN
    R2_BUCKET = R2_BUCKET
    R2_ENDPOINT = R2_ENDPOINT
    R2_S3_ENDPOINT = R2_S3_ENDPOINT
    R2_CDN_BASE = R2_CDN_BASE
    R2_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY

    # Git / publish
    DISABLE_GIT_PUSH = DISABLE_GIT_PUSH
    GIT_REMOTE = GIT_REMOTE
    GIT_BRANCH = GIT_BRANCH
    GIT_AUTHOR_NAME = GIT_AUTHOR_NAME
    GIT_AUTHOR_EMAIL = GIT_AUTHOR_EMAIL
    GH_TOKEN = GH_TOKEN

    # CORS (useful if something imports these from config)
    CORS_ORIGINS = CORS_ORIGINS
    CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
