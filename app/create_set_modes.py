# app/create_set_modes.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .constants import SETS_DIR, SET_MODES_JSON

OUTFILE = SET_MODES_JSON


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for m in items:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def infer_modes_from_item(item: dict[str, Any] | Any) -> list[str]:
    """
    Heuristics to infer which modes a set supports based on a representative item.

    Rules:
      - Flashcards/Practice: vocab-ish keys (phrase/meaning, front/back, pl/en, etc.)
      - Reading: requires a title + polish (prevents collision with Listening)
      - Listening: audio-ish fields OR plain {polish, english?} without a title
                   (and NOT classic vocab shapes)
      - Fallback: ['flashcards', 'practice']
    """
    # Non-dict (e.g., list of strings): assume vocab/practice
    if not isinstance(item, dict):
        return ["flashcards", "practice"]

    keys = {k.lower() for k in item.keys()}

    # --- Flashcards (vocab) ---
    has_flash = (
        {"phrase", "meaning"}.issubset(keys)
        or {"front", "back"}.issubset(keys)
        or {"pl", "en"}.issubset(keys)
        or {"word", "meaning"}.issubset(keys)
        or {"term", "definition"}.issubset(keys)
        or {"phrase", "pronunciation", "meaning"}.issubset(keys)
    )
    looks_like_vocab = has_flash

    # --- Reading (needs a title to disambiguate from Listening) ---
    has_read = (
        ("title" in keys and "polish" in keys)
        or {"title", "polish", "english"}.issubset(keys)
    )

    # --- Listening ---
    audio_keys = {"audio", "audio_url", "mp3", "wav", "sound", "file", "url"}
    dialogish = bool({"gist", "detail"}.intersection(keys)) or bool(
        {"transcript_pl", "translation_en"}.intersection(keys)
    )

    # Plain {polish, english?} (no title) counts as Listening if not vocab
    plain_pl_en_no_title = (
        ("polish" in keys) and ("title" not in keys) and not looks_like_vocab
    )

    has_listen = (
        any(k in keys for k in audio_keys)
        or dialogish
        or plain_pl_en_no_title
    )

    modes: list[str] = []
    if has_flash:
        modes.extend(["flashcards", "practice"])
    if has_read:
        modes.append("reading")
    if has_listen:
        modes.append("listening")

    if not modes:
        modes = ["flashcards", "practice"]

    return _dedupe_keep_order(modes)


def _pick_repr_item_from_wrapper(obj: dict[str, Any]) -> dict[str, Any] | None:
    """
    Some sets could be saved in a wrapper form:
      { "meta": {...}, "cards": [...]} or {"passages": [...] } or {"items": [...] }
    Pick the first element from the first list-like field we recognize.
    """
    for key in ("cards", "passages", "items"):
        val = obj.get(key)
        if isinstance(val, list) and val:
            first = val[0]
            return first if isinstance(first, dict) else {}
    return None


def infer_modes_for_set(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)

        # Legacy/standard: list of items
        if isinstance(data, list):
            if data:
                first = data[0]
                return infer_modes_from_item(first if isinstance(first, dict) else {})
            # Empty list → safe default
            return ["flashcards", "practice"]

        # Wrapper: pick representative item
        if isinstance(data, dict):
            item = _pick_repr_item_from_wrapper(data)
            if item is not None:
                return infer_modes_from_item(item)
            # Unknown wrapper → safe default
            return ["flashcards", "practice"]

        # Unknown shape → safe default
        return ["flashcards", "practice"]

    except Exception:
        # Malformed JSON or read issue → safe default
        return ["flashcards", "practice"]


def main() -> None:
    if not SETS_DIR.exists():
        print(f"⚠️ No {SETS_DIR} folder found; writing empty map.")
        OUTFILE.write_text("{}", encoding="utf-8")
        return

    mapping: dict[str, list[str]] = {}
    for p in sorted(SETS_DIR.glob("*.json")):
        name = p.stem
        mapping[name] = infer_modes_for_set(p)

    OUTFILE.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"✅ Wrote {OUTFILE} with {len(mapping)} collections.")


if __name__ == "__main__":
    main()
