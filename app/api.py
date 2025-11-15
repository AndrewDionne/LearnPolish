# app/api.py
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
from datetime import datetime, timedelta, time as dtime
from collections import defaultdict
from shutil import rmtree
from pathlib import Path
import os, json, re, jwt, random, string
from urllib.parse import quote
from sqlalchemy.exc import OperationalError

from .auth import token_required
from .models import db, Score, UserSet, GroupMembership, Group, Rating, User, SessionState
from .emailer import send_email
from .listening import create_listening_set
# Project paths & helpers
from .constants import SETS_DIR, PAGES_DIR, STATIC_DIR
from .sets_utils import regenerate_set_pages, sanitize_filename, build_all_mode_indexes, rebuild_set_modes_map

# Publishing is handled centrally in sets_api (GITHUB_REPO_SLUG).
# This module delegates create routes to sets_api to avoid divergence.

api_bp = Blueprint("api", __name__)

@api_bp.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat()})

# ---------------------------
# Helpers
# ---------------------------
def safe_commit():
    """Commit once; on DB disconnect/idle-ssl errors, rollback and retry once."""
    try:
        db.session.commit()
    except OperationalError as e:
        db.session.rollback()
        current_app.logger.warning("Commit failed (retrying once): %s", e)
        try:
            db.session.commit()
        except Exception as e2:
            db.session.rollback()
            raise e2

def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def _call_view(fn, *args, **kwargs):
    """Invoke the original view function, bypassing stacked @token_required wrappers."""
    target = getattr(fn, "__wrapped__", fn)
    return target(*args, **kwargs)

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

def _invite_subject(group_name: str) -> str:
    return f"You’re invited to join {group_name} on Path to POLISH"

def _invite_bodies(group_name: str, link: str, code: str, sender_name: str) -> tuple[str, str]:
    text = f"""Hi,

You’ve been invited to join {group_name} on Path to POLISH — a simple app where we learn Polish together.

Join with this link:
{link}

If asked for a code, enter: {code}

What to expect:
• Shared sets we’re learning
• Listening/reading/speaking practice
• Group progress and weekly goals

Getting started:
1) Open the link on your phone (Safari/Chrome).
2) Sign in or create an account.
3) You’ll land in our group automatically.

Questions? Just reply to this email.

— {sender_name}
"""

    html = f"""<html>
  <body style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial; line-height:1.6; color:#0c0f14;">
    <p>Hi,</p>
    <p>You’ve been invited to join <b>{group_name}</b> on <i>Path to POLISH</i> — a simple app where we learn Polish together.</p>

    <p style="margin:20px 0;">
      <a href="{link}" style="display:inline-block;padding:12px 18px;background:#2d6cdf;color:#fff;text-decoration:none;border-radius:10px;">Join {group_name}</a>
    </p>

    <p>If asked for a code, enter: <b>{code}</b></p>

    <p><b>What to expect:</b><br>
      • Shared sets we’re learning<br>
      • Listening/reading/speaking practice<br>
      • Group progress and weekly goals
    </p>

    <p><b>Getting started:</b><br>
      1) Open the link on your phone (Safari/Chrome).<br>
      2) Sign in or create an account.<br>
      3) You’ll land in our group automatically.
    </p>

  </body>
</html>"""
    return text, html

def make_reset_token(user_id: int, minutes: int = 30) -> str:
    payload = {
        "uid": user_id,
        "typ": "pwdreset",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
    }
    secret = current_app.config.get("SECRET_KEY") or os.environ["SECRET_KEY"]
    return jwt.encode(payload, secret, algorithm="HS256")

def reset_email_bodies(link: str) -> tuple[str, str]:
    text = f"""Hi,

We received a request to reset your Path to POLISH password.

Reset your password using this link:
{link}

If you didn’t request this, you can safely ignore this email.

Thanks,
Path to POLISH Support
"""
    html = f"""<html><body>
<p>Hi,</p>
<p>We received a request to reset your <b>Path to POLISH</b> password.</p>
<p><b>Reset your password using this link:</b><br>
<a href="{link}">{link}</a></p>
<p>If you didn’t request this, you can safely ignore this email.</p>
<p>Thanks,<br>Path to POLISH Support</p>
</body></html>"""
    return text, html

