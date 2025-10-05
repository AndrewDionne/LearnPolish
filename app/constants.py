# app/constants.py
from pathlib import Path

# --- Project directories (relative to repo root) ---
PAGES_DIR        = Path("docs")
SETS_DIR         = PAGES_DIR / "sets"
STATIC_DIR       = PAGES_DIR / "static"
AUDIO_DIR        = STATIC_DIR / "audio"
SET_MODES_JSON   = PAGES_DIR / "set_modes.json"

# Ensure essential dirs exist (safe to run multiple times)
for d in (SETS_DIR, STATIC_DIR, AUDIO_DIR):
    d.mkdir(parents=True, exist_ok=True)

# System audio cue names (used by generators / UI beeps)
SYSTEM_CUE_NAMES = ["repeat_after_me", "good", "try_again"]

# NOTE:
# - Keep generator registries in app/modes.py (single source of truth).
# - Do NOT import generators here; constants should remain import-safe everywhere.
