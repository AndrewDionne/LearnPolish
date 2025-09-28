#!/usr/bin/env python3
# rebuild_all.py  — run from repo root, e.g. `python rebuild_all.py`

import json
from pathlib import Path

# Ensure we can import the app package when run from repo root
import sys
sys.path.append(str(Path(__file__).parent))

# Import helpers
from app.sets_utils import SETS_DIR, regenerate_set_pages
from app.listening import create_listening_set

try:
    # Optional: if you have a catalog/index builder
    from app.utils import build_all_mode_indexes
except Exception:
    def build_all_mode_indexes():
        print("⚠️ build_all_mode_indexes() not available, skipping catalog rebuild.")

ALLOW = {"learn", "speak", "read", "listen"}

def infer_modes(j) -> list[str]:
    """Match server logic; accept both dict (new) and list (legacy)."""
    # Legacy top-level array → default to flashcards (learn+speak)
    if isinstance(j, list):
        # If any item has audio/audio_url, treat as listening
        if any(isinstance(c, dict) and ("audio" in c or "audio_url" in c) for c in j):
            return ["listen"]
        return ["learn", "speak"]

    # Dict shape
    meta = (j.get("meta") or {})
    modes = j.get("modes") or meta.get("modes") or []
    if isinstance(modes, list) and modes:
        s = {str(m).lower() for m in modes if str(m).lower() in ALLOW}
        if "learn" in s or "speak" in s:
            s.update({"learn", "speak"})
        return [m for m in ["learn", "speak", "read", "listen"] if m in s]

    # Structural inference (legacy keys)
    if isinstance(j.get("passages"), list):
        return ["read"]
    if any(isinstance(c, dict) and ("audio" in c or "audio_url" in c) for c in (j.get("cards") or [])):
        return ["listen"]

    return ["learn", "speak"]

def items_for_listening(j):
    """Pick the item list used to author listening dialogues."""
    if isinstance(j, list):
        return j
    return j.get("data") or j.get("cards") or j.get("items") or []

def rebuild_one_set(json_path: Path):
    """Rebuild one set. Returns (name, modes, warnings:list[str])."""
    warns = []
    try:
        j = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return (json_path.stem, [], [f"read_json_failed: {e}"])

    # Set name
    if isinstance(j, dict):
        name = j.get("name") or json_path.stem
    else:
        name = json_path.stem

    # Always regenerate HTML/audio for non-listening modes
    try:
        regenerate_set_pages(name)
    except Exception as e:
        warns.append(f"regenerate_set_pages_failed: {e}")

    # Listening (only if set actually supports it)
    try:
        modes = infer_modes(j)
        if "listen" in modes:
            items = items_for_listening(j)
            create_listening_set(name, items)
    except Exception as e:
        warns.append(f"listening_build_failed: {e}")
        modes = infer_modes(j)  # best effort

    return (name, infer_modes(j), warns)

def main():
    if not SETS_DIR.exists():
        print("No SETS_DIR:", SETS_DIR)
        return

    total = 0
    listening = 0
    had_warns = 0

    print(f"🔁 Rebuilding all sets from {SETS_DIR} …")
    for p in sorted(SETS_DIR.glob("*.json")):
        name, modes, warns = rebuild_one_set(p)
        total += 1
        if "listen" in (modes or []):
            listening += 1
        if warns:
            had_warns += 1
            print(f"⚠️  {name}: " + " | ".join(warns))
        else:
            print(f"✅  {name}: {', '.join(modes) if modes else 'unknown'}")

    # Rebuild top-level catalogs (if available)
    try:
        build_all_mode_indexes()
    except Exception as e:
        print(f"⚠️ catalog rebuild failed → {e}")

    print(f"\n🎉 Done. Rebuilt {total} sets ({listening} with listening). "
          f"{'Warnings on some sets.' if had_warns else 'No warnings.'}")

if __name__ == "__main__":
    main()