# ---------- Global sets: helpers ----------
ALLOWED_MODES = ("learn", "speak", "read", "listen")

def _type_from_modes(modes):
    m = set(modes or [])
    if m == {"listen"}: return "listening"
    if m == {"read"}:   return "reading"
    # learn/speak or mixed → show as flashcards in tables
    return "flashcards"

def _extract_modes_from_json(j):
    """
    Read explicit modes only (no inference). Enforce learn<->speak pairing
    and canonical order.
    """
    meta = j.get("meta") or {}
    raw = j.get("modes") or meta.get("modes") or []
    if not isinstance(raw, list):
        return []
    allow = {"learn", "speak", "read", "listen"}
    seen, out = set(), []
    for m in raw:
        s = str(m).lower().strip()
        if s in allow and s not in seen:
            seen.add(s); out.append(s)
    if "learn" in seen or "speak" in seen:
        if "learn" not in seen: out.insert(0, "learn"); seen.add("learn")
        if "speak" not in seen: out.insert(1, "speak"); seen.add("speak")
    order = ["learn", "speak", "read", "listen"]
    return [m for m in order if m in seen]

def _body_for_set(set_name: str, modes: list[str], data: list[dict]) -> dict:
    """
    Canonical wrapper shape:
      - read-only → passages:[...]
      - else      → cards:[...]
    Mirror modes at top-level and in meta.
    """
    # enforce pairing + canonical order
    ms = set(str(x).lower() for x in (modes or []))
    if "learn" in ms or "speak" in ms:
        ms.update({"learn", "speak"})
    ordered = [m for m in ["learn", "speak", "read", "listen"] if m in ms]

    is_read_only = set(ordered) == {"read"} or ordered == ["read"]
    body = {"name": set_name, "modes": ordered, "meta": {"modes": ordered}}
    if is_read_only:
        body["passages"] = data
    else:
        body["cards"] = data
    return body

def _count_items(j):
    if isinstance(j.get("cards"), list):     return len(j["cards"])
    if isinstance(j.get("passages"), list):  return len(j["passages"])
    if isinstance(j.get("items"), list):     return len(j["items"])   # legacy
    if isinstance(j.get("data"), list):      return len(j["data"])    # legacy
    return 0

# ---------- Create/Update set: helpers ----------

def _valid_set_name(name: str) -> bool:
    if not name or len(name) > 200:
        return False
    # allow letters, digits, spaces, underscore, hyphen
    return all(ch.isalnum() or ch in " _-" for ch in name)

def _normalize_modes(modes_in):
    """Normalize + enforce learn<->speak pairing; stable order."""
    if not isinstance(modes_in, (list, tuple)):
        return None
    allow = {"learn", "speak", "read", "listen"}
    wanted = [str(m).lower().strip() for m in modes_in if str(m).lower().strip() in allow]
    seen, norm = set(), []
    for m in wanted:
        if m not in seen:
            seen.add(m); norm.append(m)
    if not norm:
        return None
    if "learn" in seen or "speak" in seen:
        if "learn" not in seen:
            norm.insert(0, "learn"); seen.add("learn")
        if "speak" not in seen:
            norm.insert(1, "speak"); seen.add("speak")
    order = ["learn", "speak", "read", "listen"]
    return [m for m in order if m in seen]

# ---------- Delete set: helpers ----------

DOCS_ROOT = PAGES_DIR

def _safe_rmtree(p: Path):
    try:
        if p.exists():
            rmtree(p)
    except Exception:
        pass

def delete_set_files_everywhere(set_name: str):
    try:
        (SETS_DIR / f"{set_name}.json").unlink(missing_ok=True)
    except Exception:
        pass
    _safe_rmtree(DOCS_ROOT / "flashcards" / set_name)
    _safe_rmtree(DOCS_ROOT / "practice"   / set_name)
    _safe_rmtree(DOCS_ROOT / "reading"    / set_name)
    _safe_rmtree(DOCS_ROOT / "listening"  / set_name)
    _safe_rmtree(DOCS_ROOT / "static"     / set_name)

# ---------------------------
# Account / profile
# ---------------------------

@api_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
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
        safe_commit()

    return jsonify({"ok": True})

