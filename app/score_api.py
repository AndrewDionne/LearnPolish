from __future__ import annotations
from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy import func
from .models import db, Score, PointsEvent, User
from .stats import build_stats_payload
# Use your existing auth decorator (_current_user/require_auth). Adjust imports if needed:
from .api import require_auth, _current_user  # if your auth helpers live elsewhere, import from there.

score_bp = Blueprint("score_api", __name__)

def _mode_norm(m: str | None) -> str:
    if not m: return "flashcards"
    m = m.lower()
    if m in ("practice","speak"): return "practice"
    if m in ("reading","read"):   return "reading"
    if m in ("listening","listen"): return "listening"
    return m

@score_bp.post("/submit_score")
@require_auth
def submit_score():
    u = _current_user()
    payload = request.get_json(silent=True) or {}
    set_name = (payload.get("set_name") or "").strip()
    mode     = _mode_norm(payload.get("mode"))
    score    = float(payload.get("score") or 0)
    attempts = int(payload.get("attempts") or 1)
    details  = payload.get("details") or {}
    # points (aka gold) can be provided as 'points' or 'gold'
    points   = int(payload.get("points") or payload.get("gold") or details.get("points") or 0)
    if points < 0: points = 0

    # 1) write Score (keeps top score history)
    s = Score(user_id=u.id, set_name=set_name, mode=mode, score=score, attempts=attempts, details=details)
    db.session.add(s)

    # 2) write PointsEvent (ledger)
    pe = PointsEvent(user_id=u.id, set_name=set_name, mode=mode, points=points, meta={"source":"finish","details":details})
    db.session.add(pe)

    db.session.commit()

    # 3) return updated stats (weekly/total/streak)
    stats = build_stats_payload(u)
    return jsonify({"ok": True, "score_id": s.id, "points_event_id": pe.id, "stats": stats}), 201

@score_bp.get("/my/stats")
@require_auth
def my_stats():
    u = _current_user()
    return jsonify(build_stats_payload(u))
