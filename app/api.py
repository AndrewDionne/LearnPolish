# app/api.py
from flask import Blueprint, request, jsonify
from pathlib import Path
from sqlalchemy import func
from datetime import datetime, timedelta, time as dtime
from collections import defaultdict
import json
import random, string
from shutil import rmtree
from .listening import create_listening_set
from .auth import token_required
from .models import db, Score, UserSet, GroupMembership, Group, Rating, User, SessionState

# Prefer canonical sets directory from sets_utils; fall back to docs/sets
try:
    from .sets_utils import SETS_DIR  # expected Path("docs/sets")
    from .sets_utils import regenerate_set_pages
except Exception:
    SETS_DIR = Path("docs/sets")
    # ensure later calls don't crash if sets_utils isn't available
    def regenerate_set_pages(_set_name: str):
        return None

api_bp = Blueprint("api", __name__)


# ---------------------------
# Helpers
# ---------------------------

def _cap_points(v):
    try:
        iv = int(v or 0)
    except Exception:
        iv = 0
    return max(0, min(100, iv))

def _week_start_utc(d=None):
    d = (d or datetime.utcnow().date())
    iso_year, iso_week, iso_weekday = d.isocalendar()
    monday = d - timedelta(days=iso_weekday - 1)
    return datetime.combine(monday, dtime.min)

def _safe_set(obj, attr, value):
    """Only set attribute if the model has it; return True/False."""
    if hasattr(obj, attr):
        setattr(obj, attr, value)
        return True
    return False

def _display_name(u: User):
    if not u:
        return "—"
    return getattr(u, "name", None) or (
        u.email.split("@")[0] if getattr(u, "email", None) else f"User {u.id}"
    )

def _path_for(mode: str, set_name: str) -> str:
    m = (mode or "").lower()
    if m in ("flashcards", "vocab", "learn", ""):
        return f"/flashcards/{set_name}/"
    if m in ("practice", "speak"):
        return f"/practice/{set_name}/"
    if m in ("reading", "read"):
        return f"/reading/{set_name}/"
    if m in ("listening", "listen"):
        return f"/listening/{set_name}/"
    return f"/flashcards/{set_name}/"

# ---------- Global sets: helpers ----------
ALLOWED_MODES = ("learn", "speak", "read", "listen")

def _type_from_modes(modes):
    m = set(modes or [])
    if m == {"listen"}: return "listening"
    if m == {"read"}:   return "reading"
    # learn/speak or mixed → show as flashcards in tables
    return "flashcards"

def _infer_modes_from_json(j):
    """
    Determine which activities this set supports.
    Priority:
      1) Explicit JSON: top-level "modes" OR meta.modes
      2) Structure-based inference:
         - "passages" → ["read"]
         - card with audio/audio_url → ["listen"]
      3) Default: ["learn","speak"]  (flashcard-like)
    We also enforce learn<->speak pairing if either is present.
    """
    meta = j.get("meta") or {}
    modes = j.get("modes") or meta.get("modes")
    if isinstance(modes, list) and modes:
        allow = {"learn", "speak", "read", "listen"}
        norm = [str(m).lower() for m in modes if str(m).lower() in allow]
        s = set(norm)
        if "learn" in s or "speak" in s:
            s.update({"learn", "speak"})
        ordered = [m for m in ["learn", "speak", "read", "listen"] if m in s]
        if ordered:
            return ordered

    if "passages" in j or "reading" in (meta.get("type") or "").lower():
        return ["read"]

    if any(isinstance(c, dict) and ("audio" in c or "audio_url" in c) for c in j.get("cards", [])):
        return ["listen"]

    return ["learn", "speak"]

def _count_items(j):
    """Return a reasonable item count for the set."""
    if isinstance(j.get("data"), list): return len(j["data"])
    if isinstance(j.get("cards"), list): return len(j["cards"])
    if isinstance(j.get("items"), list): return len(j["items"])
    if isinstance(j.get("passages"), list): return len(j["passages"])
    return 0


# ---------- Create/Update set: helpers ----------

def _valid_set_name(name: str) -> bool:
    if not name or len(name) > 200:
        return False
    # allow letters, digits, spaces, underscore, hyphen
    return all(ch.isalnum() or ch in " _-" for ch in name)

