# app/create_set_modes.py
from __future__ import annotations
import json
from pathlib import Path

SETS_DIR = Path("docs/sets")
OUTFILE  = Path("docs/set_modes.json")

# Heuristics to infer modes from the first item in a set JSON array.
# Tweak these rules if your schemas evolve.
def infer_modes_from_item(item: dict) -> list[str]:
    if not isinstance(item, dict):
        return ["flashcards", "practice"]  # generic default for string/primitive lists

    keys = {k.lower() for k in item.keys()}

    # Vocabulary (flashcards): common schemas
    has_flash = (
        {"phrase", "meaning"}.issubset(keys) or
        {"front", "back"}.issubset(keys) or
        {"pl", "en"}.issubset(keys) or
        {"word", "meaning"}.issubset(keys) or
        {"term", "definition"}.issubset(keys) or
        {"phrase","pronunciation","meaning"}.issubset(keys)
    )

    # Read(ing): typical reading schema
    has_read = (
        {"title", "polish", "english"}.issubset(keys) or
        ({"polish", "english"}.issubset(keys) and "title" in keys)
    )

    # Listen(ing): any audio-ish field
    audio_keys = {"audio", "mp3", "wav", "sound", "file", "url"}
    has_listen = any(k in keys for k in audio_keys)

    modes = []
    if has_flash:
        modes.extend(["flashcards", "practice"])  # practice (Speak) usually piggybacks on vocab
    if has_read:
        modes.append("reading")
    if has_listen:
        modes.append("listening")

    # If nothing matched, be permissive (so the UI isn’t too restrictive)
    if not modes:
        modes = ["flashcards", "practice"]  # safe default

    # De-dupe while preserving order
    seen, out = set(), []
    for m in modes:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out

def infer_modes_for_set(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            first = data[0]
            return infer_modes_from_item(first if isinstance(first, dict) else {})
        elif isinstance(data, list) and not data:
            # Empty list: assume at least vocab/practice
            return ["flashcards", "practice"]
        else:
            return ["flashcards", "practice"]
    except Exception:
        # Malformed JSON? Don’t block the whole build; fall back to permissive
        return ["flashcards", "practice"]

def main():
    if not SETS_DIR.exists():
        print(f"⚠️ No {SETS_DIR} folder found; writing empty map.")
        OUTFILE.write_text("{}", encoding="utf-8")
        return

    mapping = {}
    for p in sorted(SETS_DIR.glob("*.json")):
        name = p.stem
        mapping[name] = infer_modes_for_set(p)

    # Pretty-print with stable keys
    OUTFILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"✅ Wrote {OUTFILE} with {len(mapping)} collections.")

if __name__ == "__main__":
    main()