@api_bp.route("/me", methods=["DELETE"])
@token_required
def me_delete(current_user):
    uid = current_user.id
    Score.query.filter_by(user_id=uid).delete()
    Rating.query.filter_by(user_id=uid).delete()
    SessionState.query.filter_by(user_id=uid).delete()
    UserSet.query.filter_by(user_id=uid).delete()
    GroupMembership.query.filter_by(user_id=uid).delete()
    db.session.delete(current_user)
    safe_commit()
    return jsonify({"ok": True})

@api_bp.route("/my/export", methods=["GET"])
@token_required
def my_export(current_user):
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
    return jsonify({"ok": False, "message": "avatar uploads not configured"}), 501

# ---------------------------
# Scores (existing + alias)
# ---------------------------

@api_bp.route("/submit_score", methods=["POST"])
@token_required
def submit_score(current_user):
    """
    Store one run (set + mode) + award gold.

    Flashcards gold logic:
      - +10 gold for first-ever run on a set (per user+set+mode)
      - +1 gold per card that has *ever* reached 100% (permanent unlock)
      - Weekly perfect bonus: if the set is fully perfect in a run,
        grant +n100 gold once per week for that set+mode.

    Other modes:
      - Keep prior behaviour (score/points-based with a per-set cap).
    """
    data = request.get_json(silent=True) or {}

    set_name = (data.get("set_name") or "").strip()
    mode = (data.get("mode") or "practice").strip().lower()

    # Normalise modes to a small set
    if mode in ("learn", "vocab", "flashcard", "flashcards", ""):
        mode = "flashcards"
    elif mode in ("speak", "practice"):
        mode = "practice"
    elif mode in ("read", "reading"):
        mode = "reading"
    elif mode in ("listen", "listening"):
        mode = "listening"
    else:
        mode = "flashcards"

    score_val = data.get("score")
    attempts = data.get("attempts", 1)
    details = data.get("details", {}) or {}
    gold_in = data.get("gold", None)

    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    if score_val is None:
        return jsonify({"message": "score is required"}), 400

    try:
        score_val = float(score_val)
    except (TypeError, ValueError):
        return jsonify({"message": "score must be a number"}), 400

    try:
        attempts = int(attempts)
    except (TypeError, ValueError):
        attempts = 1

    if not isinstance(details, dict):
        details = {"raw": str(details)[:2000]}

    # ---- details size cap (~50 KB) ----
    def _cap_details(obj, cap=50_000):
        try:
            s = json.dumps(obj, ensure_ascii=False)
            if len(s) <= cap:
                return obj
        except Exception:
            return {"raw": "unserializable"}

        if isinstance(obj, dict):
            trimmed = dict(obj)
            # Common "big" fields get trimmed
            for key in ("perDialogueLog", "items", "per", "cards", "segments"):
                if isinstance(trimmed.get(key), list):
                    trimmed[key] = trimmed[key][:200]
            try:
                s = json.dumps(trimmed, ensure_ascii=False)
                if len(s) <= cap:
                    return trimmed
            except Exception:
                pass
        return {"truncated": True}

    details = _cap_details(details)

    run_gold_awarded: float | None = None
    run_gold_raw: float | None = None

    # ---------------- FLASHCARDS GOLD ENGINE ----------------
    if mode == "flashcards":
        # We expect the frontend to send:
        #   details.total  -> totalCards
        #   details.n100   -> cards at 100% this run
        try:
            total_cards = int(details.get("total") or 0)
        except (TypeError, ValueError):
            total_cards = 0

        try:
            n100 = int(details.get("n100") or 0)
        except (TypeError, ValueError):
            n100 = 0

        # All past runs for this user+set+mode
        existing_rows = (
            Score.query
            .filter(
                Score.user_id == current_user.id,
                Score.set_name == set_name,
                Score.mode == mode,
            )
            .order_by(Score.timestamp.asc())
            .all()
        )
        first_time = len(existing_rows) == 0

        # Highest n100 we've ever seen before on this set+mode
        prev_max_n100 = 0
        for r in existing_rows:
            d = r.details or {}
            if isinstance(d, dict):
                try:
                    v = int(d.get("n100") or 0)
                except (TypeError, ValueError):
                    v = 0
                if v > prev_max_n100:
                    prev_max_n100 = v

        new_perfect_cards = max(0, n100 - prev_max_n100)

        # 10 gold the first time only (ever for this set+mode)
        first_time_bonus = 10.0 if first_time else 0.0

        # 1 gold per newly-perfected card
        per_card_gold = float(new_perfect_cards)

        # Weekly perfect-set bonus: +n100 once per week per set+mode
        perfect_run = bool(
            score_val >= 100.0 or (total_cards > 0 and n100 >= total_cards)
        )
        perfect_bonus = 0.0
        if perfect_run and total_cards > 0 and n100 >= total_cards:
            today = datetime.utcnow().date()
            week_start = _week_start_utc(today)
            weekly_rows = (
                Score.query
                .filter(
                    Score.user_id == current_user.id,
                    Score.set_name == set_name,
                    Score.mode == mode,
                    Score.timestamp >= week_start,
                )
                .all()
            )
            weekly_bonus_used = False
            for r in weekly_rows:
                d = r.details or {}
                if isinstance(d, dict):
                    try:
                        if float(d.get("perfect_bonus") or 0) > 0:
                            weekly_bonus_used = True
                            break
                    except (TypeError, ValueError):
                        continue

            if not weekly_bonus_used:
                # +1 per card this run as a weekly perfect bonus
                perfect_bonus = float(n100 or 0)

        run_gold_awarded = max(0.0, first_time_bonus + per_card_gold + perfect_bonus)
        run_gold_raw = run_gold_awarded

        # Annotate details for later summaries
        if isinstance(details, dict):
            details.setdefault("total", total_cards)
            details.setdefault("n100", n100)
            details["first_time_bonus"] = first_time_bonus
            details["new_perfect_cards"] = new_perfect_cards
            details["perfect_bonus"] = perfect_bonus

    # ---------------- OTHER MODES (LEGACY LOGIC) ----------------
    else:
        def _gold_from_details(d):
            if not isinstance(d, dict):
                return None
            for key in ("gold_rounded", "gold_raw", "gold", "points_total"):
                if key in d:
                    try:
                        return float(d[key])
                    except (TypeError, ValueError):
                        continue
            return None

        run_gold_raw = None

        # 1) explicit "gold" from client
        if gold_in is not None:
            try:
                run_gold_raw = float(gold_in)
            except (TypeError, ValueError):
                run_gold_raw = None

        # 2) else derive from details
        if run_gold_raw is None:
            run_gold_raw = _gold_from_details(details)

        # 3) final fallback: capped score
        if run_gold_raw is None:
            run_gold_raw = float(_cap_points(score_val))

        if run_gold_raw < 0:
            run_gold_raw = 0.0

        gold_rounded = round(run_gold_raw * 2.0) / 2.0

        # Lifetime per-set cap for non-flashcards
        MAX_GOLD_PER_SET = 50

        points_awarded_local = gold_rounded

        if MAX_GOLD_PER_SET is not None and MAX_GOLD_PER_SET > 0:
            existing_rows = (
                Score.query
                .filter(
                    Score.user_id == current_user.id,
                    Score.set_name == set_name,
                    Score.mode == mode,
                )
                .all()
            )

            def _row_gold(row):
                d = row.details or {}
                if isinstance(d, dict):
                    for key in (
                        "gold_awarded",
                        "points_awarded",
                        "gold_rounded",
                        "gold_raw",
                        "gold",
                        "points_total",
                    ):
                        if key in d:
                            try:
                                return float(d[key])
                            except (TypeError, ValueError):
                                continue
                return float(_cap_points(row.score))

            already = sum(_row_gold(r) for r in existing_rows)
            remaining = max(0.0, float(MAX_GOLD_PER_SET) - already)
            points_awarded_local = max(0.0, min(gold_rounded, remaining))

        run_gold_awarded = points_awarded_local
        # keep run_gold_raw as-is for diagnostics

    # ---- embed gold into details ----
    if run_gold_awarded is None:
        run_gold_awarded = 0.0

    if run_gold_raw is None:
        run_gold_raw = run_gold_awarded

    try:
        gold_raw_val = float(run_gold_raw)
    except (TypeError, ValueError):
        gold_raw_val = float(run_gold_awarded)

    if gold_raw_val < 0:
        gold_raw_val = 0.0

    gold_rounded_val = round(gold_raw_val * 2.0) / 2.0

    if isinstance(details, dict):
        details.setdefault("gold_raw", gold_raw_val)
        details.setdefault("gold_rounded", gold_rounded_val)
        details["gold_awarded"] = float(run_gold_awarded)
        details["points_awarded"] = float(run_gold_awarded)

    # ---- persist ----
    s = Score(
        user_id=current_user.id,
        set_name=set_name,
        mode=mode,
        score=score_val,
        attempts=attempts,
        details=details,
    )
    db.session.add(s)
    safe_commit()

    return jsonify(
        {
            "message": "saved",
            "score_id": s.id,
            "details": {"points_awarded": int(round(run_gold_awarded))},
        }
    ), 201

