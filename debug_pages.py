#!/usr/bin/env python3
"""
Debug static page generation/publish for a specific set slug.

Usage examples:
  # Just inspect & verify presence
  python debug_pages.py --slug 10LS --modes flashcards

  # Build pages locally using your app generator (no push)
  python debug_pages.py --slug 10LS --modes flashcards --build

  # Build + commit + push to GitHub (uses your local git creds)
  python debug_pages.py --slug 10LS --modes flashcards --build --push

  # After pushing, verify GH Pages is serving it
  python debug_pages.py --slug 10LS --modes flashcards --check-gh
"""

import os, sys, json, subprocess
from pathlib import Path
from typing import List
import argparse

def ok(m): print(f"✅ {m}")
def warn(m): print(f"⚠️  {m}")
def err(m): print(f"❌ {m}")

ROOT = Path(__file__).resolve().parent

def git_run(args: List[str], cwd: Path = ROOT, check=True):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=check)

def gh_root_url() -> str:
    # Andrew’s GH Pages base
    return "https://andrewdionne.github.io/LearnPolish"

def ensure_import_path():
    # Allow "from app import create_app" when running at repo root
    if str(ROOT) not in sys.path:
      sys.path.insert(0, str(ROOT))

def load_app():
    ensure_import_path()
    from app import create_app
    app = create_app()
    return app

def print_constants():
    try:
        from app.constants import SETS_DIR, PAGES_DIR
        ok(f"SETS_DIR = {SETS_DIR}")
        ok(f"PAGES_DIR = {PAGES_DIR}")
    except Exception as e:
        warn(f"Could not load app.constants (will infer): {e}")
        # Fallback guesses:
        sets_dir = ROOT / "docs" / "sets"
        pages_dir = ROOT / "docs"
        ok(f"[guess] SETS_DIR = {sets_dir}")
        ok(f"[guess] PAGES_DIR = {pages_dir}")

def expected_output_dirs(slug: str, modes: List[str]) -> List[Path]:
    base = ROOT / "docs"
    out = []
    for m in modes:
        out.append(base / m / slug)
    return out

def check_outputs(slug: str, modes: List[str]) -> bool:
    all_present = True
    for d in expected_output_dirs(slug, modes):
        idx = d / "index.html"
        if idx.exists():
            ok(f"Found: {idx}")
        else:
            all_present = False
            err(f"Missing: {idx}")
    return all_present

def build_with_app(slug: str, modes: List[str]) -> bool:
    """
    Call your generator inside Flask app context, adapting to the actual signature.
    Falls back to mode-specific builders if needed.
    """
    import inspect
    try:
        app = load_app()
    except Exception as e:
        err(f"Could not create Flask app: {e}")
        return False

    with app.app_context():
        ok(f"Building pages for slug '{slug}' in modes {modes} ...")

        # 1) Try sets_utils.regenerate_set_pages with flexible call shapes
        try:
            from app.sets_utils import regenerate_set_pages as regen
            sig = inspect.signature(regen)
            params = set(sig.parameters.keys())

            # Try the most likely order without keywords
            tried = []
            if "modes" in params and "force" in params and "verbose" in params:
                tried.append(("regen(slug, modes=..., force=True, verbose=True)", lambda: regen(slug, modes=modes, force=True, verbose=True)))
            if "force" in params and "verbose" in params:
                tried.append(("regen(slug, force=True, verbose=True)", lambda: regen(slug, force=True, verbose=True)))
            if "force" in params:
                tried.append(("regen(slug, force=True)", lambda: regen(slug, force=True)))
            tried.append(("regen(slug)", lambda: regen(slug)))

            for label, call in tried:
                try:
                    rc = call()
                    ok(f"regenerate_set_pages OK via {label}: {rc}")
                    return True
                except TypeError as te:
                    warn(f"Signature mismatch for {label}: {te}")
                except Exception as e:
                    warn(f"Call failed for {label}: {e}")
        except Exception as e:
            warn(f"No sets_utils.regenerate_set_pages available: {e}")

        # 2) Fallback: per-mode builders (best-effort)
        def try_mode(mod_name, func_names):
            try:
                mod = __import__(f"app.{mod_name}", fromlist=["*"])
                for fn in func_names:
                    if hasattr(mod, fn):
                        f = getattr(mod, fn)
                        try:
                            rc = f(slug)  # most common shape
                            ok(f"{mod_name}.{fn}('{slug}') OK: {rc}")
                            return True
                        except TypeError:
                            # try force kw if exists
                            try:
                                rc = f(slug, force=True)
                                ok(f"{mod_name}.{fn}('{slug}', force=True) OK: {rc}")
                                return True
                            except Exception as e:
                                warn(f"{mod_name}.{fn} signature failed: {e}")
            except Exception as e:
                warn(f"Could not import app.{mod_name}: {e}")
            return False

        tried_any = False
        for m in modes:
            if m == "flashcards":
                tried_any |= try_mode("flashcards", ["generate_set_pages", "generate_pages", "build_pages"])
            elif m == "practice":
                tried_any |= try_mode("practice", ["generate_set_pages", "generate_pages", "build_pages"])
            elif m == "reading":
                tried_any |= try_mode("reading", ["generate_set_pages", "generate_pages", "build_pages"])
            elif m == "listening":
                tried_any |= try_mode("listening", ["create_listening_set", "generate_set_pages", "generate_pages", "build_pages"])
            else:
                warn(f"Unknown mode: {m}")

        return bool(tried_any)


