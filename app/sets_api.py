# app/sets_api.py

from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from shutil import rmtree
import subprocess

from .modes import SET_TYPES
from .models import db, UserSet
from .auth import token_required
from .utils import build_all_mode_indexes

# Try to use your git_utils if available; fall back to subprocess
try:
    from .git_utils import Repo  # GitPython-like wrapper in your repo
except Exception:
    Repo = None

# Centralized paths + constants
from .constants import SETS_DIR, PAGES_DIR, SET_MODES_JSON

# Canonical helpers from sets_utils
from .sets_utils import (
    sanitize_filename,
    create_set as util_create_set,
    delete_set_file,
    list_global_sets,
    get_set_metadata,
)

# Keep the map-builder explicit (no silent fallback)
from .create_set_modes import main as rebuild_set_modes_map

# Single blueprint for this module
sets_api = Blueprint("sets_api", __name__)

# ----------------------------
# Helpers
# ----------------------------

def _global_map_by_name(global_list: list[dict]) -> dict[str, dict]:
    return {s["name"]: s for s in global_list if "name" in s}

def _with_deprecation_headers(resp, successor_path: str):
    """
    Add soft deprecation hints without breaking existing consumers.
    See: RFC 8594 (Link rel="successor-version"); Deprecation header (draft).
    """
    try:
        resp.headers["Deprecation"] = "true"
        resp.headers["Link"] = f'<{successor_path}>; rel="successor-version"'
    except Exception:
        pass
    return resp

def _apply_list_params(items: list[dict]):
    """
    Optional filters for listings:
      ?q=<substring> (case-insensitive match on name)
      ?limit=, ?offset=
      ?sort=name|count  (default=name)
      ?order=asc|desc   (default=asc)
    """
    q = (request.args.get("q") or "").strip().lower()
    sort = (request.args.get("sort") or "name").lower()
    order = (request.args.get("order") or "asc").lower()
    try:
        limit = int(request.args.get("limit", 0))
    except Exception:
        limit = 0
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0

    out = items
    if q:
        out = [x for x in out if q in (x.get("name") or "").lower()]

    keyfunc = (lambda x: (x.get("name") or "").lower())
    if sort == "count":
        keyfunc = (lambda x: (
            x.get("count") if isinstance(x.get("count"), int) else -1,
            (x.get("name") or "").lower()
        ))
    out.sort(key=keyfunc, reverse=(order == "desc"))

    if offset > 0 or (limit and limit > 0):
        start = max(offset, 0)
        end = start + max(limit, 0) if limit and limit > 0 else None
        out = out[start:end]

    return out

def _ensure_modes(row: dict) -> dict:
    """
    Guarantee a 'modes' array on each listing row.
    If the set JSON already has modes, keep them.
    Otherwise derive from 'type'.
    """
    try:
        if isinstance(row.get("modes"), list) and row["modes"]:
            return row
        t = (row.get("type") or "").lower()
        if t in ("flashcards", "vocab", "cards"):
            row["modes"] = ["learn", "speak"]
        elif t in ("reading", "read"):
            row["modes"] = ["read"]
        elif t in ("listening", "listen", "audio"):
            row["modes"] = ["listen"]
        else:
            row["modes"] = []
    except Exception:
        row["modes"] = []
    return row

# Replace legacy docs root alias with centralized pages dir
DOCS_ROOT = PAGES_DIR

def _safe_rmtree(p: Path):
    try:
        if p.exists():
            rmtree(p)
    except Exception:
        pass

def _delete_set_files_everywhere(set_name: str):
    # remove the JSON via existing delete_set_file (if it wraps extra logic)
    try:
        delete_set_file(set_name)
    except Exception:
        try:
            (SETS_DIR / f"{set_name}.json").unlink(missing_ok=True)
        except Exception:
            pass

    # nuke generated assets and pages
    _safe_rmtree(DOCS_ROOT / "flashcards" / set_name)
    _safe_rmtree(DOCS_ROOT / "practice"   / set_name)
    _safe_rmtree(DOCS_ROOT / "reading"    / set_name)
    _safe_rmtree(DOCS_ROOT / "listening"  / set_name)
    _safe_rmtree(DOCS_ROOT / "static"     / set_name)