def _normalize_modes(modes_in):
    """Normalize + enforce learn<->speak pairing. Return list in stable order or None if invalid/empty."""
    if not isinstance(modes_in, (list, tuple)):
        return None
    allow = {"learn", "speak", "read", "listen"}
    wanted = [str(m).lower() for m in modes_in if str(m).lower() in allow]
    # dedupe preserving order
    seen, norm = set(), []
    for m in wanted:
        if m not in seen:
            seen.add(m)
            norm.append(m)
    if not norm:
        return None
    # enforce pairing
    if "learn" in seen or "speak" in seen:
        if "learn" not in seen:
            norm.insert(0, "learn"); seen.add("learn")
        if "speak" not in seen:
            norm.insert(1, "speak"); seen.add("speak")
    # canonical order
    order = ["learn", "speak", "read", "listen"]
    norm = [m for m in order if m in seen]
    return norm

def _body_for_set(set_name: str, modes: list[str], data: list):
    """Canonical on-disk shape for new sets."""
    # normalize modes: if either learn or speak is chosen, enforce both
    mset = set(modes or [])
    if "learn" in mset or "speak" in mset:
        mset.update({"learn", "speak"})
    clean = [m for m in ("learn","speak","read","listen") if m in mset]
    return {
        "name": set_name,
        "modes": clean,
        "data": data,
    }

# ---------- Delete set: helpers ----------

DOCS_ROOT = Path("docs")

def _safe_rmtree(p: Path):
    try:
        if p.exists():
            rmtree(p)
    except Exception:
        pass

def delete_set_files_everywhere(set_name: str):
    # main json
    try:
        (SETS_DIR / f"{set_name}.json").unlink(missing_ok=True)  # py3.8+: wrap try/except if needed
    except Exception:
        pass

    # generated pages/assets we create
    # flashcards + speak
    _safe_rmtree(DOCS_ROOT / "flashcards" / set_name)
    _safe_rmtree(DOCS_ROOT / "practice"   / set_name)
    # reading
    _safe_rmtree(DOCS_ROOT / "reading"    / set_name)
    # listening
    _safe_rmtree(DOCS_ROOT / "listening"  / set_name)
    # static (audio buckets)
    _safe_rmtree(DOCS_ROOT / "static"     / set_name)

# ---------------------------
# Account / profile
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
        "display_name": getattr(current_user, "display_name", None) if hasattr(current_user, "display_name") else None,
        "avatar_id": getattr(current_user, "avatar_id", None) if hasattr(current_user, "avatar_id") else None,
        "weekly_goal": getattr(current_user, "weekly_goal", None) if hasattr(current_user, "weekly_goal") else None,
        "is_admin": bool(getattr(current_user, "is_admin", False)),
        "created_at": created.isoformat() if created else None,
    })

@api_bp.route("/me", methods=["PATCH"])
@token_required
def me_patch(current_user):
    """
    Update lightweight profile fields (if columns exist).
    Body: { display_name?, name?, weekly_goal?, avatar_id?, ui_lang? }
    Unknown fields are ignored.
    """
    data = request.get_json(silent=True) or {}
    changed = False

    if "display_name" in data:
        changed |= _safe_set(current_user, "display_name", (data.get("display_name") or "").strip() or None)
        if hasattr(current_user, "name") and not getattr(current_user, "name", None):
            current_user.name = data.get("display_name") or None
            changed = True

    if "name" in data:
        changed |= _safe_set(current_user, "name", (data.get("name") or "").strip() or None)

    if "weekly_goal" in data:
        try:
            goal = int(data.get("weekly_goal"))
            goal = max(50, min(goal, 5000))
            changed |= _safe_set(current_user, "weekly_goal", goal)
        except Exception:
            pass

    if "avatar_id" in data:
        changed |= _safe_set(current_user, "avatar_id", (data.get("avatar_id") or "").strip() or None)

    if changed:
        db.session.commit()

    return jsonify({"ok": True})

