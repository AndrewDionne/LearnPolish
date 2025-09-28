#!/usr/bin/env python3
# rebuild_all.py  (run from the repo root)

import argparse
import json
import sys
from pathlib import Path

# --- make sure we can import "app.*" when running from root ---
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Project helpers
from app.sets_utils import SETS_DIR, regenerate_set_pages
from app.listening import create_listening_set

# Optional: global catalog builder (docs/<mode>/index.html)
try:
    from app.utils import build_all_mode_indexes
except Exception:
    def build_all_mode_indexes():
        print("⚠️ build_all_mode_indexes() not available, skipping catalog rebuild.")

ALLOW = {"learn", "speak", "read", "listen"}

def infer_modes(j: dict) -> list[str]:
    """Mirror server inference; prefer explicit modes and enforce learn<->speak pairing."""
    meta = j.get("meta") or {}
    modes = j.get("modes") or meta.get("modes") or []
    if isinstance(modes, list) and modes:
        s = {str(m).lower() for m in modes if isinstance(m, str) and str(m).lower() in ALLOW}
        if "learn" in s or "speak" in s:
            s.update({"learn", "speak"})
        if s:
            return [m for m in ["learn", "speak", "read", "listen"] if m in s]

    # Legacy structural inference
    if isinstance(j.get("passages"), list):
        return ["read"]
    cards = j.get("data") or j.get("cards") or j.get("items") or []
    if any(isinstance(c, dict) and ("audio" in c or "audio_url" in c) for c in cards):
        return ["listen"]
    return ["learn", "speak"]

def items_for_listening(j: dict):
    """Prefer canonical 'data', fallback to older keys."""
    return j.get("data") or j.get("cards") or j.get("items") or []

def rebuild_one_set(json_path: Path) -> tuple[str, list[str], list[str]]:
    """Rebuild a single set; return (name, modes, warnings)."""
    warnings = []
    try:
        j = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return (json_path.stem, [], [f"read_json_failed: {e}"])

    name = j.get("name") or json_path.stem
    modes = infer_modes(j)

    # learn/speak/read
    try:
        regenerate_set_pages(name)
    except Exception as e:
        warnings.append(f"regenerate_failed: {e}")

    # listening
    try:
        if "listen" in modes:
            items = items_for_listening(j)
            create_listening_set(name, items)
    except Exception as e:
        warnings.append(f"listening_generate_failed: {e}")

    return (name, modes, warnings)

def ensure_nojekyll():
    docs = Path("docs")
    docs.mkdir(parents=True, exist_ok=True)
    (docs / ".nojekyll").write_text("", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Rebuild all static pages for all sets.")
    parser.add_argument("--only", metavar="SET_NAME", help="Rebuild a single set by name (without .json)")
    parser.add_argument("--no-catalog", action="store_true", help="Skip rebuilding docs/<mode>/index.html catalogs")
    args = parser.parse_args()

    if not SETS_DIR.exists():
        print("No SETS_DIR:", SETS_DIR)
        return

    ensure_nojekyll()

    total = 0
    listening_cnt = 0
    had_errors = False

    targets = [SETS_DIR / f"{args.only}.json"] if args.only else sorted(SETS_DIR.glob("*.json"))

    for p in targets:
        if not p.exists():
            print(f"⚠️ Missing: {p}")
            had_errors = True
            continue

        name, modes, warns = rebuild_one_set(p)
        total += 1
        if "listen" in modes:
            listening_cnt += 1

        tag = ",".join(modes) if modes else "—"
        if warns:
            print(f"• {name:>20}  [{tag}]  ⚠️ " + " | ".join(warns))
            had_errors = True
        else:
            print(f"• {name:>20}  [{tag}]  ✓")

    if not args.no_catalog:
        try:
            build_all_mode_indexes()
            print("✓ catalogs rebuilt (docs/<mode>/index.html)")
        except Exception as e:
            print(f"⚠️ catalog rebuild failed → {e}")
            had_errors = True

    print(f"✅ Rebuilt {total} set(s) ({listening_cnt} with listening).")
    if had_errors:
        print("Done with warnings. See messages above.")

if __name__ == "__main__":
    main()
