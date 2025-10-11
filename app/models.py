# app/models.py
# Preserves existing tables and adds optional profile fields on User
# (display_name, weekly_goal, avatar_id, ui_lang). Groups, Ratings, Scores,
# SessionState unchanged except for cleanup.

from __future__ import annotations
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random, string

# Single global SQLAlchemy instance lives here.
db = SQLAlchemy()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _gen_join_code(n: int = 8) -> str:
    # URL-safe, human-friendly join code (e.g., "7KQ9M2XJ")
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

# -----------------------------------------------------------------------------
# Core models
# -----------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional profile fields used by Profile/Dashboard UIs
    display_name = db.Column(db.String(100), nullable=True)
    weekly_goal  = db.Column(db.Integer, nullable=True, default=500)   # used by /api/my/stats goal
    avatar_id    = db.Column(db.String(40), nullable=True)             # preset picker id (e.g., "scout")
    ui_lang      = db.Column(db.String(12), nullable=True, default="en")

    # Relationships (declared for convenience)
    scores = db.relationship("Score", backref="user", lazy=True)
    ratings = db.relationship("Rating", backref="user", lazy=True)
    memberships = db.relationship("GroupMembership", backref="user", lazy=True)
    user_sets = db.relationship("UserSet", backref="user", lazy=True)

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"


class Score(db.Model):
    __tablename__ = "scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    set_name = db.Column(db.String(200), nullable=False, default="")
    # Keep existing string modes; UI can map to Vocabulary/Speak/Read/Listen
    mode = db.Column(db.String(50))  # e.g., "practice", "flashcards", "read", "listen", "speak"
    score = db.Column(db.Float)      # 0..100
    attempts = db.Column(db.Integer)
    details = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<Score u={self.user_id} set={self.set_name} mode={self.mode} score={self.score}>"


class UserSet(db.Model):
    __tablename__ = "user_sets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    set_name = db.Column(db.String(200), nullable=False, index=True)
    is_owner = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "set_name", name="uq_user_set"),)

    def __repr__(self) -> str:
        return f"<UserSet u={self.user_id} {self.set_name} owner={self.is_owner}>"


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Join by code (owner can share). Unique so it’s easy to look up.
    join_code = db.Column(db.String(12), unique=True, nullable=False, default=_gen_join_code)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", foreign_keys=[owner_id])
    memberships = db.relationship("GroupMembership", backref="group", lazy=True)

    def __repr__(self) -> str:
        return f"<Group {self.id} {self.name}>"


class GroupMembership(db.Model):
    __tablename__ = "group_memberships"

    # Composite key for cleaner uniqueness (one row per user per group)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), primary_key=True)
    role = db.Column(db.String(20), default="member")  # "owner" | "member"
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<GroupMembership g={self.group_id} u={self.user_id} {self.role}>"


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    set_name = db.Column(db.String(200), nullable=False, index=True)
    stars = db.Column(db.Integer, nullable=False)  # 1..5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "set_name", name="uq_rating_user_set"),)

    def __repr__(self) -> str:
        return f"<Rating u={self.user_id} {self.set_name} {self.stars}★>"


class SessionState(db.Model):
    __tablename__ = "session_state"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    set_name = db.Column(db.String(255), index=True, nullable=False)
    mode = db.Column(db.String(32), index=True, nullable=False)  # learn|speak|read|listen
    progress = db.Column(db.JSON, nullable=False, default=dict)  # arbitrary JSON payload
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "set_name", "mode", name="uq_session_state_user_set_mode"),)
