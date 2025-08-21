import os
import json
from pathlib import Path
from .sets_utils import load_set_modes, sanitize_filename

def generate_test_html(set_name, data):
    set_modes = load_set_modes()
    if "test" in set_modes and set_name not in set_modes["test"]:
        print(f"⏭️ Skipping test for '{set_name}' (not in test mode).")
        return None

    output_dir = Path("docs/test") / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"

    for idx, entry in enumerate(data):
        filename = f"{idx}_{sanitize_filename(entry['phrase'])}.mp3"
        entry["audio_file"] = f"/static/{set_name}/audio/{filename}"

    cards_json = json.dumps(data, ensure_ascii=False)

    test_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} – Test Yourself</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f9f9f9;
            padding: 2rem;
            text-align: center;
        }}
        h1 {{
            font-size: 1.6rem;
            margin-bottom: 1rem;
        }}
        .info {{
            font-size: 1rem;
            color: #666;
            margin-bottom: 2rem;
        }}
        .back {{
            display: block;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #555;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>🧪 Test Yourself – {set_name}</h1>
    <div class="info">Test your memory by matching meanings, pronunciations, and audio.</div>
    <a class="back" href="index.html">← Back to Mode Selection</a>

    <script>
        const cards = {cards_json};
        const setName = "{set_name}";
    </script>

    <!-- Add your test quiz/game logic here -->

</body>
</html>
"""


    print(f"✅ test.html generated for: {set_name}")
    return test_html