@api_bp.route("/me", methods=["DELETE"])
@token_required
def me_delete(current_user):
    """
    Delete account (soft-safe). Removes Scores, Ratings, SessionState, UserSet,
    GroupMembership (not groups themselves), then User.
    """
    uid = current_user.id
    Score.query.filter_by(user_id=uid).delete()
    Rating.query.filter_by(user_id=uid).delete()
    SessionState.query.filter_by(user_id=uid).delete()
    UserSet.query.filter_by(user_id=uid).delete()
    GroupMembership.query.filter_by(user_id=uid).delete()
    db.session.delete(current_user)
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.route("/my/export", methods=["GET"])
@token_required
def my_export(current_user):
    """Export user-related data as JSON."""
    uid = current_user.id
    scores = [{
        "id": s.id, "set_name": s.set_name, "mode": s.mode, "score": s.score,
        "attempts": s.attempts, "details": s.details,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None
    } for s in Score.query.filter_by(user_id=uid).order_by(Score.timestamp.desc()).all()]
    ratings = [{
        "set_name": r.set_name, "stars": r.stars, "comment": r.comment,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None
    } for r in Rating.query.filter_by(user_id=uid).order_by(Rating.updated_at.desc()).all()]
    states = [{
        "set_name": s.set_name, "mode": s.mode, "progress": s.progress,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None
    } for s in SessionState.query.filter_by(user_id=uid).order_by(SessionState.updated_at.desc()).all()]
    sets_ = [{
        "set_name": u.set_name, "is_owner": bool(u.is_owner)
    } for u in UserSet.query.filter_by(user_id=uid).all()]
    groups = [{
        "group_id": m.group_id, "group_name": (Group.query.get(m.group_id).name if Group.query.get(m.group_id) else None),
        "role": m.role
    } for m in GroupMembership.query.filter_by(user_id=uid).all()]
    user = {
        "id": uid,
        "email": getattr(current_user, "email", None),
        "name": getattr(current_user, "name", None),
        "display_name": getattr(current_user, "display_name", None) if hasattr(current_user, "display_name") else None,
        "avatar_id": getattr(current_user, "avatar_id", None) if hasattr(current_user, "avatar_id") else None,
        "weekly_goal": getattr(current_user, "weekly_goal", None) if hasattr(current_user, "weekly_goal") else None,
        "created_at": getattr(current_user, "created_at", None).isoformat() if getattr(current_user, "created_at", None) else None,
    }
    return jsonify({"user": user, "scores": scores, "ratings": ratings, "session_state": states, "sets": sets_, "groups": groups})

@api_bp.route("/me/avatar_upload", methods=["POST"])
@token_required
def avatar_upload(current_user):
    """
    Optional (stub) upload endpoint. Saves nothing by default.
    If you later store files, persist and return {"avatar_id": "..."} or {"avatar_url": "..."}.
    """
    return jsonify({"ok": False, "message": "avatar uploads not configured"}), 501

# ---------------------------
# Scores (existing + alias)
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

@api_bp.route("/scores", methods=["POST"])
@token_required
def post_scores_alias(current_user):
    """Alias for cleaner front-end naming."""
    return submit_score(current_user)

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
        "id": s.id, "set_name": s.set_name, "mode": s.mode, "score": s.score, "attempts": s.attempts,
        "details": s.details, "timestamp": s.timestamp.isoformat() if s.timestamp else None
    } for s in rows]

    next_offset = offset + len(results) if len(results) == limit else None
    return jsonify({"scores": results, "limit": limit, "offset": offset, "next_offset": next_offset})

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
        "id": s.id, "set_name": s.set_name, "mode": s.mode, "score": s.score, "attempts": s.attempts,
        "details": s.details, "timestamp": s.timestamp.isoformat() if s.timestamp else None
    } for s in rows])

# ---------------------------
# Stats (streaks, weekly gold)
# ---------------------------

@api_bp.route("/my/stats", methods=["GET"])
@token_required
def my_stats(current_user):
    """
    Returns streaks and weekly gold (points capped 0..100).
    Adds: longest_streak, total_gold, and goal_points from User.weekly_goal if present.
    """
    since = datetime.utcnow() - timedelta(days=365)
    rows = (
        db.session.query(Score.timestamp, Score.score)
        .filter(Score.user_id == current_user.id, Score.timestamp >= since)
        .order_by(Score.timestamp.desc())
        .all()
    )

    # Streak in UTC dates
    days = sorted({ts.date() for ts, _ in rows}, reverse=True)
    today = datetime.utcnow().date()

    # current streak
    streak = 0
    d = today
    days_set = set(days)
    while d in days_set:
        streak += 1
        d = d - timedelta(days=1)

    # longest streak
    longest = 0
    if days:
        s = sorted(days)
        run = 1
        for i in range(1, len(s)):
            if (s[i] - s[i-1]).days == 1:
                run += 1
            else:
                if run > longest: longest = run
                run = 1
        if run > longest: longest = run

    # Weekly gold
    week_start = _week_start_utc(today)
    weekly_points = sum(_cap_points(sc) for ts, sc in rows if ts >= week_start)

    # Total gold (capped)
    total_gold = sum(_cap_points(sc) for _, sc in rows)

    # Goal points from user if available; fallback 500
    goal = 500
    if hasattr(current_user, "weekly_goal") and isinstance(getattr(current_user, "weekly_goal"), int):
        goal = max(50, min(int(getattr(current_user, "weekly_goal")), 5000))

    return jsonify({
        "streak_days": streak,
        "longest_streak": longest,
        "weekly_points": weekly_points,
        "weekly_gold": weekly_points,  # alias for UI convenience
        "goal_points": goal,
        "goal_gold": goal,             # alias
        "total_gold": total_gold
    })