@api_bp.route("/scores", methods=["POST"])
@token_required
def post_scores_alias(current_user):
    return _call_view(submit_score, current_user)

@api_bp.route("/get_scores", methods=["GET"])
@token_required
def get_scores(current_user):
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

@api_bp.route("/points_event", methods=["POST"])
@token_required
def points_event(current_user):
    try:
        from .models import PointsEvent  # type: ignore
    except Exception:
        return jsonify({"ok": False, "error": "points_event_not_enabled"}), 501
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip() or None
    mode     = (data.get("mode") or "").strip() or None
    try: points = int(data.get("points") or 0)
    except: points = 0
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
    row = PointsEvent(user_id=current_user.id, set_name=set_name, mode=mode, points=points, meta=meta)
    db.session.add(row)
    safe_commit()
    return jsonify({"ok": True, "id": row.id})


# ---------------------------
# Stats
# ---------------------------

@api_bp.route("/my/stats", methods=["GET"])
@token_required
def my_stats(current_user):
    since = datetime.utcnow() - timedelta(days=365)
    rows = (
        db.session.query(Score.timestamp, Score.score, Score.details)
        .filter(Score.user_id == current_user.id, Score.timestamp >= since)
        .order_by(Score.timestamp.desc())
        .all()
    )

    # ---- streaks ----
    today = datetime.utcnow().date()
    day_set = {ts.date() for ts, _, _ in rows}
    days = sorted(day_set, reverse=True)

    streak = 0
    d = today
    while d in day_set:
        streak += 1
        d = d - timedelta(days=1)

    longest = 0
    if days:
        seq = sorted(days)
        run = 1
        for i in range(1, len(seq)):
            if (seq[i] - seq[i - 1]).days == 1:
                run += 1
            else:
                if run > longest:
                    longest = run
                run = 1
        if run > longest:
            longest = run

    week_start = _week_start_utc(today)

    def _points_from_row(score_val, details):
        """Best-effort gold for stats.

        Priority:
        1) gold_awarded / points_awarded  (what we *actually* counted)
        2) gold_rounded / gold_raw / gold / points_total
        3) fallback: capped score
        """
        if isinstance(details, dict):
            for key in (
                "gold_awarded",
                "points_awarded",
                "gold_rounded",
                "gold_raw",
                "gold",
                "points_total",
            ):
                if key in details:
                    try:
                        return max(0, int(round(float(details[key]))))
                    except (TypeError, ValueError):
                        continue
        return _cap_points(score_val)

    weekly_points = sum(
        _points_from_row(sc, det) for ts, sc, det in rows if ts.date() >= week_start.date()
    )
    total_gold = sum(_points_from_row(sc, det) for _, sc, det in rows)

    # ---- weekly goal ----
    goal = 500
    if hasattr(current_user, "weekly_goal"):
        try:
            g = int(getattr(current_user, "weekly_goal"))
            if g > 0:
                goal = max(50, min(g, 5000))
        except (TypeError, ValueError):
            pass

    return jsonify(
        {
            "streak_days": streak,
            "longest_streak": longest,
            "weekly_points": weekly_points,
            "weekly_gold": weekly_points,
            "goal_points": goal,
            "goal_gold": goal,
            "total_gold": total_gold,
        }
    )