def git_status():
    try:
        r = git_run(["git", "status", "--porcelain"])
        if r.stdout.strip():
            warn("Working tree has changes:")
            print(r.stdout)
        else:
            ok("Working tree clean.")
    except Exception as e:
        warn(f"git status failed: {e}")

def git_push(paths: List[Path], message: str):
    try:
        args = ["git", "add"] + [str(p) for p in paths]
        git_run(args)
        git_run(["git", "commit", "-m", message])
        ok("Committed changes.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in (e.stderr or "") + (e.stdout or ""):
            warn("Nothing to commit (already up to date).")
        else:
            raise
    git_run(["git", "push"])
    ok("Pushed to origin.")

def head_request(url: str, timeout=12):
    import requests
    try:
        r = requests.head(url, timeout=timeout)
        return r.status_code
    except Exception:
        # Fallback GET if HEAD blocked
        try:
            r = requests.get(url, timeout=timeout)
            return r.status_code
        except Exception as e:
            warn(f"HEAD/GET failed for {url}: {e}")
            return 0

def check_github_pages(slug: str, modes: List[str]) -> None:
    base = gh_root_url().rstrip("/")
    for m in modes:
        url1 = f"{base}/{m}/{slug}/"
        url2 = f"{base}/{m}/{slug}/index.html"
        s1 = head_request(url1)
        s2 = head_request(url2)
        if s1 == 200 or s2 == 200:
            ok(f"GH Pages serving {m}/{slug} (HTTP {s1 or s2}) → {url1}")
        else:
            err(f"GH Pages NOT serving {m}/{slug} (HTTP {s1},{s2}) → {url1}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="Set slug, e.g. 10LS")
    ap.add_argument("--modes", default="flashcards", help="Comma list: flashcards,practice,reading,listening")
    ap.add_argument("--build", action="store_true", help="Attempt to regenerate pages using app generators")
    ap.add_argument("--push", action="store_true", help="git add/commit/push changed output dirs")
    ap.add_argument("--check-gh", action="store_true", help="Check GitHub Pages URL for 200")
    args = ap.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    print("— Constants —")
    print_constants()

    print("\n— Presence check —")
    present = check_outputs(args.slug, modes)

    if (not present) and args.build:
        print("\n— Build —")
        if build_with_app(args.slug, modes):
            # Re-check presence after build
            print("\n— Presence check (after build) —")
            present = check_outputs(args.slug, modes)

    if args.push:
        print("\n— Git —")
        git_status()
        out_dirs = expected_output_dirs(args.slug, modes)
        try:
            git_push(out_dirs, f"build: {args.slug} [{','.join(modes)}]")
        except Exception as e:
            err(f"git push failed: {e}")

    if args.check_gh:
        print("\n— GitHub Pages check —")
        check_github_pages(args.slug, modes)

if __name__ == "__main__":
    main()
