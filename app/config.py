import os

# Detect environment (local dev, Render, GitHub Pages)
if os.getenv("RENDER"):
    # Running on Render
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://flashcards-5c95.onrender.com")
    GITHUB_PAGES_URL = "https://github.com/AndrewDionne/LearnPolish"
elif os.getenv("GITHUB_ACTIONS"):
    # Building for GitHub Pages
    RENDER_URL = ""
    GITHUB_PAGES_URL = "https://github.com/AndrewDionne/LearnPolish"
else:
    # Local development
    RENDER_URL = "http://localhost:5000"
    GITHUB_PAGES_URL = "http://localhost:5000/docs"

# Global list of learning modes
MODES = ["flashcards", "practice", "reading", "listening", "test"]

# ✅ Read Azure Speech env vars (no defaults; keep secrets out of code)
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_REGION")
