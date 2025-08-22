import os
import re
import json
import shutil
import requests
from pathlib import Path
from flask import jsonify, redirect, url_for, render_template, send_file
from gtts import gTTS
from jinja2 import Environment, FileSystemLoader

from .config import MODES  # <-- now imported from config.py
from .git_utils import commit_and_push_changes
from .modes import (
    generate_practice_html,
    generate_flashcard_html,
    generate_reading_html,
    generate_listening_html,
    generate_test_html
)
# mapping mode names to generator functions
MODE_GENERATORS = {
    "flashcards": generate_flashcard_html,
    "practice": generate_practice_html,
    "reading": generate_reading_html,
    "listening": generate_listening_html,
    "test": generate_test_html
}

from .sets_utils import (
    SETS_DIR,
    sanitize_filename,
    get_all_sets,
    load_set_modes,
    load_sets_for_mode
)


# === Utility ===

def open_browser():
    """Open local dev server in a browser."""
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

# === Homepage Export ===
def export_homepage_static():
    """Re-render homepage index.html for GitHub Pages."""
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.html")
    sets = get_all_sets()
    set_modes = load_set_modes()
    rendered = template.render(sets=sets, set_modes=set_modes)
    (Path("docs") / "index.html").write_text(rendered, encoding="utf-8")

def export_mode_pages():
    """Export each mode landing page to docs/<mode>/index.html for GitHub Pages."""
    env = Environment(loader=FileSystemLoader("templates"))
    sets = get_all_sets()
    set_modes = load_set_modes()

    mode_templates = {
        "flashcards": "flashcards_home.html",
        "practice": "practice_home.html",
        "reading": "reading_home.html",
        "listening": "listening_home.html",
        "test": "test_home.html",
        "manage_sets": "manage_sets.html"
    }

    for mode, template_name in mode_templates.items():
        try:
            template = env.get_template(template_name)
        except Exception as e:
            print(f"⚠️ Skipping {mode}: template {template_name} missing ({e})")
            continue

        rendered = template.render(sets=sets, set_modes=set_modes)

        outdir = Path("docs") / mode
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / "index.html"
        outfile.write_text(rendered, encoding="utf-8")

        print(f"✅ Exported {outfile}")
# === Azure Speech ===
def get_azure_token():
    """Request a temporary Azure speech token."""
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    AZURE_REGION = os.getenv("AZURE_REGION", "canadaeast")  # 👈 renamed

    if not AZURE_SPEECH_KEY:
        return jsonify({"error": "AZURE_SPEECH_KEY missing"}), 500
    if not AZURE_REGION:
        return jsonify({"error": "AZURE_REGION missing"}), 500

    url = f"https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY, "Content-Length": "0"}
    try:
        res = requests.post(url, headers=headers, timeout=6)
        res.raise_for_status()
        return jsonify({"token": res.text, "region": AZURE_REGION})
    except requests.RequestException as e:
        return jsonify({"error": "token_request_failed", "detail": str(e)}), 502

# === Set Creation / Deletion ===
def handle_flashcard_creation(form):
    """Create new set from form data and generate HTML/audio."""
    set_name = form.get("set_name", "").strip()
    json_input = form.get("json_input", "").strip()
    selected_modes = form.getlist("modes")  # Flask turns checkboxes into a list

    # Safety checks
    if not set_name:
        return "<h2 style='color:red;'>❌ Set name is required.</h2>", 400
    if (SETS_DIR / set_name).exists():
        return f"<h2 style='color:red;'>❌ Set '{set_name}' already exists.</h2>", 400

    # Parse JSON
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError:
        return "<h2 style='color:red;'>❌ Invalid JSON input format.</h2>", 400

    # Validate entries
    for entry in data:
        if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
            return "<h2 style='color:red;'>❌ Each entry must have 'phrase', 'pronunciation', and 'meaning'.</h2>", 400

    # Prepare folders
    audio_dir = Path("docs/static") / set_name / "audio"
    set_dir = SETS_DIR / set_name
    for path in (audio_dir, set_dir):
        path.mkdir(parents=True, exist_ok=True)

    # Generate audio files
    for i, entry in enumerate(data):
        phrase = entry["phrase"]
        filename = f"{i}_{sanitize_filename(phrase)}.mp3"
        filepath = audio_dir / filename
        if not filepath.exists():
            gTTS(text=phrase, lang="pl").save(filepath)

    # Save JSON data
    with open(set_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # === Generate HTML for all modes ===
    for mode in MODES:
        generator = MODE_GENERATORS.get(mode)
        if generator:
            html_path = generator(set_name, data)  # generator already writes and returns a Path
            print(f"✅ Generated {html_path}")

    # Commit changes
    commit_and_push_changes(f"✨ Created/updated set {set_name}")

    return None  # success

def generate_mode_html(set_name: str, mode: str) -> None:
    """
    Generate an index.html for a set in the given mode and save it under docs/<mode>/<set_name>/index.html
    """
    output_dir = Path("docs") / mode / set_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Render the HTML using your Jinja template for that mode
    template_name = f"{mode}.html" if mode in ["flashcards", "practice", "reading", "listening", "test"] else None
    if not template_name:
        raise ValueError(f"Unknown mode: {mode}")

    rendered = render_template(template_name, set_name=set_name)

    (output_dir / "index.html").write_text(rendered, encoding="utf-8")
    print(f"✅ Generated {output_dir}/index.html")
       
def delete_set(set_name: str):
    """Delete set folders from all locations."""
    # Delete JSON data
    shutil.rmtree(SETS_DIR / set_name, ignore_errors=True)

    # Delete audio
    shutil.rmtree(Path("docs/static") / set_name, ignore_errors=True)

    # Delete per-mode HTML
    for mode in MODES:
        shutil.rmtree(Path("docs") / mode / set_name, ignore_errors=True)

    commit_and_push_changes(f"🗑️ Deleted set: {set_name}")
    print(f"✅ Deleted set: {set_name}")

def delete_set_and_push(set_name: str):
    delete_set(set_name)