# ---------------------------
# Groups
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
            "group_name": (g.name if g else None),
            "role": m.role,
        })
    return jsonify(out)

@api_bp.route("/groups", methods=["POST"])
@token_required
def create_group(current_user):
    """Create a group. Body: { name: str }. Generates join_code if the column exists."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name_required"}), 400

    g = Group(name=name, owner_id=current_user.id)

    if hasattr(Group, "join_code"):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            while db.session.query(Group.id).filter_by(join_code=code).first():
                code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        except Exception:
            pass
        if hasattr(g, "join_code"):
            g.join_code = code

    db.session.add(g)
    db.session.flush()
    if not GroupMembership.query.filter_by(user_id=current_user.id, group_id=g.id).first():
        db.session.add(GroupMembership(user_id=current_user.id, group_id=g.id, role="owner"))
    db.session.commit()

    resp = {"id": g.id, "name": g.name}
    if hasattr(g, "join_code"):
        resp["join_code"] = g.join_code
    return jsonify(resp), 201

@api_bp.route("/groups/join", methods=["POST"])
@token_required
def join_group(current_user):
    """Join a group via join code. Body: { code: 'ABCD1234' }."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "code_required"}), 400

    if not hasattr(Group, "join_code"):
        return jsonify({"error": "join_not_supported"}), 400

    g = Group.query.filter_by(join_code=code).first()
    if not g:
        return jsonify({"error": "invalid_code"}), 404

    existing = GroupMembership.query.filter_by(user_id=current_user.id, group_id=g.id).first()
    if not existing:
        db.session.add(GroupMembership(user_id=current_user.id, group_id=g.id, role="member"))
        db.session.commit()
    return jsonify({"ok": True, "group_id": g.id, "group_name": g.name})

@api_bp.route("/groups/<int:group_id>/leave", methods=["DELETE"])
@token_required
def leave_group(current_user, group_id):
    """Leave a group. If this was the last member, delete the group.
       If the owner leaves and others remain, transfer ownership."""
    m = GroupMembership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not m:
        return jsonify({"ok": True, "message": "not a member"})

    owner_left = (m.role or "").lower() == "owner"
    db.session.delete(m)
    db.session.flush()

    remaining = GroupMembership.query.filter_by(group_id=group_id).all()
    g = Group.query.get(group_id)

    if not remaining:
        if g:
            db.session.delete(g)  # no members left -> delete group
        db.session.commit()
        return jsonify({"ok": True, "deleted": True})

    # Transfer ownership if needed
    if owner_left and g:
        # Pick any remaining member as the new owner (first in list)
        new_owner = remaining[0]
        g.owner_id = new_owner.user_id
        new_owner.role = "owner"

    db.session.commit()
    return jsonify({"ok": True, "deleted": False})


@api_bp.route("/groups/<int:group_id>/invite_code", methods=["GET"])
@token_required
def group_invite_code(current_user, group_id):
    """Return invite code if supported."""
    g = Group.query.get(group_id)
    if not g:
        return jsonify({"error": "not_found"}), 404
    if not hasattr(g, "join_code"):
        return jsonify({"error": "join_not_supported"}), 400
    return jsonify({"code": g.join_code or ""})

@api_bp.route("/groups/<int:group_id>/recent_activity", methods=["GET"])
@token_required
def group_recent_activity(current_user, group_id):
    """
    Recent activity for members in a group.
    Query: ?limit=50
    Returns: [{timestamp, user_id, user_name, set_name, mode, score}, ...]
    """
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except Exception:
        limit = 50

    # Ensure the requester is in the group
    member = GroupMembership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not member:
        return jsonify({"error": "forbidden"}), 403

    member_ids = [m.user_id for m in GroupMembership.query.filter_by(group_id=group_id).all()]
    q = (Score.query
         .filter(Score.user_id.in_(member_ids))
         .order_by(Score.timestamp.desc())
         .limit(limit))
    rows = q.all()

    users = {u.id: u for u in User.query.filter(User.id.in_(member_ids)).all()}
    out = []
    for s in rows:
        u = users.get(s.user_id)
        out.append({
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "user_id": s.user_id,
            "user_name": _display_name(u),
            "set_name": s.set_name,
            "mode": s.mode,
            "score": s.score,
        })
    return jsonify(out)

