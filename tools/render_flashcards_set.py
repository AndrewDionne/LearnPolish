# tools/render_flashcards_set.py
import sys, json, pathlib, os

# --- ensure we can import 'app.*' from project root ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main(slug: str):
    # 1) load the set JSON
    src = pathlib.Path(f"docs/sets/{slug}.json")
    if not src.exists():
        print(f"ERR: {src} not found", file=sys.stderr)
        sys.exit(2)
    data = json.loads(src.read_text(encoding="utf-8"))

    # 2) import the module
    try:
        import app.flashcards as m
    except Exception as e:
        print(f"ERR: cannot import app.flashcards: {e}", file=sys.stderr)
        sys.exit(2)

    # 3) call generate_flashcard_html(set_name, data_or_items)
    html = None
    tried = []
    for payload in (data, data.get("items"), None):
        if payload is None:
            continue
        try:
            res = m.generate_flashcard_html(slug, payload)
            if isinstance(res, str):
                html = res
            elif isinstance(res, tuple) and res and isinstance(res[0], str):
                html = res[0]
            elif isinstance(res, dict) and "html" in res:
                html = res["html"]
            else:
                raise TypeError(f"unexpected return type: {type(res)}")
            break
        except Exception as e:
            tried.append(repr(e))
            continue

    if not html:
        print("ERR: generate_flashcard_html failed with payloads; errors:", file=sys.stderr)
        for t in tried:
            print(" -", t, file=sys.stderr)
        sys.exit(1)

    # 4) Wrap fragment if needed
    if "<html" not in html.lower():
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Flashcards – {slug}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="/LearnPolish/static/app.css" />
</head>
<body>
{html}
<script src="/LearnPolish/static/js/app-config.js"></script>
<script src="/LearnPolish/static/js/api.js"></script>
</body>
</html>
"""

    # 5) write the page
    out = pathlib.Path(f"docs/flashcards/{slug}/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("Wrote", out)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/render_flashcards_set.py <slug>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