# --- GIT PUBLISH HELPER (module-level) ---
def _git_add_commit_push(paths: list[Path], message: str) -> None:
    """
    Add/commit/push a set of paths.
    - Uses git_utils.Repo if present; else subprocess.
    - Honors GIT_REMOTE and GIT_BRANCH (for Render).
    """
    root = Path(current_app.root_path).parent  # repo root
    to_add = [str(p) for p in paths if p and Path(p).exists()]
    if not to_add:
        current_app.logger.info("Nothing to add; no paths exist.")
        return

    remote_url = (current_app.config.get("GIT_REMOTE") or "").strip()
    branch     = (current_app.config.get("GIT_BRANCH") or "main").strip() or "main"
    author_n   = current_app.config.get("GIT_AUTHOR_NAME", "Path to POLISH Bot")
    author_e   = current_app.config.get("GIT_AUTHOR_EMAIL", "bot@pathtopolish.app")

    if Repo is not None:
        repo = Repo(str(root))
        # ensure identity
        try:
            repo.git.config("--local", "user.email", author_e)
            repo.git.config("--local", "user.name",  author_n)
        except Exception:
            pass

        # ensure remote if provided
        if remote_url:
            try:
                repo.git.remote("remove", "origin")
            except Exception:
                pass
            repo.git.remote("add", "origin", remote_url)

        repo.git.add(to_add)
        if repo.is_dirty():
            repo.index.commit(message, author=author_n, author_email=author_e)
            repo.git.push("origin", f"HEAD:{branch}")
        else:
            current_app.logger.info("No changes to commit.")
        return

    # subprocess fallback
    def run(args): return subprocess.check_output(args, cwd=str(root))

    # identity
    try:
        run(["git", "config", "user.email", author_e])
        run(["git", "config", "user.name",  author_n])
    except Exception:
        pass

    # remote
    if remote_url:
        try:
            run(["git", "remote", "remove", "origin"])
        except Exception:
            pass
        run(["git", "remote", "add", "origin", remote_url])

    run(["git", "add"] + to_add)
    try:
        run(["git", "commit", "-m", message])
    except subprocess.CalledProcessError as e:
        out = (getattr(e, "output", b"") or b"").decode("utf-8", "ignore")
        if "nothing to commit" not in out:
            raise
    run(["git", "push", "origin", f"HEAD:{branch}"])