@api_bp.route("/my/groups/recent", methods=["GET"])
@token_required
def my_groups_recent(current_user):
    """Union of recent activity across all groups the user is in."""
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except Exception:
        limit = 50

    group_ids = [m.group_id for m in GroupMembership.query.filter_by(user_id=current_user.id).all()]
    if not group_ids:
        return jsonify([])

    member_ids = [m.user_id for m in GroupMembership.query.filter(GroupMembership.group_id.in_(group_ids)).all()]
    if not member_ids:
        return jsonify([])

    q = (Score.query
         .filter(Score.user_id.in_(member_ids))
         .order_by(Score.timestamp.desc())
         .limit(limit))
    rows = q.all()
    users = {u.id: u for u in User.query.filter(User.id.in_(member_ids)).all()}

    out = []
    for s in rows:
        u = users.get(s.user_id)
        out.append({
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "user_id": s.user_id,
            "user_name": _display_name(u),
            "set_name": s.set_name,
            "mode": s.mode,
            "score": s.score,
        })
    return jsonify(out)

@api_bp.route("/groups/<int:group_id>/leaderboard", methods=["GET"])
@token_required
def group_leaderboard(current_user, group_id):
    """Weekly or all-time leaderboard for a group. ?window=week|all (default week)."""
    window = (request.args.get("window") or "week").lower()
    since_dt = None
    if window == "week":
        since_dt = _week_start_utc()

    # requester must be a member
    if not GroupMembership.query.filter_by(user_id=current_user.id, group_id=group_id).first():
        return jsonify({"error": "forbidden"}), 403

    q = (
        db.session.query(Score.user_id, Score.timestamp, Score.score)
        .join(GroupMembership, GroupMembership.user_id == Score.user_id)
        .filter(GroupMembership.group_id == group_id)
    )
    if since_dt:
        q = q.filter(Score.timestamp >= since_dt)

    rows = q.all()
    totals = defaultdict(int)
    for user_id, _ts, sc in rows:
        totals[user_id] += _cap_points(sc)

    if not totals:
        return jsonify({"leaderboard": []})

    users = {u.id: u for u in db.session.query(User).filter(User.id.in_(list(totals.keys()))).all()}

    leaderboard = []
    for uid, points in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        u = users.get(uid)
        leaderboard.append({"user_id": uid, "name": _display_name(u), "points": points})

    return jsonify({"leaderboard": leaderboard})

# ---------------------------
# Sets (library + global + create/update)
# ---------------------------

@api_bp.route("/my/sets", methods=["GET"])
@token_required
def my_sets_get(current_user):
    """Return [{set_name, is_owner, modes, type, count}] for the user."""
    rows = UserSet.query.filter_by(user_id=current_user.id).all()
    out = []
    for r in rows:
        modes = None
        count = 0
        typ = None

        p = SETS_DIR / f"{r.set_name}.json"
        if p.exists():
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(j, dict):
                    # infer modes (supports top-level + meta.modes + structure)
                    modes = _infer_modes_from_json(j) or None
                    # DRY count (data/cards/passages/items)
                    count = _count_items(j)
                elif isinstance(j, list):
                    # legacy array
                    modes = ["learn", "speak"]
                    count = len(j)
            except Exception:
                pass

        # Provide a type only if we know the modes; else leave None ("unknown" in UI)
        if modes:
            typ = _type_from_modes(modes)

        out.append({
            "set_name": r.set_name,
            "is_owner": bool(r.is_owner),
            "modes": modes,
            "type": typ,
            "count": count,
        })
    return jsonify(out)


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

@api_bp.route("/sets/available", methods=["GET"])
@token_required
def list_available_sets(current_user):
    """
    Auth-only list of all available sets (bare-minimum).
    Treat any *.json file directly under SETS_DIR as a set.
    """
    if not SETS_DIR.exists():
        return jsonify([])
    sets = [{"name": p.stem, "filename": p.name} for p in sorted(SETS_DIR.glob("*.json"))]
    return jsonify(sets)

# ---------- Global sets: public, enriched (single canonical route) ----------

@api_bp.route("/global_sets", methods=["GET"])
def global_sets_index():
    """
    Public list with metadata the UI needs.
    Prefers explicit 'modes' saved in the set file; falls back only for legacy sets.
    Returns: [{ name, filename, count, modes, type }]
    """
    out = []
    if not SETS_DIR.exists():
        return jsonify(out)

    for p in sorted(SETS_DIR.glob("*.json")):
        name = p.stem
        modes = ["learn", "speak"]  # safe default for legacy
        count = 0

        try:
            j = json.loads(p.read_text(encoding="utf-8"))

            if isinstance(j, dict):
                name = j.get("name") or name
                # infer modes (handles top-level, meta.modes, structure)
                modes = _infer_modes_from_json(j) or modes
                # DRY count
                count = _count_items(j)

            elif isinstance(j, list):
                # very old: top-level array of cards
                count = len(j)

        except Exception:
            # keep defaults if file is malformed
            pass

        out.append({
            "name": name,
            "filename": p.name,
            "count": count,
            "modes": modes,
            "type": _type_from_modes(modes),
        })

    return jsonify(out)

