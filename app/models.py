# models.py
from datetime import datetime
from .config import ADMIN_EMAIL
from . import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    # Keep a real DB flag for admin; set it at registration if email == ADMIN_EMAIL
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    scores = db.relationship("Score", backref="user", lazy=True)
    sets = db.relationship("UserSet", backref="user", lazy=True)
    memberships = db.relationship("GroupMembership", backref="user", lazy=True)
    ratings = db.relationship("Rating", backref="user", lazy=True) 
   
    # OPTIONAL helper: does this user match the configured admin email?
    @property
    def is_admin_email(self) -> bool:
        return bool(self.email and self.email.lower() == (ADMIN_EMAIL or "").lower())


class Score(db.Model):
    __tablename__ = "scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    set_name = db.Column(db.String(200))
    mode = db.Column(db.String(50))  # e.g. "practice", "flashcards"
    score = db.Column(db.Float)
    attempts = db.Column(db.Integer)
    details = db.Column(db.JSON, nullable=True)  # stores extra info
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class UserSet(db.Model):
    __tablename__ = "user_sets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    set_name = db.Column(db.String(200), nullable=False)
    is_owner = db.Column(db.Boolean, default=False, nullable=False)
    # DEPRECATED: per-user modes are no longer used by the UI/backend.
    # Remove the column via migration (recommended). If you are not ready to migrate,
    # leave it commented here to avoid new references.
    # modes = db.Column(db.JSON, default=list)

    __table_args__ = (
        db.UniqueConstraint("user_id", "set_name", name="uq_user_set"),
    )


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship("GroupMembership", backref="group", lazy=True)


class GroupMembership(db.Model):
    __tablename__ = "group_memberships"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    role = db.Column(db.String(50), default="member")  # e.g. member, admin

    __table_args__ = (
        db.UniqueConstraint("user_id", "group_id", name="uq_group_membership"),
    )

class Rating(db.Model):
    __tablename__ = "ratings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    set_name = db.Column(db.String(200), nullable=False)
    stars = db.Column(db.Integer, nullable=False)          # 1–5 (validated in API)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "set_name", name="uq_rating_user_set"),
    )
