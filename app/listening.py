import os
import json
from pathlib import Path

def generate_listening_html(set_name, data):
    """Generate the listening.html page for a flashcard set."""
    output_dir = Path("docs/output") / set_name
    output_dir.mkdir(parents=True, exist_ok=True)

    listening_path = output_dir / "listening.html"
    cards_json = json.dumps(data, ensure_ascii=False)

    listening_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} Listening Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f0f0f0;
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
            margin-bottom: 1.5rem;
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
    <h1>🎧 Listening Mode – {set_name}</h1>
    <div class="info">Listen to a Polish phrase and select the correct English meaning.</div>
    <a class="back" href="index.html">← Back to Mode Selection</a>

    <script>
        const cards = {cards_json};
        const setName = "{set_name}";
    </script>

    <!-- Listening quiz logic will be added here -->

</body>
</html>
"""

    
    print(f"✅ listening.html generated for: {set_name}")
    return listening_html