# ---------- Create set ----------

@api_bp.route("/create_set", methods=["POST"])
@token_required
def create_set(current_user):
    """
    Body:
      { set_name: str, data: [...],
        modes?: ["learn","speak","read","listen"],
        set_type?: "learn"|"reading"|"listening" (legacy) }
    Rules:
      - No default; if modes omitted, set_type must be present.
      - If 'learn' or 'speak' present, both are enforced.
    """
    payload = request.get_json(silent=True) or {}
    set_name = (payload.get("set_name") or "").strip()
    data = payload.get("data")

    if not _valid_set_name(set_name):
        return jsonify({"error": "invalid_set_name"}), 400
    if not isinstance(data, list) or not data:
        return jsonify({"error": "data must be a non-empty array"}), 400

    modes = _normalize_modes(payload.get("modes"))
    if not modes:
        st = (payload.get("set_type") or "").lower()
        if st in ("flashcards", "learn"):
            modes = ["learn", "speak"]
        elif st in ("reading", "read"):
            modes = ["read"]
        elif st in ("listening", "listen"):
            modes = ["listen"]
        else:
            return jsonify({"error": "modes_or_valid_set_type_required"}), 400

    SETS_DIR.mkdir(parents=True, exist_ok=True)
    path = SETS_DIR / f"{set_name}.json"
    if path.exists():
        return jsonify({"error": "set_already_exists"}), 409

    body = _body_for_set(set_name, modes, data)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    # Library attach (owner)
    if not UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first():
        db.session.add(UserSet(user_id=current_user.id, set_name=set_name, is_owner=True))
        db.session.commit()

    # ---- NEW: generate static assets (audio + HTML) for the modes implied by data ----
    warnings = []
    try:
        # This will:
        # - Generate flashcard/practice audio via gTTS into docs/static/<set>/audio/...
        # - Generate reading audio via gTTS into docs/static/<set>/reading/...
        # - Regenerate HTML pages for flashcards/practice/reading (via MODE_GENERATORS)
        # Listening is handled separately in app/listening.py and isn’t part of MODE_GENERATORS.
        regenerate_set_pages(set_name)
    except Exception as e:
        warnings.append(f"regenerate_failed: {e}")
        
    # Generate Listening artifacts if requested
    try:
        if "listen" in modes:
            # Pass the same 'data' shape you received. The helper will normalize
            # and write MP3s to docs/static/<set>/listening/ and page to docs/listening/<set>/.
            create_listening_set(set_name, data)

    except Exception as e:
        warnings.append(f"listening_generate_failed: {e}")

    resp = {"ok": True, "name": set_name, "modes": modes}
    if warnings:
        resp["warnings"] = warnings
    return jsonify(resp), 201

# ---------- Update set ----------

@api_bp.route("/update_set", methods=["POST", "PUT", "PATCH"])
@token_required
def update_set(current_user):
    """
    Body:
      { set_name: str,
        data?: [...],           # replaces cards/passages entirely if provided
        modes?: ["learn","speak","read","listen"] }  # optional
    Guard: must be owner (UserSet.is_owner) or admin.
    """
    payload = request.get_json(silent=True) or {}
    set_name = (payload.get("set_name") or "").strip()
    if not _valid_set_name(set_name):
        return jsonify({"error": "invalid_set_name"}), 400

    path = SETS_DIR / f"{set_name}.json"
    if not path.exists():
        return jsonify({"error": "not_found"}), 404

    is_admin = bool(getattr(current_user, "is_admin", False))
    owner_row = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not is_admin and not (owner_row and owner_row.is_owner):
        return jsonify({"error": "forbidden"}), 403

    try:
        j = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        j = {}

    # Modes (optional)
    if "modes" in payload:
        modes = _normalize_modes(payload.get("modes"))
        if not modes:
            return jsonify({"error": "invalid_modes"}), 400
        j.setdefault("meta", {})
        j["meta"]["modes"] = modes
        j["modes"] = modes  # keep top-level in sync

    # Data (optional → full replace)
    if "data" in payload:
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return jsonify({"error": "data must be a non-empty array"}), 400
        # decide which key to write based on (possibly updated) modes
        modes_now = _infer_modes_from_json(j)
        if "read" in modes_now and len(modes_now) == 1:
            j.pop("cards", None)
            j["passages"] = data
        else:
            j.pop("passages", None)
            j["cards"] = data

    # Ensure name is present & consistent
    j["name"] = j.get("name") or set_name

    path.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")

    warns = []

    # Rebuild other modes’ audio/pages
    try:
        regenerate_set_pages(set_name)
    except Exception as e:
        warns.append(f"regenerate_failed: {e}")

    # Rebuild Listening if this set uses it
    try:
        modes_now = _infer_modes_from_json(j)
        if "listen" in modes_now:
            # For listening, items live in "cards" when not purely reading
            items = j.get("cards") or j.get("items") or []
            create_listening_set(set_name, items)
    except Exception as e:
        warns.append(f"listening_generate_failed: {e}")

    return jsonify({
        "ok": True,
        "name": set_name,
        "modes": _infer_modes_from_json(j),
        "warnings": warns or None
    })


