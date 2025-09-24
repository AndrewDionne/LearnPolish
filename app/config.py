# config.py
import os

# ---- App env ----
APP_ENV = os.getenv("APP_ENV", "development")  # development | staging | production

# ---- Admin ----
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

# ---- Security ----
# Set this in the environment in prod (Render dashboard)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")

# ---- Hostnames / Base URLs ----
# Backend (Flask API) on Render
RENDER = os.getenv("RENDER")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://flashcards-5c95.onrender.com") if RENDER else ""

# Frontend (static site) on GitHub Pages
# Use the *published site*, not the repo URL:
GITHUB_PAGES_SITE = "https://andrewdionne.github.io/LearnPolish"

if RENDER:
    # Production: API lives on Render, frontend on GitHub Pages
    API_BASE_URL = RENDER_URL
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", GITHUB_PAGES_SITE)
elif os.getenv("GITHUB_ACTIONS"):
    # GH Actions build context (rarely used at runtime)
    API_BASE_URL = ""
    FRONTEND_BASE_URL = GITHUB_PAGES_SITE
else:
    # Local development
    API_BASE_URL = "http://localhost:5000"
    # Your static site is served under /docs locally
    FRONTEND_BASE_URL = "http://localhost:5000/docs"

# ---- Optional: CORS ----
# You can add more comma-separated origins via env
CORS_ALLOWED_ORIGINS = [
    FRONTEND_BASE_URL,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
] + [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# ---- Legacy/optional constants ----
# If you still reference MODES in code, keep it; otherwise you can remove it.
MODES = ["flashcards", "practice", "reading", "listening", "test"]

# ---- Azure Speech (no defaults) ----
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_REGION")
