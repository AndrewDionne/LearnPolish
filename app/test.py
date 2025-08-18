import os
import json
from pathlib import Path

def generate_test_html(set_name, data):
    """Generate the test.html page for a flashcard set!"""

    # Ensure output directory
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    test_path = os.path.join(output_dir, "test.html")
   
    # Prepare data
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