# ---------------------------
# Ratings
# ---------------------------

@api_bp.route("/sets/rate", methods=["POST"])
@token_required
def rate_set(current_user):
    """Upsert the current user's rating for a set."""
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    stars = data.get("stars")
    comment = data.get("comment", None)

    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        return jsonify({"message": "stars must be an integer 1..5"}), 400
    if stars < 1 or stars > 5:
        return jsonify({"message": "stars must be between 1 and 5"}), 400

    row = Rating.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if row:
        row.stars = stars
        row.comment = comment
    else:
        row = Rating(user_id=current_user.id, set_name=set_name, stars=stars, comment=comment)
        db.session.add(row)
    db.session.commit()

    return jsonify({
        "ok": True,
        "set_name": set_name,
        "stars": row.stars,
        "comment": row.comment,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }), 200

@api_bp.route("/sets/ratings", methods=["GET"])
def set_ratings_aggregate():
    """
    If ?set=<set_name> provided: return single aggregate.
    (Back-compat for existing clients.)
    """
    set_name = (request.args.get("set") or "").strip()
    if not set_name:
        return jsonify({"message": "set query param is required"}), 400

    agg = (db.session.query(func.count(Rating.id), func.avg(Rating.stars))
           .filter(Rating.set_name == set_name)
           .first())
    count = int(agg[0] or 0)
    avg = float(agg[1]) if agg and agg[1] is not None else None

    return jsonify({"set_name": set_name, "count": count, "avg_stars": round(avg, 3) if avg is not None else None})

@api_bp.route("/sets/ratings/batch", methods=["POST"])
def set_ratings_batch():
    """
    Body: { "sets": ["name1","name2", ...] }  (max ~200)
    Returns: [{ set_name, count, avg_stars }, ...] preserving input order.
    """
    data = request.get_json(silent=True) or {}
    names = data.get("sets")
    if not isinstance(names, list) or not names:
        return jsonify({"message": "sets must be a non-empty array"}), 400

    norm, seen = [], set()
    for s in names:
        n = (s or "").strip()
        if not n or n in seen:
            continue
        seen.add(n)
        norm.append(n)
        if len(norm) >= 200:
            break

    if not norm:
        return jsonify([])

    rows = (db.session.query(Rating.set_name, func.count(Rating.id), func.avg(Rating.stars))
            .filter(Rating.set_name.in_(norm))
            .group_by(Rating.set_name)
            .all())
    agg_map = {name: {"set_name": name, "count": 0, "avg_stars": None} for name in norm}
    for set_name, cnt, avg in rows:
        agg_map[set_name] = {"set_name": set_name, "count": int(cnt or 0), "avg_stars": round(float(avg), 3) if avg is not None else None}
    return jsonify([agg_map[n] for n in norm])

@api_bp.route("/sets/ratings/averages", methods=["GET"])
def set_ratings_averages():
    """
    Lightweight list of averages for ALL sets that have at least one rating.
    Returns: [{ set_name, avg: number, count }, ...]
    """
    rows = (db.session.query(Rating.set_name, func.count(Rating.id), func.avg(Rating.stars))
            .group_by(Rating.set_name)
            .all())
    out = []
    for set_name, cnt, avg in rows:
        out.append({"set_name": set_name, "count": int(cnt or 0), "avg": round(float(avg), 3) if avg is not None else None})
    return jsonify(out)

