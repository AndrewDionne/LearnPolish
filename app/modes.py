# app/modes.py

from .practice import generate_practice_html
from .flashcards import generate_flashcard_html
from .reading import generate_reading_html
from .listening import generate_listening_html
from .test import generate_test_html

__all__ = [
    "generate_practice_html",
    "generate_flashcard_html",
    "generate_reading_html",
    "generate_listening_html",
    "generate_test_html"
]
