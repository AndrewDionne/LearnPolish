#!/usr/bin/env python3
import argparse, json, re, shutil
from pathlib import Path

def detect_type(name, data):
    t = str(data.get("type", "")).lower()
    s = str(name or "").lower()
    if t in ("reading","read") or re.search(r"\b(read|reading|story|article)\b", s):
        return "reading"
    if t in ("listening","listen") or re.search(r"\b(listen|listening|audio|podcast)\b", s):
        return "listening"
    return "flashcards"  # default → Learn/Speak

def modes_from_type(t):
    return {"reading":["read"], "listening":["listen"]}.get(t, ["learn","speak"])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="Folder containing *.json sets (can be nested)")
    p.add_argument("--dest", default="docs/sets", help="Destination folder (default: docs/sets)")
    args = p.parse_args()

    src = Path(args.src).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    index_rows = []
    seen = set()

    for jf in sorted(src.rglob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        name = data.get("name") or jf.stem
        typ  = detect_type(name, data)
        modes = modes_from_type(typ)

        # copy file into docs/sets/
        out = dest / jf.name
        shutil.copy2(jf, out)

        # de-duplicate by name
        if name not in seen:
            index_rows.append({"name": name, "modes": modes, "type": typ})
            seen.add(name)

    # write docs/set_modes.json
    index_rows.sort(key=lambda r: r["name"].lower())
    out_index = dest.parent / "set_modes.json"   # docs/set_modes.json
    out_index.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Copied {len(list(dest.glob('*.json')))} sets → {dest}")
    print(f"Wrote index → {out_index} ({len(index_rows)} entries)")

if __name__ == "__main__":
    main()
