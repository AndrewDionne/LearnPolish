#app/stats.py
from __future__ import annotations
from datetime import datetime, timedelta, date
from sqlalchemy import func
from .models import db, PointsEvent, User

# Treat "today" in server local time; if you keep TZ aware, swap in your tz utils.
def _today() -> date:
    return datetime.now().date()

def _start_of_week(d: date) -> datetime:
    # ISO week (Mon 00:00)
    return datetime(d.year, d.month, d.day) - timedelta(days=d.weekday())

def compute_weekly_points(user_id: int, ref: date | None = None) -> int:
    ref = ref or _today()
    start = _start_of_week(ref)
    end   = start + timedelta(days=7)
    q = db.session.query(func.coalesce(func.sum(PointsEvent.points), 0))\
        .filter(PointsEvent.user_id == user_id,
                PointsEvent.created_at >= start,
                PointsEvent.created_at <  end)
    return int(q.scalar() or 0)

def compute_total_points(user_id: int) -> int:
    q = db.session.query(func.coalesce(func.sum(PointsEvent.points), 0))\
        .filter(PointsEvent.user_id == user_id)
    return int(q.scalar() or 0)

def compute_streak(user_id: int) -> tuple[int, int]:
    """
    Return (current_streak_days, longest_streak_days).
    A 'day' counts if any PointsEvent exists that day.
    """
    # Fetch last 365 days (cheap, indexed)
    since = datetime.now() - timedelta(days=365)
    rows = db.session.query(PointsEvent.created_at)\
        .filter(PointsEvent.user_id == user_id, PointsEvent.created_at >= since)\
        .order_by(PointsEvent.created_at.desc()).all()
    days = set(dt.created_at.date() for dt in rows)

    # Current streak (ending today)
    cur = 0
    d = _today()
    while d in days:
        cur += 1
        d = d - timedelta(days=1)

    # Longest streak (scan)
    longest = 0
    if days:
        sorted_days = sorted(days)
        run = 1
        for i in range(1, len(sorted_days)):
            if (sorted_days[i] - sorted_days[i-1]).days == 1:
                run += 1
            else:
                longest = max(longest, run)
                run = 1
        longest = max(longest, run)
    return cur, longest

def build_stats_payload(user: User) -> dict:
    weekly = compute_weekly_points(user.id)
    total  = compute_total_points(user.id)
    cur, best = compute_streak(user.id)
    goal = user.weekly_goal or 500
    return {
        "user_id": user.id,
        "display_name": user.display_name or user.name,
        "weekly_points": weekly,
        "goal_points": goal,
        "total_points": total,
        "streak_days": cur,
        "longest_streak": best,
    }