# ---------------------------
# Groups
# ---------------------------

@api_bp.route("/my/groups", methods=["GET"])
@token_required
def my_groups(current_user):
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
    safe_commit()

    resp = {"id": g.id, "name": g.name}
    if hasattr(g, "join_code"):
        resp["join_code"] = g.join_code
    return jsonify(resp), 201

@api_bp.route("/groups/join", methods=["POST"])
@token_required
def join_group(current_user):
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
        safe_commit()
    return jsonify({"ok": True, "group_id": g.id, "group_name": g.name})

@api_bp.route("/groups/<int:group_id>/leave", methods=["DELETE"])
@token_required
def leave_group(current_user, group_id):
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
            db.session.delete(g)
        safe_commit()
        return jsonify({"ok": True, "deleted": True})

    if owner_left and g:
        new_owner = remaining[0]
        g.owner_id = new_owner.user_id
        new_owner.role = "owner"

    safe_commit()
    return jsonify({"ok": True, "deleted": False})

@api_bp.route("/groups/<int:group_id>/invite_code", methods=["GET"])
@token_required
def group_invite_code(current_user, group_id):
    g = Group.query.get(group_id)
    if not g:
        return jsonify({"error": "not_found"}), 404
    if not hasattr(g, "join_code"):
        return jsonify({"error": "join_not_supported"}), 400
    return jsonify({"code": g.join_code or ""})