# --- PAGE REGEN HELPER (module-level) ---
def _regen_pages_for_slug(slug: str, modes: list[str]) -> None:
    """
    Rebuild pages for this slug, adapting to whichever generator signature exists.
    Prefers sets_utils.regenerate_set_pages; falls back to per-mode modules.
    """
    from . import sets_utils

    regen = getattr(sets_utils, "regenerate_set_pages", None)
    if regen:
        try: regen(slug, modes=modes, force=True, verbose=True); return
        except TypeError: pass
        try: regen(slug, force=True, verbose=True); return
        except TypeError: pass
        try: regen(slug, force=True); return
        except TypeError: pass
        regen(slug); return

    def _try_module(mod_name, funcs):
        try:
            mod = __import__(f"app.{mod_name}", fromlist=["*"])
        except Exception:
            return False
        for fn in funcs:
            f = getattr(mod, fn, None)
            if not f: continue
            try: f(slug); return True
            except TypeError:
                try: f(slug, force=True); return True
                except Exception: continue
        return False

    for m in modes:
        if m == "flashcards":
            _try_module("flashcards", ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "practice":
            _try_module("practice",   ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "reading":
            _try_module("reading",    ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "listening":
            _try_module("listening",  ["create_listening_set", "generate_set_pages", "generate_pages", "build_pages"])

# ----------------------------
# API
# ----------------------------

# 0) Global sets (canonical shape)
@sets_api.route("/global_sets", methods=["GET"])
def global_sets():
    """
    Returns: [
      { "name": "...", "count": 123, "type": "flashcards|reading|unknown", "created_by": "system|user|me" },
      ...
    ]
    Optional filters: ?q=&limit=&offset=&sort=name|count&order=asc|desc
    """
    glist = list_global_sets()
    glist = _apply_list_params(glist)
    glist = [_ensure_modes(x) for x in glist]
    resp = jsonify(glist)
    return _with_deprecation_headers(resp, "/api/sets/available")

# 1) My sets (canonical shape, mark ownership and enrich private)
@sets_api.route("/my_sets", methods=["GET"])
@token_required
def my_sets(current_user):
    """
    Returns the SAME canonical shape as global_sets, for the current user's library.
    Ownership (for showing the 🗑️ Delete button):
      - If UserSet.is_owner == True -> created_by = "me"
      - Else if present in global -> keep global's created_by (usually "system")
      - Else (not in global) -> treat as private -> created_by = "me"
    """
    rows = UserSet.query.filter_by(user_id=current_user.id).all()
    user_names = [r.set_name for r in rows]
    ownership = {r.set_name: bool(getattr(r, "is_owner", False)) for r in rows}

    glist = list_global_sets()
    gmap = _global_map_by_name(glist)

    out = []
    for name in sorted(set(user_names)):
        if name in gmap:
            meta = gmap[name].copy()
            if ownership.get(name):
                meta["created_by"] = "me"
            meta = _ensure_modes(meta)
            out.append(meta)
        else:
            meta = get_set_metadata(name)
            meta["created_by"] = "me"
            meta = _ensure_modes(meta)
            out.append(meta)

    out = _apply_list_params(out)
    resp = jsonify(out)
    return _with_deprecation_headers(resp, "/api/my/sets")

# 2) Add a set to user library
@sets_api.route("/add_set", methods=["POST"])
@token_required
def add_set(current_user):
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    if not set_name:
        return jsonify({"message": "Set name required"}), 400

    set_name = sanitize_filename(set_name)
    existing = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if existing:
        resp = jsonify({"message": "Already in your collection"})
        return _with_deprecation_headers(resp, "/api/my/sets")

    db.session.add(UserSet(user_id=current_user.id, set_name=set_name, is_owner=False))
    db.session.commit()
    resp = jsonify({"message": f"Set '{set_name}' added to your collection"})
    return _with_deprecation_headers(resp, "/api/my/sets")

# 3) Remove a set from user library
@sets_api.route("/remove_set", methods=["POST"])
@token_required
def remove_set(current_user):
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    if not set_name:
        return jsonify({"message": "Set name required"}), 400

    set_name = sanitize_filename(set_name)
    user_set = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not user_set:
        resp = jsonify({"message": "Set not in your collection"})
        return _with_deprecation_headers(resp, f"/api/my/sets/{set_name}")

    db.session.delete(user_set)
    db.session.commit()
    resp = jsonify({"message": f"Set '{set_name}' removed from your collection"})
    return _with_deprecation_headers(resp, f"/api/my/sets/{set_name}")

# 4) Create a set (owner-only on create)
@sets_api.route("/create_set_v2", methods=["POST"])
@token_required
def create_set(current_user):
    """
    Body: { set_type: "<one of SET_TYPES>", set_name: str, data: [ ... ] }
    - Saves docs/sets/<name>.json
    - Generates assets/pages for implied modes
    - Adds to user's collection with is_owner=True
    - Commits & pushes changes so GitHub Pages serves it
    """
    body = request.get_json(silent=True) or {}
    set_type = (body.get("set_type") or "").strip().lower()
    set_name = (body.get("set_name") or "").strip()
    data = body.get("data")

    if set_type not in SET_TYPES:
        return jsonify({"message": f"Invalid set_type. Allowed: {sorted(SET_TYPES)}"}), 400
    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    if not isinstance(data, list) or not data:
        return jsonify({"message": "data must be a non-empty JSON array"}), 400

    safe_name = sanitize_filename(set_name)
    if not safe_name:
        return jsonify({"message": "Invalid set_name"}), 400

    json_path = SETS_DIR / f"{safe_name}.json"
    if json_path.exists():
        return jsonify({"message": "set_already_exists"}), 409  # frontend expects this key

    try:
        # 1) Write JSON (+ any assets your util_create_set generates)
        meta = util_create_set(set_type, safe_name, data)

        # 2) Link to user as owner
        existing = UserSet.query.filter_by(user_id=current_user.id, set_name=safe_name).first()
        if not existing:
            db.session.add(UserSet(user_id=current_user.id, set_name=safe_name, is_owner=True))
        else:
            existing.is_owner = True
        db.session.commit()

        # 3) Regenerate static pages for implied mode(s)
        implied = {
            "flashcards": ["flashcards"],
            "reading":    ["reading"],
            "listening":  ["listening"],
            "practice":   ["practice"],
        }
        modes = implied.get(set_type, ["flashcards"])
        _regen_pages_for_slug(safe_name, modes)

        # 4) Rebuild landing/index artifacts (best-effort)
        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

        # 5) Commit & push the changed files so GH Pages serves them
        to_commit = [json_path] + [PAGES_DIR / m / safe_name for m in modes]
        # include common index artifacts if present
        for p in [
            PAGES_DIR / "flashcards" / "index.html",
            PAGES_DIR / "practice"   / "index.html",
            PAGES_DIR / "reading"    / "index.html",
            PAGES_DIR / "listening"  / "index.html",
            PAGES_DIR / "set_modes.json",
        ]:
            if p.exists():
                to_commit.append(p)
        _git_add_commit_push(to_commit, f"build: {safe_name} [{','.join(modes)}]")

        meta["created_by"] = "me"
        meta["modes"] = modes
        return jsonify(meta), 201

    except Exception as e:
        return jsonify({"message": "Failed to create set", "error": str(e)}), 500

# 5) Delete a set (owner-only)
@sets_api.route("/delete_set/<string:set_name>", methods=["POST"])
@token_required
def delete_set(current_user, set_name):
    """
    Owner action:
      - If only the owner has this set: delete files and unlink all rows.
      - If others also have it: transfer ownership to another user, unlink current owner, keep files.
    """
    safe_name = sanitize_filename(set_name or "")
    if not safe_name:
        return jsonify({"message": "Invalid set name"}), 400

    links = UserSet.query.filter_by(set_name=safe_name).all()
    if not links:
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        return jsonify({"ok": True, deleted: True}), 200

    me_link = next((l for l in links if l.user_id == current_user.id), None)
    if not me_link or not getattr(me_link, "is_owner", False):
        return jsonify({"message": "Only the owner can delete this set"}), 403

    others = [l for l in links if l.user_id != current_user.id]

    if not others:
        for l in links:
            db.session.delete(l)
        db.session.commit()
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes after delete: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json after delete: %s", e)
        return jsonify({"ok": True, "handover": True, "new_owner_id": new_owner_link.user_id}), 200

    new_owner_link = sorted(others, key=lambda l: l.id)[0]
    me_link.is_owner = False
    new_owner_link.is_owner = True
    db.session.delete(me_link)
    db.session.commit()

    try:
        build_all_mode_indexes()
    except Exception as e:
        current_app.logger.warning("Failed to rebuild mode indexes after handover: %s", e)
    try:
        rebuild_set_modes_map()
    except Exception as e:
        current_app.logger.warning("Failed to rebuild set_modes.json after handover: %s", e)

    return jsonify({"ok": True, handover: True, new_owner_id: new_owner_link.user_id}), 200

# 6) Admin build & publish (server-side)
@sets_api.route("/admin/build_publish", methods=["POST", "OPTIONS"])
@token_required
def admin_build_publish(current_user):
    """
    Admin-only: rebuild static pages for a slug and push to GitHub.
    Body: { "slug": "10LS", "modes": ["flashcards","reading","listening","practice"]? }
    """
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards"]

    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    json_path = SETS_DIR / f"{slug}.json"
    if not json_path.exists():
        current_app.logger.warning("Set JSON not found at %s; generator may still handle DB-based sets.", json_path)

    try:
        _regen_pages_for_slug(slug, modes)

        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json: %s", e)

        changed = [json_path]
        for m in modes:
            changed.append(PAGES_DIR / m / slug)
        for p in [
            PAGES_DIR / "flashcards" / "index.html",
            PAGES_DIR / "practice" / "index.html",
            PAGES_DIR / "reading" / "index.html",
            PAGES_DIR / "listening" / "index.html",
            PAGES_DIR / "set_modes.json",
        ]:
            if p.exists():
                changed.append(p)

        _git_add_commit_push(changed, f"build: {slug} [{','.join(modes)}]")

        return jsonify({"ok": True}), 200

    except Exception as e:
        current_app.logger.exception("admin_build_publish failed for %s", slug)
        return jsonify({"ok": False, "error": str(e)}), 500
