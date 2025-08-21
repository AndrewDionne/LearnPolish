from flask import render_template, request, redirect, send_file, jsonify, url_for
import os, json, shutil
from pathlib import Path
from .config import RENDER_URL, GITHUB_PAGES_URL, MODES
from .sets_utils import (
    sanitize_filename,
    load_sets_for_mode,
    load_set_modes,
    save_set_modes,
    get_all_sets,
    SETS_DIR,
    MODES  
)
from .utils import (
    generate_flashcard_html,
    handle_flashcard_creation,
    get_azure_token
)
from .git_utils import commit_and_push_changes


def init_routes(app):

    # Inject URLs into all templates
    @app.context_processor
    def inject_base_urls():
        return {
            "RENDER_URL": RENDER_URL,
            "GITHUB_PAGES_URL": GITHUB_PAGES_URL
        }

    # === Public Home ===
    @app.route("/")
    def home():
        sets = get_all_sets()
        set_modes = load_set_modes()
        return render_template("index.html", sets=sets, set_modes=set_modes)

        # === Per-Set Routes (serve generated HTML from docs/<mode>/<set_name>/index.html) ===
    def serve_mode_set(mode, set_name):
        set_path = Path("docs") / mode / set_name / "index.html"
        if not set_path.exists():
            return f"❌ {mode.capitalize()} set '{set_name}' not found", 404
        return send_file(set_path)

    @app.route("/flashcards/<set_name>/")
    def flashcards_set(set_name):
        return serve_mode_set("flashcards", set_name)

    @app.route("/practice/<set_name>/")
    def practice_set(set_name):
        return serve_mode_set("practice", set_name)

    @app.route("/reading/<set_name>/")
    def reading_set(set_name):
        return serve_mode_set("reading", set_name)

    @app.route("/listening/<set_name>/")
    def listening_set(set_name):
        return serve_mode_set("listening", set_name)

    @app.route("/test/<set_name>/")
    def test_set(set_name):
        return serve_mode_set("test", set_name)


    # === Learning Mode Pages ===
    @app.route("/flashcards")
    def flashcards_home():
        sets = load_sets_for_mode("flashcards")
        return render_template("flashcards_home.html", sets=sets)

    @app.route("/practice")
    def practice_home():
        sets = load_sets_for_mode("practice")
        return render_template("practice_home.html", sets=sets)

    @app.route("/reading")
    def reading_home():
        sets = load_sets_for_mode("reading")
        return render_template("reading_home.html", sets=sets)

    @app.route("/listening")
    def listening_home():
        sets = load_sets_for_mode("listening")
        return render_template("listening_home.html", sets=sets)

    @app.route("/test")
    def test_home():
        sets = load_sets_for_mode("test")
        return render_template("test_home.html", sets=sets)

    # === Azure Token Endpoint ===
    @app.route("/api/token", methods=["GET"])
    def get_token():
        return get_azure_token()

    # === Static/Output File Serving ===
    @app.route("/custom_static/<path:filename>")
    def serve_static_file(filename):
        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "docs" / "static" / filename
        if not full_path.exists():
            print("❌ Audio file not found:", full_path)
            return "Audio file not found", 404
        return send_file(full_path)

    
    @app.route("/docs")
    def serve_docs_home():
        docs_index = Path("docs/index.html")
        if not docs_index.exists():
            return "Homepage not found", 404
        return send_file(docs_index)

    # === Set Management System ===
    @app.route("/manage_sets", methods=["GET"])
    def manage_sets():
        # Get all sets with counts and modes from sets_utils
        sets = get_all_sets()  # already returns [{"name": ..., "count": ..., "modes": [...]}, ...]

        return render_template(
            "manage_sets.html",
            sets=sets,
            sets_data=sets  # if template still uses sets_data
    )

    @app.route("/update_set_modes", methods=["POST"])
    def update_set_modes():
        updates = request.get_json()
        save_set_modes(updates)
        commit_and_push_changes("✅ Updated mode assignments")
        return jsonify({"status": "ok"})

    @app.route("/delete_set/<set_name>", methods=["POST"])
    def delete_set(set_name):
        shutil.rmtree(SETS_DIR / set_name, ignore_errors=True)
        shutil.rmtree(Path("docs/static") / set_name, ignore_errors=True)
        for mode in MODES:
            shutil.rmtree(Path("docs") / mode / set_name, ignore_errors=True)

        commit_and_push_changes(f"🗑️ Deleted set {set_name}")
        return redirect(url_for("manage_sets"))

    @app.route("/delete_sets", methods=["GET", "POST"])
    def delete_sets():
        if request.method == "POST":
            for set_name in request.form.getlist("sets_to_delete"):
                shutil.rmtree(SETS_DIR / set_name, ignore_errors=True)
                shutil.rmtree(Path("docs/static") / set_name, ignore_errors=True)
                for mode in MODES:
                    shutil.rmtree(Path("docs") / mode / set_name, ignore_errors=True)

            commit_and_push_changes("🗑️ Bulk delete sets")
            return redirect(url_for("manage_sets"))

        all_sets = get_all_sets()
        return render_template("delete_sets.html", all_sets=all_sets)

    # === Create New Sets ===
    @app.route("/create", methods=["GET", "POST"])
    def create_set_page():
        if request.method == "POST":
            result = handle_flashcard_creation(request.form)

            # If the function returns something truthy (HTML, Response, etc.),
            # it's likely an error message/page, so just return it
            if result:
                return result

            # If no error, go to Manage Sets
            return redirect(url_for("manage_sets"))

        # GET request → show empty creation page
        set_name = request.args.get("set_name", "")
        return render_template("create.html", set_name=set_name)

    @app.route("/create_set", methods=["POST"])
    def create_set_with_data():
        name = request.form.get("new_set_name", "").strip()
        if name:
            set_dir = SETS_DIR / name
            set_dir.mkdir(parents=True, exist_ok=True)

            json_path = set_dir / "data.json"
            if not json_path.exists():
                json_path.write_text("[]", encoding="utf-8")

            print(f"✅ Created set: {name}")
            commit_and_push_changes(f"✅ Created set {name}")
            return redirect(url_for("create_set_page", set_name=name))

        return redirect(url_for("manage_sets"))

    # === Legacy Config Update (Form POST) ===
    @app.route("/update_set_config", methods=["POST"])
    def update_set_config():
        data = request.form.to_dict(flat=False)
        config = {mode: data.get(mode, []) for mode in MODES}
        save_set_modes(config)
        print(f"💾 Updated mode config: {config}")
        commit_and_push_changes("✅ Updated mode config via form")
        return redirect(url_for("manage_sets"))
