# app/sets_api.py
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from shutil import rmtree
import subprocess
import os
import shlex

from .modes import SET_TYPES
from .models import db, UserSet
from .auth import token_required
from .utils import build_all_mode_indexes

from .debug_trace import trace

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

# Also export alias used by app factory if it imports as sets_bp
sets_bp = sets_api

# =============================================================================
# Helpers (listing / hygiene)
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
# Git publishing (Option B only: GITHUB_TOKEN + GITHUB_REPO_SLUG)
# =============================================================================

def _collect_commit_targets(slug: str, modes: list[str]) -> list[Path]:
    """
    Return a robust list of repo-relative *files and dirs* to stage.
    We include each slug directory AND its index.html explicitly so 'git add'
    definitely sees a file path.
    """
    targets: list[Path] = []

    # JSON
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        targets.append(json_path)

    # Per-mode pages
    for m in modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            targets.append(d)
            ix = d / "index.html"
            if ix.exists():
                targets.append(ix)

    # Common artifacts / indexes
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

def _run(cmd, cwd, check=True):
    return subprocess.run(
        cmd, cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        check=check
    ).stdout

def _prepare_repo(root: Path, token: str, repo_slug: str, branch: str = "main") -> str:
    """Ensure identity, remote, and branch are correct for Option B."""
    # 1) identity (ok if already set)
    _run(["git", "config", "--global", "--add", "safe.directory", str(root)], root, check=False)
    _run(["git", "config", "user.name",  "Path to Polish Bot"], root, check=False)
    _run(["git", "config", "user.email", "bot@pathtopolish.app"], root, check=False)

    # 2) remote url (classic PAT over HTTPS uses owner as username)
    owner = repo_slug.split("/", 1)[0]
    remote_url = f"https://{owner}:{token}@github.com/{repo_slug}.git"
    remotes = _run(["git", "remote", "-v"], root, check=False)
    if "origin" not in remotes:
        _run(["git", "remote", "add", "origin", remote_url], root, check=True)
    else:
        _run(["git", "remote", "set-url", "origin", remote_url], root, check=False)

    # 3) branch (Render often checks out in detached HEAD)
    _run(["git", "fetch", "origin", "--prune"], root, check=False)
    current = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, check=False).strip()
    if current == "HEAD":
        _run(["git", "checkout", "-B", branch], root, check=True)  # create/update local branch
    else:
        _run(["git", "checkout", branch], root, check=False)

    # set upstream & fast-forward if it exists
    _run(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], root, check=False)
    _run(["git", "pull", "--ff-only", "origin", branch], root, check=False)

    return remote_url

def _git_add_commit_push(paths: list[Path], message: str) -> None:
    """
    Add/commit/push repo-relative paths to GitHub using ONLY:
      - GITHUB_TOKEN
      - GITHUB_REPO_SLUG (e.g. "AndrewDionne/LearnPolish")
      - GIT_BRANCH (default: "main")
    """
    root = Path(current_app.root_path).parent  # repo root on Render

    def log_i(msg: str):
        print(msg, flush=True)
        try:
            current_app.logger.info(msg)
        except Exception:
            pass

    def run(args: list[str], ok_if_fails: bool = False) -> str:
        cmd = " ".join(args)
        log_i(f"git$ {cmd}")
        try:
            out = subprocess.check_output(
                args, cwd=str(root), stderr=subprocess.STDOUT, text=True
            )
            if out.strip():
                log_i(out.strip())
            return out
        except subprocess.CalledProcessError as e:
            if ok_if_fails:
                log_i(f"[ignored] {e.output.strip()}")
                return e.output
            raise

    # ------------------------
    # Env (Option B only)
    # ------------------------
    token     = os.getenv("GITHUB_TOKEN")
    repo_slug = os.getenv("GITHUB_REPO_SLUG") or os.getenv("GITHUB_REPOSITORY")
    branch    = (os.getenv("GIT_BRANCH") or "main").strip() or "main"
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set (Option B)")
    if not repo_slug:
        raise RuntimeError("GITHUB_REPO_SLUG (or GITHUB_REPOSITORY) is not set (Option B)")

    # Ensure repo/init
    if not (root / ".git").exists():
        run(["git", "init"])

    # Prepare remote + branch (handles identity, detached HEAD, upstream)
    _prepare_repo(root, token, repo_slug, branch)

    # Normalize to repo-relative paths (robust even if inputs are relative)
    to_add_rel: list[str] = []
    for p in paths:
        if not p:
            continue
        p = Path(p)
        p_abs = p if p.is_absolute() else (root / p)
        if not p_abs.exists():
            continue
        rel = p_abs.relative_to(root)
        to_add_rel.append(str(rel))

    if not to_add_rel:
        raise RuntimeError("Nothing to push (no repo-relative files)")

    # Stage aggressively (captures new files under given paths)
    run(["git", "add", "-A", "--"] + to_add_rel)

    # Commit (allow empty so we always have a branch tip)
    run(["git", "commit", "-m", message, "--no-gpg-sign"], ok_if_fails=True)

    # Push (retry once after rebase)
    try:
        run(["git", "push", "origin", f"HEAD:{branch}"])
    except subprocess.CalledProcessError:
        log_i("git push rejected; pulling --rebase and retrying")
        run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)
        run(["git", "push", "origin", f"HEAD:{branch}"])

