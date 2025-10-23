# app/sets_api.py
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from shutil import rmtree
import subprocess

from .modes import SET_TYPES
from .models import db, UserSet
from .auth import token_required
from .utils import build_all_mode_indexes

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

# =============================================================================
# Helpers
# =============================================================================

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

# =============================================================================
# Git publishing (single authoritative helper + verification)
# =============================================================================

def _collect_commit_targets(slug: str, modes: list[str]) -> list[Path]:
    """
    Return a robust list of repo-relative *files and dirs* to stage.
    We include each slug directory AND its index.html explicitly so 'git add'
    definitely sees files (Git ignores empty dirs).
    """
    targets: list[Path] = []

    # JSON per-set
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        targets.append(json_path)

    # Mode pages and their index.html
    for m in modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            targets.append(d)
            ix = d / "index.html"
            if ix.exists():
                targets.append(ix)

    # Common artifacts / indexes / manifest
    commons = [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice"   / "index.html",
        PAGES_DIR / "reading"    / "index.html",
        PAGES_DIR / "listening"  / "index.html",
        PAGES_DIR / "set_modes.json",
        PAGES_DIR / "static"     / slug / "r2_manifest.json",
    ]
    for p in commons:
        if p.exists():
            targets.append(p)

    return targets


def _git_add_commit_push(paths: list[Path], message: str) -> None:
    """
    Add/commit/push repo-relative paths to GitHub.

    Environment (any ONE remote source works):
      - Preferred: GIT_REMOTE (full https URL; credentials may be embedded)
      - Else build from:
          GH_TOKEN or GITHUB_TOKEN
          GITHUB_REPO_SLUG or GITHUB_REPOSITORY (owner/repo)
      - GIT_BRANCH (default: main)
      - GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL (optional)

    Retries once on non-fast-forward; logs status and remotes for debugging.
    """
    import os
    root = Path(current_app.root_path).parent  # repo root

    def run(args: list[str], ok_if_fails: bool = False) -> str:
        # Log to both logger and stdout so Render captures it
        line = "git: " + " ".join(args)
        try:
            current_app.logger.info(line)
        except Exception:
            print(line, flush=True)

        try:
            out = subprocess.check_output(
                args, cwd=str(root), stderr=subprocess.STDOUT, text=True
            )
            return out
        except subprocess.CalledProcessError as e:
            if ok_if_fails:
                try:
                    current_app.logger.warning("git (ignored): %s\n%s", " ".join(args), e.output)
                except Exception:
                    print("git (ignored):", " ".join(args), "\n", e.output, flush=True)
                return e.output
            raise

    # Ensure repo/init + mark safe directory
    if not (root / ".git").exists():
        run(["git", "init"])
    run(["git", "config", "--global", "--add", "safe.directory", str(root)], ok_if_fails=True)

    # Identity every time (avoids container user issues)
    author_name  = os.getenv("GIT_AUTHOR_NAME")  or "Path to Polish Bot"
    author_email = os.getenv("GIT_AUTHOR_EMAIL") or "bot@pathtopolish.app"
    run(["git", "config", "user.name", author_name], ok_if_fails=True)
    run(["git", "config", "user.email", author_email], ok_if_fails=True)

    # Determine remote URL
    branch = (os.getenv("GIT_BRANCH") or "main").strip() or "main"
    configured_remote = os.getenv("GIT_REMOTE", "").strip()

    remote_url = configured_remote
    if not remote_url:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
        slug  = os.getenv("GITHUB_REPO_SLUG") or os.getenv("GITHUB_REPOSITORY") or ""
        if not token or not slug:
            raise RuntimeError(
                "Missing remote config: set GIT_REMOTE or both (GH|GITHUB)_TOKEN and GITHUB_REPO_(SLUG|REPOSITORY)"
            )
        remote_url = f"https://x-access-token:{token}@github.com/{slug}.git"

    # Ensure 'origin' exists and points to the right URL
    existing_remotes = run(["git", "remote"], ok_if_fails=True)
    if "origin" in existing_remotes.splitlines():
        run(["git", "remote", "set-url", "origin", remote_url])
    else:
        run(["git", "remote", "add", "origin", remote_url])
    # Show remotes in logs
    remotes_verbose = run(["git", "remote", "-v"], ok_if_fails=True)
    try:
        current_app.logger.info("git remotes:\n%s", remotes_verbose)
    except Exception:
        print("git remotes:\n" + remotes_verbose, flush=True)

    # Be on the desired branch & rebase latest
    run(["git", "checkout", "-B", branch])
    run(["git", "fetch", "origin", branch, "--depth=1"], ok_if_fails=True)
    run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)

    # Normalize to repo-relative paths; include both dirs and files
    to_add_rel: list[str] = []
    for p in paths:
        if not p:
            continue
        p = Path(p)
        if not p.exists():
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = Path(os.path.relpath(str(p), str(root)))
        to_add_rel.append(str(rel))

    if not to_add_rel:
        raise RuntimeError("Nothing to push (no repo-relative files)")

    # Pre-status for debugging
    pre = run(["git", "status", "--porcelain"], ok_if_fails=True)
    try:
        current_app.logger.info("git status (pre-add):\n%s", pre)
    except Exception:
        print("git status (pre-add):\n" + pre, flush=True)

    # Stage aggressively under the provided paths
    run(["git", "add", "-A", "--"] + to_add_rel)

    mid = run(["git", "status", "--porcelain"], ok_if_fails=True)
    try:
        current_app.logger.info("git status (post-add):\n%s", mid)
    except Exception:
        print("git status (post-add):\n" + mid, flush=True)

    # Commit (allow empty to carry index-only changes like renames)
    run(["git", "commit", "-m", message, "--no-gpg-sign"], ok_if_fails=True)

    # Push with one retry on non-FF
    try:
        run(["git", "push", "origin", f"HEAD:{branch}"])
    except subprocess.CalledProcessError:
        try:
            current_app.logger.warning("git push rejected; pulling --rebase and retrying")
        except Exception:
            print("git push rejected; pulling --rebase and retrying", flush=True)
        run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)
        run(["git", "push", "origin", f"HEAD:{branch}"])

    post = run(["git", "status", "--porcelain"], ok_if_fails=True)
    try:
        current_app.logger.info("git status (post-push):\n%s", post)
    except Exception:
        print("git status (post-push):\n" + post, flush=True)