@api_bp.route("/groups/<int:group_id>/recent_activity", methods=["GET"])
@token_required
def group_recent_activity(current_user, group_id):
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except Exception:
        limit = 50

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
    window = (request.args.get("window") or "week").lower()
    since_dt = None
    if window == "week":
        since_dt = _week_start_utc()

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

@api_bp.route("/groups/<int:group_id>/invite_emails", methods=["POST"])
@token_required
def invite_emails(current_user, group_id):
    data = request.get_json(silent=True) or {}
    raw = data.get("emails", "")

    if isinstance(raw, list):
        candidates = [str(x) for x in raw]
    else:
        candidates = re.split(r"[\s,;]+", raw or "")

    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    emails = [e.strip().lower() for e in candidates if e and EMAIL_RE.match(e)]
    emails = list(dict.fromkeys(emails))

    if not emails:
        return jsonify({"ok": False, "error": "no_valid_emails"}), 400

    m = GroupMembership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not m:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    g = Group.query.get(group_id)
    if not g:
        return jsonify({"ok": False, "error": "not_found"}), 404

    code = None
    if hasattr(g, "join_code"):
        code = (getattr(g, "join_code") or "").strip()
    if not code and hasattr(g, "invite_code"):
        code = (getattr(g, "invite_code") or "").strip()

    if not code:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if hasattr(g, "join_code"):
            g.join_code = code
        elif hasattr(g, "invite_code"):
            g.invite_code = code
        safe_commit()

    base = (
        current_app.config.get("FRONTEND_BASE_URL")
        or current_app.config.get("APP_BASE_URL")
        or os.environ.get("APP_BASE_URL")
        or request.host_url
    ).rstrip("/")
    link = f"{base}/groups.html?code={code}"

    group_name = getattr(g, "name", None) or getattr(g, "group_name", None) or f"Group {g.id}"
    sender_name = getattr(current_user, "name", None) or (
        current_user.email.split("@")[0] if getattr(current_user, "email", None) else "A member"
    )

    subject = _invite_subject(group_name)
    text, html = _invite_bodies(group_name, link, code, sender_name)

    visible_to = []
    if getattr(current_user, "email", None):
        visible_to = [current_user.email]
    elif os.environ.get("GMAIL_USER"):
        visible_to = [os.environ["GMAIL_USER"]]

    try:
        # Batch BCC to stay within SMTP/SES recipient caps
        max_rcpts = int(os.getenv("EMAIL_MAX_RCPTS", "40"))
        sent_total = 0
        for chunk in _chunks(emails, max_rcpts):
            send_email(
                subject=subject,
                text=text,
                html=html,
                to=visible_to,
                bcc=chunk,
                reply_to=(current_user.email or None),
            )
            sent_total += len(chunk)
        return jsonify({"ok": True, "sent": sent_total})
    except Exception as e:
        err_msg = getattr(e, "smtp_error", None)
        if isinstance(err_msg, (bytes, bytearray)):
            try: err_msg = err_msg.decode("utf-8", "ignore")
            except Exception: err_msg = None
        detail = (err_msg or str(e) or "email_send_failed").strip()
        current_app.logger.exception("Invite send failed: %s", detail)
        return jsonify({"ok": False, "error": "EMAIL_SEND_FAILED", "detail": detail[:200]}), 500

