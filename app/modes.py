# app/modes.py

# Core generators (these should exist)
from .flashcards import generate_flashcard_html
from .practice import generate_practice_html
from .reading import generate_reading_html

# Optional generators (may not exist yet)
try:
    from .listening import generate_listening_html  # not built yet? fine.
except Exception:
    generate_listening_html = None

try:
    from .test import generate_test_html
except Exception:
    generate_test_html = None


def modes_for_type(set_type: str) -> list[str]:
    """
    Map a set 'type' to the learning modes we should generate.
    - flashcards -> flashcards + practice
    - reading    -> reading
    """
    if set_type == "flashcards":
        return ["flashcards", "practice"]
    if set_type == "reading":
        return ["reading"]
    return []


# Build MODE_GENERATORS only for available generators
MODE_GENERATORS = {
    "flashcards": generate_flashcard_html,
    "practice": generate_practice_html,
    "reading": generate_reading_html,
}
if generate_listening_html:
    MODE_GENERATORS["listening"] = generate_listening_html
if generate_test_html:
    MODE_GENERATORS["test"] = generate_test_html

# Convenient exports for other modules
SET_TYPES = {"flashcards", "reading"}            # types accepted by /api/create_set
AVAILABLE_MODES = set(MODE_GENERATORS.keys())    # modes we can currently generate

__all__ = [
    "modes_for_type",
    "MODE_GENERATORS",
    "SET_TYPES",
    "AVAILABLE_MODES",
    "generate_flashcard_html",
    "generate_practice_html",
    "generate_reading_html",
] + ([ "generate_listening_html" ] if generate_listening_html else []) \
  + ([ "generate_test_html" ] if generate_test_html else [])
