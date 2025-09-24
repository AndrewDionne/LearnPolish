# app/api.py
from flask import Blueprint, request, jsonify
from pathlib import Path

from .auth import token_required
from .models import db, Score, UserSet, GroupMembership, Group

# Prefer canonical sets directory from sets_utils; fall back to docs/sets
try:
    from .sets_utils import SETS_DIR  # expected Path("docs/sets")
except Exception:
    SETS_DIR = Path("docs/sets")

api_bp = Blueprint("api", __name__)

# ---------------------------
# Account / profile utilities
# ---------------------------

@api_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
    """Return the authenticated user's public profile."""
    created = getattr(current_user, "created_at", None)
    return jsonify({
        "id": current_user.id,
        "email": getattr(current_user, "email", None),
        "name": getattr(current_user, "name", None),
        "is_admin": bool(getattr(current_user, "is_admin", False)),
        "created_at": created.isoformat() if created else None,
    })

# ---------------------------
# Scores (existing + new)
# ---------------------------

@api_bp.route("/submit_score", methods=["POST"])
@token_required
def submit_score(current_user):
    """Create a score row. Hardened parsing, same external behavior."""
    data = request.get_json(silent=True) or {}

    set_name = (data.get("set_name") or "").strip()
    mode = (data.get("mode") or "practice").strip() or "practice"
    score_val = data.get("score")
    attempts = data.get("attempts", 1)
    details = data.get("details", {})

    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    try:
        score_val = float(score_val)
    except (TypeError, ValueError):
        return jsonify({"message": "score must be a number"}), 400
    try:
        attempts = int(attempts)
    except (TypeError, ValueError):
        return jsonify({"message": "attempts must be an integer"}), 400

    s = Score(
        user_id=current_user.id,
        set_name=set_name,
        mode=mode,
        score=score_val,
        attempts=attempts,
        details=details if isinstance(details, dict) else {"raw": details},
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"message": "saved", "score_id": s.id}), 201


@api_bp.route("/get_scores", methods=["GET"])
@token_required
def get_scores(current_user):
    """Get scores, with optional pagination; defaults unchanged."""
    set_name = request.args.get("set_name")
    try:
        limit = int(request.args.get("limit", 200))
    except (TypeError, ValueError):
        limit = 200
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    q = Score.query.filter_by(user_id=current_user.id)
    if set_name:
        q = q.filter_by(set_name=set_name)
    q = q.order_by(Score.timestamp.desc())

    rows = q.offset(offset).limit(limit).all()
    results = [{
        "id": s.id,
        "set_name": s.set_name,
        "mode": s.mode,
        "score": s.score,
        "attempts": s.attempts,
        "details": s.details,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
    } for s in rows]

    next_offset = offset + len(results) if len(results) == limit else None
    return jsonify({
        "scores": results,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset
    })


@api_bp.route("/my/scores", methods=["GET"])
@token_required
def my_scores(current_user):
    """Lightweight recent scores for dashboards."""
    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))

    rows = (Score.query
            .filter(Score.user_id == current_user.id)
            .order_by(Score.timestamp.desc())
            .limit(limit)
            .all())

    return jsonify([{
        "id": s.id,
        "set_name": s.set_name,
        "mode": s.mode,
        "score": s.score,
        "attempts": s.attempts,
        "details": s.details,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
    } for s in rows])

# ---------------------------
# Groups (per-user)
# ---------------------------

@api_bp.route("/my/groups", methods=["GET"])
@token_required
def my_groups(current_user):
    """List group memberships for the current user."""
    memberships = GroupMembership.query.filter_by(user_id=current_user.id).all()
    out = []
    for m in memberships:
        g = Group.query.get(m.group_id)
        out.append({
            "group_id": m.group_id,
            "group_name": g.name if g else None,
            "role": m.role,
        })
    return jsonify(out)

# ---------------------------
# Sets (per-user library)
# ---------------------------

@api_bp.route("/my/sets", methods=["GET"])
@token_required
def my_sets_get(current_user):
    """List sets attached to the current user."""
    rows = UserSet.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "set_name": r.set_name,
        "is_owner": bool(r.is_owner),
    } for r in rows])


@api_bp.route("/my/sets", methods=["POST"])
@token_required
def my_sets_add(current_user):
    """Attach a set to the current user's library (idempotent/upsert)."""
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    is_owner = bool(data.get("is_owner", False))
    if not set_name:
        return jsonify({"error": "Missing set_name"}), 400

    row = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not row:
        row = UserSet(user_id=current_user.id, set_name=set_name, is_owner=is_owner)
        db.session.add(row)
    else:
        # never silently downgrade ownership
        row.is_owner = is_owner or row.is_owner
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/my/sets/<path:set_name>", methods=["DELETE"])
@token_required
def my_sets_remove(current_user, set_name):
    """Detach a set from the current user's library."""
    set_name = (set_name or "").strip()
    row = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not row:
        return jsonify({"ok": True, "message": "Already not in library"})
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})

# ---------------------------
# Sets (available on disk)
# ---------------------------

@api_bp.route("/sets/available", methods=["GET"])
@token_required
def list_available_sets(current_user):
    """
    List all available sets from docs/sets (or SETS_DIR).
    Treat any *.json file directly under SETS_DIR as a set.
    """
    if not SETS_DIR.exists():
        return jsonify([])

    sets = []
    for p in sorted(SETS_DIR.glob("*.json")):
        sets.append({
            "name": p.stem,
            "filename": p.name,
        })
    return jsonify(sets)