def _push_and_verify(slug: str, gen_modes: list[str], primary_message: str) -> None:
    """
    Primary push via _git_add_commit_push(); if Git still reports changes for
    this slug, run a conservative fallback that adds specific files again.
    """
    # Primary pass
    targets = _collect_commit_targets(slug, gen_modes)
    try:
        current_app.logger.info("publish targets for %s -> %s", slug, [str(t) for t in targets])
    except Exception:
        print(f"publish targets for {slug} -> {[str(t) for t in targets]}", flush=True)
    _git_add_commit_push(targets, primary_message)

    # Verify working tree is clean for this slug
    root = Path(current_app.root_path).parent
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(root),
            stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        out = e.output

    if slug not in out:
        return  # clean; nothing else to do

    try:
        current_app.logger.warning(
            "post-push verify: still see changes for %s; running fallback add/commit/push",
            slug
        )
    except Exception:
        print(f"post-push verify: still see changes for {slug}; running fallback add/commit/push", flush=True)

    # Precise, file-focused fallback
    specific: list[Path] = []
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        specific.append(json_path)

    for m in gen_modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            specific.append(d)
            ix = d / "index.html"
            if ix.exists():
                specific.append(ix)

    man = PAGES_DIR / "static" / slug / "r2_manifest.json"
    if man.exists():
        specific.append(man)

    for p in [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice"   / "index.html",
        PAGES_DIR / "reading"    / "index.html",
        PAGES_DIR / "listening"  / "index.html",
        PAGES_DIR / "set_modes.json",
    ]:
        if p.exists():
            specific.append(p)

    _git_add_commit_push(specific, f"{primary_message} (verify-fix)")

# =============================================================================
# Page regeneration
# =============================================================================

def _regen_pages_for_slug(slug: str, modes: list[str]) -> None:
    """
    Rebuild pages for this slug, adapting to whichever generator signature exists.
    Prefers sets_utils.regenerate_set_pages; falls back to per-mode modules.
    """
    from . import sets_utils

    regen = getattr(sets_utils, "regenerate_set_pages", None)
    if regen:
        try:
            regen(slug, modes=modes, force=True, verbose=True); return
        except TypeError:
            pass
        try:
            regen(slug, force=True, verbose=True); return
        except TypeError:
            pass
        try:
            regen(slug, force=True); return
        except TypeError:
            pass
        regen(slug); return

    def _try_module(mod_name, funcs):
        try:
            mod = __import__(f"app.{mod_name}", fromlist=["*"])
        except Exception:
            return False
        for fn in funcs:
            f = getattr(mod, fn, None)
            if not f:
                continue
            try:
                f(slug); return True
            except TypeError:
                try:
                    f(slug, force=True); return True
                except Exception:
                    continue
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

# =============================================================================
# API
# =============================================================================

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

    # map generator names -> client names
    CLIENT_MODE = {
        "flashcards": "learn",
        "practice":   "speak",
        "reading":    "read",
        "listening":  "listen",
    }

    def _augment_meta(meta: dict | None, *, existed: bool) -> dict:
        """
        Normalize the response so the client always sees:
          - set_name, slug
          - modes: ["learn","speak",...]
          - pages: {"learn": "/flashcards/<slug>/", ...}
        """
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
            try:
                build_all_mode_indexes()
            except Exception as e:
                current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
            try:
                rebuild_set_modes_map()
            except Exception as e:
                current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

            _push_and_verify(safe_name, gen_modes, f"rebuild: {safe_name} [{','.join(gen_modes)}]")

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
        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

        # push to GitHub (with verification)
        _push_and_verify(safe_name, gen_modes, f"build: {safe_name} [{','.join(gen_modes)}]")

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

        # Log what we think changed (non-authoritative; push verifies)
        changed: list[Path] = []
        if json_path.exists():
            changed.append(json_path)
        for m in modes:
            p = PAGES_DIR / m / slug
            if p.exists():
                changed.append(p)
        for p in [
            PAGES_DIR / "flashcards" / "index.html",
            PAGES_DIR / "practice"   / "index.html",
            PAGES_DIR / "reading"    / "index.html",
            PAGES_DIR / "listening"  / "index.html",
            PAGES_DIR / "set_modes.json",
        ]:
            if p.exists():
                changed.append(p)
        current_app.logger.info("admin_build_publish: will push %s", [str(x) for x in changed])

        _push_and_verify(slug, modes, f"build: {slug} [{','.join(modes)}]")

        return jsonify({"ok": True}), 200

    except Exception as e:
        current_app.logger.exception("admin_build_publish failed for %s", slug)
        return jsonify({"ok": False, "error": str(e)}), 500

@sets_api.route("/admin/git_diag", methods=["GET"])
@token_required
def admin_git_diag(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    import shlex
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
