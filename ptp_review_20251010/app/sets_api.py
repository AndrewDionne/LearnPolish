# app/sets_api.py

from flask import Blueprint, request, jsonify
from pathlib import Path
import json
from shutil import rmtree

from .modes import SET_TYPES
from .models import db, UserSet
from .auth import token_required
from .utils import build_all_mode_indexes

# ❗ Centralized paths + constants
from .constants import SETS_DIR, PAGES_DIR, SET_MODES_JSON

# Canonical helpers from sets_utils (no fallbacks)
from .sets_utils import (
    sanitize_filename,
    create_set as util_create_set,
    delete_set_file,
    list_global_sets,     # canonical global listing
    get_set_metadata,     # enrich items in /my_sets and other listings
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
        # in case resp is a tuple or something unexpected
        pass
    return resp

def _apply_list_params(items: list[dict]):
    """
    Non-breaking optional filters for listings:
      ?q=<substring>   (case-insensitive match on name)
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

    # filter
    out = items
    if q:
        out = [x for x in out if q in (x.get("name") or "").lower()]

    # sort
    keyfunc = (lambda x: (x.get("name") or "").lower())
    if sort == "count":
        keyfunc = (lambda x: (
            x.get("count") if isinstance(x.get("count"), int) else -1,
            (x.get("name") or "").lower()
        ))
    out.sort(key=keyfunc, reverse=(order == "desc"))

    # slice
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
        # fall back to manual unlink, if delete_set_file isn't present/failed
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
    glist = _apply_list_params(glist)  # non-breaking filter/sort
    glist = [_ensure_modes(x) for x in glist]
    resp = jsonify(glist)
    # Point clients to the new minimal listing at /api/sets/available
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

    Optional filters: ?q=&limit=&offset=&sort=name|count&order=asc|desc
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
            meta = _ensure_modes(meta)         # <— add
            out.append(meta)
        else:
            meta = get_set_metadata(name)
            meta["created_by"] = "me"
            meta = _ensure_modes(meta)         # <— add
            out.append(meta)

    out = _apply_list_params(out)  # non-breaking filter/sort
    resp = jsonify(out)
    # Suggest RESTful successor for new clients
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
    # Successor: POST /api/my/sets  { set_name, is_owner? }
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
    # Successor: DELETE /api/my/sets/<set_name>
    return _with_deprecation_headers(resp, f"/api/my/sets/{set_name}")

# 4) Create a set (owner-only on create)
@sets_api.route("/create_set_v2", methods=["POST"])
@token_required
def create_set(current_user):
    """
    Body: { set_type: "<one of SET_TYPES>", set_name: str, data: [ ... ] }
    - Saves docs/sets/<name>.json
    - Generates audio + pages for implied modes
    - Adds to user's collection with is_owner=True
    """
    body = request.get_json(silent=True) or {}
    set_type = (body.get("set_type") or "").strip().lower()
    set_name = (body.get("set_name") or "").strip()
    data = body.get("data")

    # ✅ single source of truth
    if set_type not in SET_TYPES:
        return jsonify({"message": f"Invalid set_type. Allowed: {sorted(SET_TYPES)}"}), 400
    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    if not isinstance(data, list) or not data:
        return jsonify({"message": "data must be a non-empty JSON array"}), 400

    safe_name = sanitize_filename(set_name)
    if not safe_name:
        return jsonify({"message": "Invalid set_name"}), 400

    # Prevent collision with an existing global set file
    p = SETS_DIR / f"{safe_name}.json"
    if p.exists():
        return jsonify({"message": f"Set '{safe_name}' already exists"}), 409

    try:
        meta = util_create_set(set_type, safe_name, data)  # saves + generates assets/pages

        # Add to user's library and mark as owner
        existing = UserSet.query.filter_by(user_id=current_user.id, set_name=safe_name).first()
        if not existing:
            db.session.add(UserSet(user_id=current_user.id, set_name=safe_name, is_owner=True))
        else:
            existing.is_owner = True
        db.session.commit()

        # Refresh landing/index pages
        try:
            build_all_mode_indexes()
        except Exception as e:
            print("⚠️ Failed to rebuild mode indexes:", e)

        # Keep docs/set_modes.json current
        try:
            rebuild_set_modes_map()
        except Exception as e:
            print("⚠️ Failed to rebuild set_modes.json after create:", e)

        meta["created_by"] = "me"
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
    - If others also have it: transfer ownership to another user, unlink current owner (or set is_owner=False), keep files.
    Returns:
      { ok: true, deleted: true }  OR
      { ok: true, handover: true, new_owner_id: <id> }
    """
    safe_name = sanitize_filename(set_name or "")
    if not safe_name:
        return jsonify({"message": "Invalid set name"}), 400

    # who has this set?
    links = UserSet.query.filter_by(set_name=safe_name).all()
    if not links:
        # Nothing in DB: best-effort file cleanup
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        return jsonify({"ok": True, deleted: True}), 200

    # ensure caller is/was owner
    me_link = next((l for l in links if l.user_id == current_user.id), None)
    if not me_link or not getattr(me_link, "is_owner", False):
        return jsonify({"message": "Only the owner can delete this set"}), 403

    # others?
    others = [l for l in links if l.user_id != current_user.id]

    if not others:
        # Sole owner -> delete files + unlink all rows
        for l in links:
            db.session.delete(l)
        db.session.commit()
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        # rebuild indices
        try:
            build_all_mode_indexes()
        except Exception as e:
            print("⚠️ Failed to rebuild mode indexes after delete:", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            print("⚠️ Failed to rebuild set_modes.json after delete:", e)
        return jsonify({"ok": True, deleted: True}), 200

    # there are other users -> transfer ownership
    new_owner_link = sorted(others, key=lambda l: l.id)[0]  # stable heuristic
    me_link.is_owner = False
    new_owner_link.is_owner = True
    # Optionally also remove the owner's membership (acts like "remove from my library")
    db.session.delete(me_link)
    db.session.commit()

    # Keep files; nothing to rebuild except indexes (optional, cheap)
    try:
        build_all_mode_indexes()
    except Exception as e:
        print("⚠️ Failed to rebuild mode indexes after handover:", e)
    try:
        rebuild_set_modes_map()
    except Exception as e:
        print("⚠️ Failed to rebuild set_modes.json after handover:", e)

    return jsonify({"ok": True, handover: True, new_owner_id: new_owner_link.user_id}), 200