def _ensure_group_code_and_link(g):
    """Ensure group has a code and return (code, invite_url)."""
    if not g:
        return None, None

    code = None
    if hasattr(g, "join_code"):
        code = (getattr(g, "join_code") or "").strip()
    if not code and hasattr(g, "invite_code"):
        code = (getattr(g, "invite_code") or "").strip()

    if not code:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if hasattr(g, "join_code"):
            g.join_code = code
        elif hasattr(g, "invite_code"):
            g.invite_code = code
        safe_commit()

    base = (
        current_app.config.get("FRONTEND_BASE_URL")
        or current_app.config.get("APP_BASE_URL")
        or os.environ.get("APP_BASE_URL")
        or request.host_url
    ).rstrip("/")
    # groups.html lives in /docs; the page reads ?code= and calls /api/groups/join
    invite_url = f"{base}/groups.html?code={code}"
    return code, invite_url


@api_bp.route("/groups/<int:group_id>/invite_link", methods=["GET", "POST"])
@token_required
def group_invite_link(current_user, group_id):
    """Compat for UI: returns {'url': '<.../groups.html?code=XXXX>', 'code': 'XXXX'}"""
    g = Group.query.get(group_id)
    if not g:
        return jsonify({"error": "not_found"}), 404
    # must be a member
    if not GroupMembership.query.filter_by(user_id=current_user.id, group_id=group_id).first():
        return jsonify({"error": "forbidden"}), 403

    code, link = _ensure_group_code_and_link(g)
    return jsonify({"url": link, "code": code})


# Aliases the UI may try
@api_bp.route("/my/groups/<int:group_id>/invite_link", methods=["GET", "POST"])
@token_required
def my_group_invite_link(current_user, group_id):
    return _call_view(group_invite_link, current_user, group_id)


@api_bp.route("/my/groups/invite_link", methods=["GET"])
@token_required
def my_groups_invite_link_qs(current_user):
    try:
        group_id = int(request.args.get("group_id"))
    except Exception:
        return jsonify({"error": "group_id_required"}), 400
    return _call_view(group_invite_link, current_user, group_id)


@api_bp.route("/groups/<int:group_id>/share", methods=["GET", "POST"])
@token_required
def group_share(current_user, group_id):
    """Another alias the UI probes."""
    return _call_view(group_invite_link, current_user, group_id)


# ---- Email invite wrappers matching the UI's POST targets ----

@api_bp.route("/groups/<int:group_id>/invite", methods=["POST"])
@token_required
def group_invite_compat(current_user, group_id):
    """Compat wrapper → reuses existing invite_emails logic."""
    return _call_view(group_invite_link, current_user, group_id)


@api_bp.route("/groups/invite", methods=["POST"])
@token_required
def groups_invite_compat_body(current_user):
    data = request.get_json(silent=True) or {}
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"ok": False, "error": "group_id_required"}), 400
    # Rebuild a request for the existing handler
    request_data = {"emails": data.get("emails", "")}
    # Temporarily swap request.json (simple, works in Flask) or just call the logic inline.
    with current_app.test_request_context(json=request_data):
        return _call_view(invite_emails, current_user, int(group_id))


@api_bp.route("/my/groups/invite", methods=["POST"])
@token_required
def my_groups_invite_compat(current_user):
    return _call_view(groups_invite_compat_body, current_user)

# ---------------------------
# Sets (library + global + create/update)
# ---------------------------

@api_bp.route("/my/sets", methods=["GET"])
@token_required
def my_sets_get(current_user):
    """Legacy path → delegate to canonical handler in sets_api for a single source of truth."""
    from .sets_api import my_sets as setsapi_my_sets  # local import to avoid cycles
    return _call_view(setsapi_my_sets, current_user)


@api_bp.route("/my/sets", methods=["POST"])
@token_required
def my_sets_add(current_user):
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
    safe_commit()
    return jsonify({"ok": True})

@api_bp.route("/my/sets/<path:set_name>", methods=["DELETE"])
@token_required
def my_sets_remove(current_user, set_name):
    set_name = (set_name or "").strip()
    row = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not row:
        return jsonify({"ok": True, "message": "Already not in library"})
    db.session.delete(row)
    safe_commit()
    return jsonify({"ok": True})

# ---- Underscore aliases the UI may hit ----

@api_bp.route("/my_sets", methods=["POST"])
@token_required
def my_sets_add_alias(current_user):
    return _call_view(my_sets_add, current_user)

