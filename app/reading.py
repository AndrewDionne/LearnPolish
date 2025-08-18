import os
import json
from pathlib import Path

def generate_reading_html(set_name, data):
    """Generate the reading.html page for a flashcard set."""

    # Ensure output directory
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    reading_path = os.path.join(output_dir, "reading.html")
   
    # Prepare data
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



    print(f"✅ reading.html generated for: {set_name}")
    return reading_html