def _push_and_verify(slug: str, gen_modes: list[str], primary_message: str) -> None:
    """
    Primary push via _git_add_commit_push(); if Git still reports changes for
    this slug, run a conservative fallback that adds specific paths again.
    """
    # Primary pass
    targets = _collect_commit_targets(slug, gen_modes)
    current_app.logger.info("publish targets for %s -> %s", slug, [str(t) for t in targets])
    _git_add_commit_push(targets, primary_message)

    # Verify working tree is clean for this slug
    root = Path(current_app.root_path).parent
    try:
        # Only check the paths we actually track for this slug
        check_paths = [
            str(SETS_DIR / f"{slug}.json"),
            str(PAGES_DIR / "flashcards" / slug),
            str(PAGES_DIR / "practice"   / slug),
            str(PAGES_DIR / "reading"    / slug),
            str(PAGES_DIR / "listening"  / slug),
            str(PAGES_DIR / "static"     / slug / "r2_manifest.json"),
        ]
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--"] + check_paths,
            cwd=str(root), stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        out = e.output

    if not (out or "").strip():
        return  # clean for this slug; nothing else to do

    current_app.logger.warning(
        "post-push verify: still see changes for %s; running fallback add/commit/push",
        slug
    )

    # Conservative, file-focused fallback
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

    # Re-add common indexes (harmless if unchanged)
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
# API (NOTE: Blueprint is mounted at url_prefix="/api" in app factory)
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

    root = Path(current_app.root_path).parent

    def run(cmd: str):
        try:
            out = subprocess.check_output(shlex.split(cmd), cwd=str(root))
            return out.decode("utf-8", "ignore").strip()
        except Exception as e:
            return f"ERROR: {e!r}"

    def redact(url: str) -> str:
        if not isinstance(url, str):
            return url
        val = url
        for k in ("GITHUB_TOKEN", "GH_TOKEN"):
            tok = os.getenv(k, "")
            if tok:
                val = val.replace(tok, "****")
        return val

    data = {
        "cwd": str(root),
        "exists": {
            "has_dot_git": (root / ".git").exists(),
            "sets_dir": SETS_DIR.exists(),
            "pages_dir": PAGES_DIR.exists(),
        },
        "git": {
            "inside_work_tree": run("git rev-parse --is-inside-work-tree"),
            "branch":           run("git rev-parse --abbrev-ref HEAD"),
            "status":           run("git status --porcelain"),
            "remotes":          redact(run("git remote -v")),
            "last_commit":      run("git log -1 --oneline"),
            "config_user_name": run("git config user.name"),
            "config_user_email":run("git config user.email"),
        },
        "env": {
            "GIT_BRANCH": os.getenv("GIT_BRANCH"),
            "GIT_REMOTE": redact(os.getenv("GIT_REMOTE") or ""),
            "GITHUB_REPO_SLUG": os.getenv("GITHUB_REPO_SLUG"),
            "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY"),
            "HAS_GITHUB_TOKEN": bool(os.getenv("GITHUB_TOKEN")),
            "HAS_GH_TOKEN": bool(os.getenv("GH_TOKEN")),
        },
        "paths": {
            "repo_root": str(root),
            "SETS_DIR": str(SETS_DIR),
            "PAGES_DIR": str(PAGES_DIR),
        }
    }
    return jsonify({"ok": True, **data}), 200

@sets_api.route("/admin/publish_now", methods=["POST"])
@token_required
def admin_publish_now(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug  = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards","practice"]
    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    # Always regenerate before pushing
    try:
        _regen_pages_for_slug(slug, modes)
    except Exception as e:
        current_app.logger.warning("publish_now: regen failed: %s", e)

    targets = _collect_commit_targets(slug, modes)
    _git_add_commit_push(targets, f"manual: {slug} [{','.join(modes)}]")

    # Return a short summary + current git status
    root = Path(current_app.root_path).parent
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
    except subprocess.CalledProcessError as e:
        status = e.output
    try:
        rem = subprocess.check_output(["git", "remote", "-v"], cwd=str(root), text=True)
    except subprocess.CalledProcessError as e:
        rem = e.output

    return jsonify({
        "ok": True,
        "slug": slug,
        "modes": modes,
        "pushed": [str(p) for p in targets],
        "git_status": status,
        "git_remotes": rem
    }), 200

@sets_api.route("/admin/push", methods=["POST"])
@token_required
def admin_push(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards", "practice"]

    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    targets = _collect_commit_targets(slug, modes)
    _git_add_commit_push(targets, f"manual: {slug} [{','.join(modes)}]")

    # quick verify summary
    root = Path(current_app.root_path).parent
    out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
    return jsonify({"ok": True, "pushed": [str(p) for p in targets], "status": out}), 200

@sets_api.route("/admin/git_smoke", methods=["POST"], endpoint="sets_admin_git_smoke")
@token_required
def admin_git_smoke(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    try:
        from datetime import datetime, timezone
        slug = ".publish_smoke"
        marker = PAGES_DIR / slug  # e.g., docs/.publish_smoke
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"ok {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")

        _git_add_commit_push([marker], "chore: publish smoke marker")
        return jsonify({"ok": True, "path": str(marker)}), 200
    except Exception as e:
        # always JSON on error
        return jsonify({"ok": False, "error": str(e)}), 500
