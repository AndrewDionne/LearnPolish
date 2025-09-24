import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

# --- Constants ---
SETS_DIR = Path("docs/sets")
STATIC_DIR = Path("docs/static")
SETS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# System cue files you already created
SYSTEM_CUE_NAMES = ["repeat_after_me", "good", "try_again"]

def _ensure_system_audio() -> None:
    """
    Ensure the system cue directory exists and warn if any expected files are missing.
    We do NOT auto-generate these (you already have custom versions).
    """
    sys_dir = STATIC_DIR / "system_audio"
    sys_dir.mkdir(parents=True, exist_ok=True)
    missing = [n for n in SYSTEM_CUE_NAMES if not (sys_dir / f"{n}.mp3").exists()]
    if missing:
        print(f"ℹ️ System audio missing (won't auto-generate): {', '.join(missing)}")


# ---------------- Utilities ----------------

def sanitize_filename(text: str) -> str:
    """Make a safe, ASCII-only filename for storage (used for set_name -> file name)."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_text)
    return safe.strip("_")


def _read_json_file(p: Path) -> Optional[Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _infer_type_from_item(obj: dict) -> str:
    if not isinstance(obj, dict):
        return "unknown"
    keys = set(obj.keys())
    if {"phrase", "pronunciation", "meaning"}.issubset(keys):
        return "flashcards"
    if {"title", "polish", "english"}.issubset(keys):
        return "reading"
    return "unknown"


def _set_file_path(set_name: str) -> Path:
    """Canonical file path for a set."""
    return SETS_DIR / f"{set_name}.json"


# ------------- Metadata / Listing -------------

def get_set_metadata(set_name: str) -> Dict[str, Any]:
    """
    Return metadata for a single set:
      { "name", "count", "type", "created_by" }
    Note: created_by isn't persisted in the file; default to "system" here.
    """
    p = _set_file_path(set_name)
    data = _read_json_file(p)
    if isinstance(data, list) and data:
        set_type = _infer_type_from_item(data[0])
        count = len(data)
    elif isinstance(data, list):
        set_type = "unknown"
        count = 0
    else:
        set_type = "unknown"
        count = "?"
    return {
        "name": set_name,
        "count": count,
        "type": set_type,
        "created_by": "system",  # sets_api can override to "me" for UI
    }


def list_global_sets() -> List[Dict[str, Any]]:
    """List all .json files in docs/sets as 'global' sets."""
    out: List[Dict[str, Any]] = []
    for p in sorted(SETS_DIR.glob("*.json")):
        out.append(get_set_metadata(p.stem))
    return out


# ---------------- Data I/O ----------------

def load_set_data(set_name: str) -> List[Dict[str, Any]]:
    """Load the array of items for a set."""
    p = _set_file_path(set_name)
    data = _read_json_file(p)
    if not isinstance(data, list):
        raise FileNotFoundError(f"Set file not found or invalid: {p}")
    return data


def save_set_data(set_name: str, data: List[Dict[str, Any]]) -> Path:
    """Save the array of items to docs/sets/<set_name>.json."""
    p = _set_file_path(set_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def count_cards(set_name: str) -> int | str:
    """Count items in the set. Returns '?' if invalid."""
    p = _set_file_path(set_name)
    data = _read_json_file(p)
    if isinstance(data, list):
        return len(data)
    return "?"


# ------------- Filtering (by implied mode) -------------

def load_sets_for_mode(mode: str) -> List[Dict[str, Any]]:
    """
    Return sets whose implied modes (via type) include the requested mode.
    Special-cases:
      - mode == 'all' -> return all sets
    """
    from .modes import modes_for_type  # avoid circular import
    all_sets = list_global_sets()
    if mode == "all":
        return all_sets
    out: List[Dict[str, Any]] = []
    for meta in all_sets:
        implied = set(modes_for_type(meta.get("type", "unknown")))
        if mode in implied:
            out.append(meta)
    return out


def _ensure_flashcard_audio(set_name: str, data: List[Dict[str, Any]]) -> None:
    try:
        from gtts import gTTS
    except Exception as e:
        print(f"⚠️ gTTS not available; skipping audio generation: {e}")
        return

    audio_dir = STATIC_DIR / set_name / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    seen = set()  # avoid regenerating identical phrases in the same set
    for i, entry in enumerate(data):
        phrase = (entry or {}).get("phrase", "").strip()
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)

        filename = f"{i}_{sanitize_filename(phrase)}.mp3"
        out = audio_dir / filename
        if out.exists():
            continue
        try:
            gTTS(text=phrase, lang="pl").save(str(out))  # ← ensure str()
        except Exception as e:
            print(f"⚠️ Failed to create TTS for '{phrase}': {e}")


def _ensure_reading_audio(set_name: str, data: List[Dict[str, Any]]) -> None:
    try:
        from gtts import gTTS
    except Exception as e:
        print(f"⚠️ gTTS not available; skipping reading audio: {e}")
        return

    audio_dir = STATIC_DIR / set_name / "reading"
    audio_dir.mkdir(parents=True, exist_ok=True)

    seen = set()
    for i, item in enumerate(data):
        polish = (item or {}).get("polish", "").strip()
        if not polish or polish in seen:
            continue
        seen.add(polish)

        out = audio_dir / f"{i}.mp3"
        if out.exists():
            continue
        try:
            gTTS(text=polish, lang="pl").save(str(out))  # ← ensure str()
        except Exception as e:
            print(f"⚠️ Failed to create reading TTS for idx {i}: {e}")

# ---------------- Page generation ----------------

def regenerate_set_pages(set_name: str) -> bool:
    """
    Regenerate HTML for a given set for the modes implied by its type.
    Generators are expected in MODE_GENERATORS:
      { "flashcards": fn, "practice": fn, "reading": fn, ... }
    where fn(set_name, data) -> Path/str of generated HTML
    """
    from .modes import MODE_GENERATORS, modes_for_type  # avoid circular import
    data = load_set_data(set_name)
    set_type = _infer_type_from_item(data[0]) if data else "unknown"
    modes = modes_for_type(set_type)

     # Generators expect audio files to already exist (so buttons work). Ensure first.
    if "flashcards" in modes or "practice" in modes:
        _ensure_flashcard_audio(set_name, data)
    if "reading" in modes:
        _ensure_reading_audio(set_name, data)

    # Ensure cue files dir exists and warn if any are missing
    _ensure_system_audio()  

    for mode in modes:
        generator = MODE_GENERATORS.get(mode)
        if generator:
            html_path = generator(set_name, data)
            print(f"🔄 Regenerated {mode} page for set '{set_name}': {html_path}")
    return True


# ---------------- High-level ops ----------------

def create_set(set_type: str, set_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a new set file and generate its pages based on set_type.
    Also generates any required audio assets.
    Returns metadata dict.
    """
    safe_name = sanitize_filename(set_name)
    if not safe_name:
        raise ValueError("Invalid set name")

    # Basic validation by set_type
    if set_type == "flashcards":
        for entry in data:
            if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
                raise ValueError("Flashcards require keys: phrase, pronunciation, meaning")
    elif set_type == "reading":
        for item in data:
            if "polish" not in item:
                raise ValueError("Reading requires key: polish (english/title optional)")

    # Persist content
    save_set_data(safe_name, data)

    # Generate assets + pages
    regenerate_set_pages(safe_name)
    

    # Metadata (created_by is set by sets_api when returning to the client)
    meta = get_set_metadata(safe_name)
    meta["type"] = set_type or meta["type"]
    return meta