@api_bp.route("/my_sets/<path:set_name>", methods=["DELETE"])
@token_required
def my_sets_remove_alias(current_user, set_name):
    return _call_view(my_sets_remove, current_user, set_name)

@api_bp.route("/sets/available", methods=["GET"])
@token_required
def list_available_sets(current_user):
    if not SETS_DIR.exists():
        return jsonify([])
    sets = [{"name": p.stem, "filename": p.name} for p in sorted(SETS_DIR.glob("*.json"))]
    return jsonify(sets)

# ---------- Create set ----------

@api_bp.route("/create_set", methods=["POST"])
@token_required
def create_set(current_user):
    """
    Delegates to the canonical create handler in sets_api (build + publish).
    We keep this URL for legacy clients.
    """
    from .sets_api import create_set as setsapi_create_set  # local import to avoid cycles
    # Reuse the same request payload/body and authenticated user
    return _call_view(setsapi_create_set, current_user)

# ---------- Update set ----------

@api_bp.route("/update_set", methods=["POST", "PUT", "PATCH"])
@token_required
def update_set(current_user):
    """
    Body:
      { set_name: str,
        data?: [...],           # replaces cards/passages entirely if provided
        modes?: ["learn","speak","read","listen"] }
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

    # Modes (optional, explicit only)
    if "modes" in payload:
        modes = _normalize_modes(payload.get("modes"))
        if not modes:
            return jsonify({"error": "invalid_modes"}), 400
        j.setdefault("meta", {})
        j["meta"]["modes"] = modes
        j["modes"] = modes

    # Data (optional → full replace)
    if "data" in payload:
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return jsonify({"error": "data must be a non-empty array"}), 400
        modes_now = _extract_modes_from_json(j) or ["learn", "speak"]  # default for legacy
        if set(modes_now) == {"read"} or modes_now == ["read"]:
            j.pop("cards", None)
            j["passages"] = data
        else:
            j.pop("passages", None)
            j["cards"] = data

    # Ensure name
    j["name"] = j.get("name") or set_name

    path.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")

    warns = []
    try:
        regenerate_set_pages(set_name)
    except Exception as e:
        warns.append(f"regenerate_failed: {e}")

    try:
        modes_now = _extract_modes_from_json(j) or []
        if "listen" in modes_now:
            items = j.get("cards") or j.get("items") or j.get("data") or []
            create_listening_set(set_name, items)
    except Exception as e:
        warns.append(f"listening_generate_failed: {e}")

    return jsonify({
        "ok": True,
        "name": set_name,
        "modes": _extract_modes_from_json(j) or ["learn","speak"],
        "warnings": warns or None
    })

# ---------------------------
# Ratings
# ---------------------------

@api_bp.route("/sets/rate", methods=["POST"])
@token_required
def rate_set(current_user):
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
    safe_commit()

    return jsonify({
        "ok": True,
        "set_name": set_name,
        "stars": row.stars,
        "comment": row.comment,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }), 200

@api_bp.route("/sets/ratings", methods=["GET"])
def set_ratings_aggregate():
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
    set_name = (request.args.get("set") or "").strip()
    q = Rating.query.filter_by(user_id=current_user.id)
    if set_name:
        q = q.filter_by(set_name=set_name)
    try:
        rows = q.order_by(Rating.updated_at.desc()).limit(200).all()
    except OperationalError as e:
        current_app.logger.warning("DB dropped on my_ratings; retrying once: %s", e)
        db.session.rollback()
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
    safe_commit()
    return jsonify({"ok": True})

@api_bp.route("/session_state/complete", methods=["POST"])
@token_required
def complete_session_state(current_user):
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    mode = (data.get("mode") or "").strip().lower()
    if not set_name or not mode:
        return jsonify({"message": "set_name and mode are required"}), 400

    SessionState.query.filter_by(user_id=current_user.id, set_name=set_name, mode=mode).delete()
    safe_commit()
    return jsonify({"ok": True})

@api_bp.route("/my/continue", methods=["GET"])
@token_required
def my_continue(current_user):
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
# Challenges (optional)
# ---------------------------

@api_bp.route("/my/challenges", methods=["GET"])
@token_required
def my_challenges(current_user):
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
    return jsonify({"ok": True})
