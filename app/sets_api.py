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
    Add/commit/push repo-relative paths to GitHub.
    Uses env:
      - GITHUB_REPO_SLUG  (e.g. "AndrewDionne/LearnPolish")
      - GITHUB_TOKEN  (or GH_TOKEN)
      - GIT_BRANCH    (default: main)
      - GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL (defaults provided)
    """
    import os, subprocess
    root = Path(current_app.root_path).parent  # repo root on Render

    def run(args: list[str], ok_if_fails: bool=False):
        current_app.logger.info("git: %s", " ".join(args))
        try:
            return subprocess.check_output(args, cwd=str(root), stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            if ok_if_fails:
                current_app.logger.warning("git (ignored error): %s\n%s", " ".join(args), e.output)
                return e.output
            raise

    # Ensure repo exists
    if not (root / ".git").exists():
        run(["git", "init"])

    # Make working tree safe for container users
    run(["git", "config", "--global", "--add", "safe.directory", str(root)], ok_if_fails=True)

    # Identity (set unconditionally, ignore failures)
    author_name  = os.getenv("GIT_AUTHOR_NAME")  or "Path to POLISH Bot"
    author_email = os.getenv("GIT_AUTHOR_EMAIL") or "bot@pathtopolish.app"
    run(["git", "config", "user.name",  author_name],  ok_if_fails=True)
    run(["git", "config", "user.email", author_email], ok_if_fails=True)

    # Remote + branch
    token  = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    slug   = os.getenv("GITHUB_REPO_SLUG") or os.getenv("GITHUB_REPOSITORY")
    branch = (os.getenv("GIT_BRANCH") or "main").strip() or "main"
    if not token:
        raise RuntimeError("GITHUB_TOKEN (or GH_TOKEN) is not set")
    if not slug:
        raise RuntimeError("GITHUB_REPO_SLUG (or GITHUB_REPOSITORY) is not set")

    remote_url = f"https://x-access-token:{token}@github.com/{slug}.git"
    if "origin" in run(["git", "remote"], ok_if_fails=True):
        run(["git", "remote", "set-url", "origin", remote_url])
    else:
        run(["git", "remote", "add", "origin", remote_url])

    # Make sure we're on the correct branch and roughly in sync
    run(["git", "checkout", "-B", branch])
    run(["git", "fetch", "origin", branch, "--depth=1"], ok_if_fails=True)
    run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)

    # Stage repo-relative paths
    to_add_rel: list[str] = []
    for p in paths:
        if not p: continue
        p = Path(p)
        if not p.exists(): continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = Path(os.path.relpath(str(p), str(root)))
        to_add_rel.append(str(rel))

    if not to_add_rel:
        raise RuntimeError("Nothing to push (no repo-relative files)")

    run(["git", "add"] + to_add_rel)
    run(["git", "status", "--porcelain"], ok_if_fails=True)

    # Commit with inline identity to bypass any repo/global config issues
    run([
        "git",
        "-c", f"user.name={author_name}",
        "-c", f"user.email={author_email}",
        "commit", "-m", message, "--no-gpg-sign"
    ], ok_if_fails=True)

    # Push (retry once after a rebase pull if needed)
    try:
        run(["git", "push", "origin", f"HEAD:{branch}"])
    except subprocess.CalledProcessError:
        current_app.logger.warning("git push rejected; attempting pull --rebase then retry")
        run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)
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

    # Post-check: log missing expectations (non-fatal)
    expected = []
    if "flashcards" in modes: expected.append(PAGES_DIR / "flashcards" / slug / "index.html")
    if "practice"   in modes: expected.append(PAGES_DIR / "practice"   / slug / "index.html")
    if "reading"    in modes: expected.append(PAGES_DIR / "reading"    / slug / "index.html")
    if "listening"  in modes: expected.append(PAGES_DIR / "listening"  / slug / "index.html")
    missing = [p for p in expected if not p.exists()]
    if missing:
        current_app.logger.warning("create_set_v2: expected pages missing for %s -> %s",
                                   slug, [str(p) for p in missing])


def _collect_commit_targets(slug: str, modes: list[str]) -> list[Path]:
    targets = []
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        targets.append(json_path)

    for m in modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            targets.append(d)

    # common index artifacts
    for p in [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice"   / "index.html",
        PAGES_DIR / "reading"    / "index.html",
        PAGES_DIR / "listening"  / "index.html",
        PAGES_DIR / "set_modes.json",
        PAGES_DIR / "static"     / slug / "r2_manifest.json",
    ]:
        if p.exists():
            targets.append(p)
    return targets


# 4) Create a set (owner-only on create)
@sets_api.route("/create_set_v2", methods=["POST"])
@token_required
def create_set(current_user):
    current_app.logger.info("create_set_v2: start")

    body = request.get_json(silent=True) or {}
    set_type = (body.get("set_type") or "").strip().lower()
    set_name = (body.get("set_name") or "").strip()
    items = body.get("data")

    # ---- validation ----
    if set_type not in SET_TYPES:
        return jsonify({"message": f"Invalid set_type. Allowed: {sorted(SET_TYPES)}"}), 400
    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"message": "data must be a non-empty JSON array"}), 400

    safe_name = sanitize_filename(set_name)
    if not safe_name:
        return jsonify({"message": "Invalid set_name"}), 400

    json_path = SETS_DIR / f"{safe_name}.json"

    # generation modes (internal generator names)
    implied = {
        "flashcards": ["flashcards", "practice"],
        "reading":    ["reading"],
        "listening":  ["listening"],
        "practice":   ["practice"],
    }
    gen_modes = implied.get(set_type, ["flashcards", "practice"])

    # client-mode labels
    CLIENT_MODE = {"flashcards": "learn", "practice": "speak", "reading": "read", "listening": "listen"}

    def _augment_meta(meta: dict | None, *, existed: bool) -> dict:
        meta = dict(meta or {})
        meta.setdefault("set_name", set_name)
        meta.setdefault("slug", safe_name)
        meta["modes"] = [CLIENT_MODE[m] for m in gen_modes if m in CLIENT_MODE]
        meta["pages"] = {CLIENT_MODE[m]: f"/{m}/{safe_name}/" for m in gen_modes if m in CLIENT_MODE}
        if existed:
            meta["note"] = "already_existed_regenerated"
        return meta

    existed = json_path.exists()

    try:
        # ---------- IDEMPOTENT REBUILD ----------
        if existed:
            _regen_pages_for_slug(safe_name, gen_modes)
            # best-effort index rebuilds
            try: build_all_mode_indexes()
            except Exception as e: current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
            try: rebuild_set_modes_map()
            except Exception as e: current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

            targets = _collect_commit_targets(safe_name, gen_modes)
            current_app.logger.info("create_set_v2: git targets (idempotent) for %s -> %s",
                                    safe_name, [str(t) for t in targets])
            _git_add_commit_push(targets, f"rebuild: {safe_name} [{','.join(gen_modes)}]")

            meta = get_set_metadata(safe_name)
            out = _augment_meta(meta, existed=True)
            resp = jsonify(out)
            resp.headers["X-Create-Handler"] = "v2"
            return resp, 200

        # ---------- NEW CREATE ----------
        meta = util_create_set(set_type, safe_name, items)

        # link user as owner (idempotent)
        link = UserSet.query.filter_by(user_id=current_user.id, set_name=safe_name).first()
        if not link:
            db.session.add(UserSet(user_id=current_user.id, set_name=safe_name, is_owner=True))
        else:
            link.is_owner = True
        db.session.commit()

        # generate static pages
        _regen_pages_for_slug(safe_name, gen_modes)

        # best-effort index rebuilds
        try: build_all_mode_indexes()
        except Exception as e: current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try: rebuild_set_modes_map()
        except Exception as e: current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

        # push to GitHub (single, authoritative push)
        targets = _collect_commit_targets(safe_name, gen_modes)
        current_app.logger.info("create_set_v2: git targets (new) for %s -> %s",
                                safe_name, [str(t) for t in targets])
        _git_add_commit_push(targets, f"build: {safe_name} [{','.join(gen_modes)}]")

        out = _augment_meta(meta, existed=False)
        out["created_by"] = "me"
        resp = jsonify(out)
        resp.headers["X-Create-Handler"] = "v2"
        return resp, 201

    except Exception as e:
        current_app.logger.exception("create_set_v2 failed for %s: %s", safe_name, e)
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
        return jsonify({"ok": True, "deleted": True}), 200

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
        return jsonify({"ok": True, "deleted": True}), 200


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

    return jsonify({"ok": True, "handover": True, "new_owner_id": new_owner_link.user_id}), 200
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

@sets_api.route("/admin/git_diag", methods=["GET"])
@token_required
def admin_git_diag(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    import subprocess, shlex
    root = Path(current_app.root_path).parent

    def run(cmd: str):
        try:
            out = subprocess.check_output(shlex.split(cmd), cwd=str(root))
            return out.decode("utf-8", "ignore").strip()
        except Exception as e:
            return f"ERROR: {e!r}"

    data = {
        "cwd": str(root),
        "inside_work_tree": run("git rev-parse --is-inside-work-tree"),
        "branch": run("git rev-parse --abbrev-ref HEAD"),
        "status": run("git status --porcelain"),
        "remotes": run("git remote -v"),
        "last_commit": run("git log -1 --oneline"),
        "git_config_user_name": run("git config user.name"),
        "git_config_user_email": run("git config user.email"),
    }
    return jsonify({"ok": True, "git": data}), 200