@api_bp.route("/my/ratings", methods=["GET"])
@token_required
def my_ratings(current_user):
    """
    Get your rating(s). Optional filter: ?set=<set_name>
    Returns: list of { set_name, stars, comment, updated_at }
    """
    set_name = (request.args.get("set") or "").strip()
    q = Rating.query.filter_by(user_id=current_user.id)
    if set_name:
        q = q.filter_by(set_name=set_name)
    rows = q.order_by(Rating.updated_at.desc()).limit(200).all()
    return jsonify([{
        "set_name": r.set_name,
        "stars": r.stars,
        "comment": r.comment,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    } for r in rows])

# ---------------------------
# Session state (resume)
# ---------------------------

@api_bp.route("/session_state", methods=["GET"])
@token_required
def get_session_state(current_user):
    """Query: ?set=<name>&mode=<mode> → single saved state."""
    set_name = (request.args.get("set") or "").strip()
    mode = (request.args.get("mode") or "").strip().lower()
    if not set_name or not mode:
        return jsonify({"message": "set and mode are required"}), 400

    row = SessionState.query.filter_by(user_id=current_user.id, set_name=set_name, mode=mode).first()
    if not row:
        return jsonify({"message": "not found"}), 404

    return jsonify({
        "set_name": row.set_name,
        "mode": row.mode,
        "progress": row.progress or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    })

@api_bp.route("/session_state/my", methods=["GET"])
@token_required
def list_session_states(current_user):
    """
    Returns recent session states for the user to power the Continue button.
    Response: [{ set_name, mode, progress, updated_at, href }, ...] newest first.
    """
    rows = (SessionState.query
            .filter_by(user_id=current_user.id)
            .order_by(SessionState.updated_at.desc())
            .limit(20)
            .all())
    return jsonify([{
        "set_name": r.set_name,
        "mode": r.mode,
        "progress": r.progress or {},
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "href": _path_for(r.mode, r.set_name),
    } for r in rows])

@api_bp.route("/session_state", methods=["POST", "PUT"])
@token_required
def upsert_session_state(current_user):
    """Body: { set_name, mode, progress: {...} } upsert."""
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    mode = (data.get("mode") or "").strip().lower()
    progress = data.get("progress") or {}
    if not set_name or not mode:
        return jsonify({"message": "set_name and mode are required"}), 400
    if not isinstance(progress, dict):
        return jsonify({"message": "progress must be an object"}), 400

    row = SessionState.query.filter_by(user_id=current_user.id, set_name=set_name, mode=mode).first()
    if not row:
        row = SessionState(user_id=current_user.id, set_name=set_name, mode=mode, progress=progress)
        db.session.add(row)
    else:
        row.progress = progress
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.route("/session_state/complete", methods=["POST"])
@token_required
def complete_session_state(current_user):
    """Body: { set_name, mode } → delete saved state."""
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    mode = (data.get("mode") or "").strip().lower()
    if not set_name or not mode:
        return jsonify({"message": "set_name and mode are required"}), 400

    SessionState.query.filter_by(user_id=current_user.id, set_name=set_name, mode=mode).delete()
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.route("/my/continue", methods=["GET"])
@token_required
def my_continue(current_user):
    """Return most-recent session state for the Continue button."""
    row = (SessionState.query
           .filter_by(user_id=current_user.id)
           .order_by(SessionState.updated_at.desc())
           .first())
    if not row:
        return jsonify({"found": False})
    return jsonify({
        "found": True,
        "set_name": row.set_name,
        "mode": row.mode,
        "progress": row.progress or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "href": _path_for(row.mode, row.set_name),
    })

# ---------------------------
# Challenges (optional, graceful)
# ---------------------------

@api_bp.route("/my/challenges", methods=["GET"])
@token_required
def my_challenges(current_user):
    """
    Optional endpoint used by Dashboard. If you don't want to persist,
    we just synthesize a few based on recent activity.
    """
    uid = current_user.id
    week_start = _week_start_utc()
    weekly = sum(_cap_points(s.score) for s in Score.query.filter(Score.user_id == uid, Score.timestamp >= week_start).all())
    out = [
        {"id":"d1","scope":"daily","title":"Complete 1 Learn session","reward":10,"progress":0,"goal":1,"done":False,"cta_href":"./learn.html"},
        {"id":"w1","scope":"weekly","title":"Earn 300 gold this week","reward":60,"progress":weekly,"goal":300,"done":weekly>=300,"cta_href":"./index.html"},
        {"id":"m1","scope":"monthly","title":"Master 3 collections","reward":200,"progress":0,"goal":3,"done":False,"cta_href":"./manage_sets/"},
    ]
    return jsonify(out)

@api_bp.route("/my/challenges/complete", methods=["POST"])
@token_required
def my_challenges_complete(current_user):
    """No-op success so the UI can show 'Claimed' without errors."""
    return jsonify({"ok": True})
