from .flashcard_generator import generate_flashcard_html
from .practice_generator import generate_practice_html
from .reading_generator import generate_reading_html
from .test_generator import generate_test_html
# add more generators here if needed

MODE_GENERATORS = {
    "flashcards": generate_flashcard_html,
    "practice": generate_practice_html,
    "reading": generate_reading_html,
    "test": generate_test_html
}
