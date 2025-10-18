# app/admin_debug.py
from flask import Blueprint, jsonify, request, current_app
from pathlib import Path
import os, subprocess, shlex

from .auth import token_required
from .constants import SETS_DIR, PAGES_DIR
from .sets_utils import sanitize_filename
from .sets_api import _git_add_commit_push  # reuse your helper

admin_debug = Blueprint("admin_debug", __name__)

def _run(cmd, cwd):
    try:
        out = subprocess.check_output(cmd, cwd=str(cwd), stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "out": out}
    except Exception as e:
        return {"ok": False, "err": str(e)}

@admin_debug.route("/api/admin/git_diag", methods=["GET"])
@token_required
def git_diag(current_user):
    # lock it to admins
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    root = Path(current_app.root_path).parent  # your repo root at runtime
    slug = sanitize_filename((request.args.get("slug") or "").strip() or "Zebra_18-12")

    # mask token but show presence/length
    gh = os.environ.get("GH_TOKEN")
    masked = f"{gh[:4]}…{gh[-4:]}" if gh and len(gh) >= 8 else (gh and "set") or None

    resp = {
        "ok": True,
        "paths": {
            "repo_root": str(root),
            "PAGES_DIR": str(PAGES_DIR.resolve()),
            "SETS_DIR": str(SETS_DIR.resolve()),
        },
        "env": {
            "GH_TOKEN": masked,
            "GIT_REMOTE": os.environ.get("GIT_REMOTE"),
            "GIT_BRANCH": os.environ.get("GIT_BRANCH"),
        },
        "exists": {
            "json": (SETS_DIR / f"{slug}.json").exists(),
            "flashcards_index": (PAGES_DIR / "flashcards" / slug / "index.html").exists(),
            "practice_index": (PAGES_DIR / "practice" / slug / "index.html").exists(),
            "reading_index": (PAGES_DIR / "reading" / slug / "index.html").exists(),
            "listening_index": (PAGES_DIR / "listening" / slug / "index.html").exists(),
        },
        "git": {
            "has_dot_git": (root / ".git").exists(),
            "is_work_tree": _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root),
            "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root),
            # remote -v can leak tokens if you set a tokenized origin; omit for safety
            "status": _run(["git", "status", "--porcelain"], cwd=root),
            "user_name": _run(["git", "config", "user.name"], cwd=root),
            "user_email": _run(["git", "config", "user.email"], cwd=root),
        }
    }
    return jsonify(resp), 200

@admin_debug.route("/api/admin/push", methods=["POST"])
@token_required
def admin_push(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards", "practice"]

    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    to_commit = []
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists(): to_commit.append(json_path)

    for m in modes:
        d = PAGES_DIR / m / slug
        if d.exists(): to_commit.append(d)

    # common index artifacts
    commons = [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice" / "index.html",
        PAGES_DIR / "reading" / "index.html",
        PAGES_DIR / "listening" / "index.html",
        PAGES_DIR / "set_modes.json",
    ]
    for p in commons:
        if p.exists(): to_commit.append(p)

    try:
        _git_add_commit_push(to_commit, f"admin push: {slug} [{','.join(modes)}]")
        return jsonify({"ok": True, "pushed": [str(p) for p in to_commit]}), 200
    except Exception as e:
        current_app.logger.exception("admin push failed")
        return jsonify({"ok": False, "error": str(e), "attempted": [str(p) for p in to_commit]}), 500
