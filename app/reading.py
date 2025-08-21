import os
import json
from pathlib import Path
from .sets_utils import load_set_modes, sanitize_filename

def generate_reading_html(set_name, data):
    set_modes = load_set_modes()
    if "reading" in set_modes and set_name not in set_modes["reading"]:
        print(f"⏭️ Skipping reading for '{set_name}' (not in reading mode).")
        return None

    # ✅ Ensure output dir exists (docs/reading/<set_name>/index.html)
    output_dir = Path("docs/reading") / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    reading_path = output_dir / "index.html"

    for idx, entry in enumerate(data):
        filename = f"{idx}_{sanitize_filename(entry['phrase'])}.mp3"
        entry["audio_file"] = f"/static/{set_name}/audio/{filename}"

    cards_json = json.dumps(data, ensure_ascii=False)

    # Practice HTML
    reading_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} Reading Mode</title>
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
            color: #555;
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
    <h1>📖 Reading Mode – {set_name}</h1>
    <div class="info">Read Polish phrases aloud and receive pronunciation feedback.</div>
    <a class="back" href="index.html">← Back to Mode Selection</a>

    <script>
        const cards = {cards_json};
        const setName = "{set_name}";
    </script>

    <!-- Reading interaction JS can be added here -->
 
   function goHome() {{
      const pathParts = window.location.pathname.split("/");
      const repo = pathParts[1];
      window.location.href = window.location.hostname === "andrewdionne.github.io" ? `/${{repo}}/` : "/";
    }}
    
</body>
</html>
"""



        # Write to file
    with open(reading_path, "w", encoding="utf-8") as f:
        f.write(reading_html)

    print(f"✅ reading/index.html generated for: {set_name}")
    return reading_path