def delete_set_file(set_name: str) -> bool:
    """
    Delete the set and its generated artifacts:
      - docs/sets/<name>.json
      - docs/static/<name>/**        (audio, reading TTS)
      - docs/<mode>/<name>/          (all generated pages)
    Returns True if the JSON file existed and was removed; False otherwise.
    """
    safe_name = sanitize_filename(set_name)
    existed = False

    # Remove JSON
    p = _set_file_path(safe_name)
    if p.exists():
        p.unlink()
        existed = True

    # Remove static assets
    static_root = STATIC_DIR / safe_name
    if static_root.exists():
        for child in static_root.rglob("*"):
            try:
                child.unlink()
            except IsADirectoryError:
                pass
        # remove empty dirs bottom-up
        for d in sorted(static_root.glob("**/*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except OSError:
                    pass
        try:
            static_root.rmdir()
        except OSError:
            pass

    # Remove generated pages for all known modes
    docs_root = Path("docs")
    for mode in MODE_GENERATORS.keys():
        target = docs_root / mode / safe_name
        if target.exists():
            for child in target.rglob("*"):
                try:
                    child.unlink()
                except IsADirectoryError:
                    pass
            for d in sorted(target.glob("**/*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except OSError:
                        pass
            try:
                target.rmdir()
            except OSError:
                pass

    return existed
