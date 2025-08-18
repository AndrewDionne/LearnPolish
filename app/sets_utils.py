import json
from pathlib import Path
from .config import MODES
import re
import unicodedata

# === Constants ===
SETS_DIR = Path("docs/sets")
MODES_FILE = Path("docs/set_modes.json")

# All available learning modes
MODES = ["flashcards", "practice", "reading", "listening", "test"]

def sanitize_filename(text: str) -> str:
    """Make a safe, ASCII-only filename for storage."""
    # Normalize Unicode → remove diacritics (e.g. ę → e, ł → l)
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Replace non-alphanumeric with underscores
    safe = re.sub(r'[^a-zA-Z0-9]+', "_", ascii_text)
    return safe.strip("_")

# === Mode Config Handling ===
def load_set_modes() -> dict:
    """Load mode assignments for all sets."""
    if MODES_FILE.exists():
        with open(MODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_set_modes(modes: dict):
    """Save mode assignments for all sets."""
    with open(MODES_FILE, "w", encoding="utf-8") as f:
        json.dump(modes, f, ensure_ascii=False, indent=2)

# === Card Counting ===
def count_cards(set_name: str) -> int:
    """Count the number of cards in a set."""
    data_file = SETS_DIR / set_name / "data.json"
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            try:
                return len(json.load(f))
            except json.JSONDecodeError:
                return 0
    return 0

# === Set Loading ===
def get_all_sets() -> list:
    """Return list of all sets with their card counts and assigned modes."""
    modes_map = load_set_modes()
    sets = []
    for d in SETS_DIR.iterdir():
        if d.is_dir():
            name = d.name
            sets.append({
                "name": name,
                "count": count_cards(name),
                "modes": modes_map.get(name, [])
            })
    return sets

def load_sets_for_mode(mode: str) -> list:
    """Return sets that have the given mode enabled (or all sets if mode='all')."""
    all_sets = get_all_sets()
    if mode == "all":
        return all_sets
    return [s for s in all_sets if mode in s["modes"]]