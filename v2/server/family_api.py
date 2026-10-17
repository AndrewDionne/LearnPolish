"""Isolated V2 private-family API. No legacy score API or paid AI dependency.

The SQLite file MUST reside on persistent, private storage if this service is
deployed. Deploying without PTP_FAMILY_DB and PTP_FAMILY_CATALOG fails closed.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, g, jsonify, request

REGIONS = frozenset((
    "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie",
    "łódzkie", "małopolskie", "mazowieckie", "opolskie", "podkarpackie",
    "podlaskie", "pomorskie", "śląskie", "świętokrzyskie",
    "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie",
))
MODES = frozenset(("learn", "read", "listen", "speak"))
TIERS = {1: 10, 2: 14, 3: 19, 4: 26, 5: 35}
EMAIL = re.compile(r"^[^@\s]{1,100}@[^@\s]{1,100}\.[^@\s]{2,30}$")
MAX_MEMBERS = 12

DDL = """
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 salt TEXT NOT NULL, password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
 expiry INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS families(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS members(
 family_id INTEGER NOT NULL REFERENCES families(id), user_id INTEGER NOT NULL REFERENCES users(id),
 joined_at INTEGER NOT NULL, PRIMARY KEY(family_id,user_id)
);
CREATE TABLE IF NOT EXISTS invitations(
 code_hash TEXT PRIMARY KEY, family_id INTEGER NOT NULL REFERENCES families(id),
 expiry INTEGER NOT NULL, redeemed_by INTEGER REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS region_goals(
 family_id INTEGER NOT NULL REFERENCES families(id), region TEXT NOT NULL,
 target INTEGER NOT NULL, PRIMARY KEY(family_id,region)
);
CREATE TABLE IF NOT EXISTS activities(
 id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL REFERENCES families(id),
 user_id INTEGER NOT NULL REFERENCES users(id), item_id TEXT NOT NULL,
 mode TEXT NOT NULL, day TEXT NOT NULL, tier INTEGER NOT NULL, xp INTEGER NOT NULL,
 expedition_xp INTEGER NOT NULL, region TEXT NOT NULL, created_at INTEGER NOT NULL,
 UNIQUE(family_id,user_id,item_id,mode,day)
);
CREATE INDEX IF NOT EXISTS activities_week ON activities(family_id,created_at,user_id);
CREATE TABLE IF NOT EXISTS login_throttle(
 identity TEXT PRIMARY KEY, failures INTEGER NOT NULL, first_at INTEGER NOT NULL
);
"""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _password(secret: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), bytes.fromhex(salt), 390000).hex()


def _now() -> int:
    return int(time.time())


def _json():
    raw = request.get_json(silent=True)
    return raw if isinstance(raw, dict) else {}


def create_app(database_path: str | None = None, catalog_path: str | None = None,
               allowed_origins: tuple[str, ...] | None = None) -> Flask:
    path = database_path or os.environ.get("PTP_FAMILY_DB")
    catalog = catalog_path or os.environ.get("PTP_FAMILY_CATALOG")
    if not path or not catalog or path == ":memory:":
        raise RuntimeError("Explicit persistent PTP_FAMILY_DB and PTP_FAMILY_CATALOG required")
    raw = json.loads(Path(catalog).read_text(encoding="utf-8"))
    if raw.get("schemaVersion") != 1 or not isinstance(raw.get("lessons"), list):
        raise RuntimeError("Invalid V2 built-in catalog")
    known: dict[str, int] = {}
    for lesson in raw["lessons"]:
        tier = lesson.get("difficultyTier", 1)
        if type(tier) is not int or tier not in TIERS:
            raise RuntimeError("Invalid lesson difficulty")
        for item in lesson["items"]:
            key = item["id"]
            if not isinstance(key, str) or not re.fullmatch(r"[\w:.-]{1,180}", key) or key in known:
                raise RuntimeError("Duplicate or invalid learning item")
            known[key] = tier
    if not known:
        raise RuntimeError("Empty lesson catalog")
    origins = allowed_origins if allowed_origins is not None else tuple(
        x.strip() for x in os.getenv("PTP_FAMILY_ORIGINS", "").split(",") if x.strip()
    )
    if any("*" in x or not x.startswith(("https://", "http://localhost:", "http://127.0.0.1:")) for x in origins):
        raise RuntimeError("Family origins must be exact HTTPS or local development URLs")
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16_000
    app.config["JSON_SORT_KEYS"] = True
    path = str(Path(path).resolve())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(DDL)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(path, isolation_level=None, timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
            g.db.execute("PRAGMA busy_timeout=15000")
        return g.db

    @app.teardown_appcontext
    def close(error=None):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    @app.after_request
    def cors(response):
        origin = request.headers.get("Origin")
        if origin and origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.before_request
    def guard():
        origin = request.headers.get("Origin")
        if origin and origin not in origins:
            return jsonify(error="origin_not_allowed"), 403
        if request.method == "OPTIONS":
            return "", 204

    def fail(error, status=400):
        return jsonify(error=error), status

    def auth(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return fail("authentication_required", 401)
            token = header[7:]
            if len(token) < 30 or len(token) > 256:
                return fail("invalid_session", 401)
            user = db().execute(
                """SELECT u.id,u.name,u.email FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=? AND s.expiry>?""", (_hash(token), _now())
            ).fetchone()
            if not user:
                return fail("invalid_session", 401)
            return fn(user, *args, **kwargs)
        return wrapped

    def member(user, family_id):
        return db().execute(
            "SELECT 1 FROM members WHERE family_id=? AND user_id=?",
            (family_id, user["id"])
        ).fetchone() is not None

    def family_guard(user, family_id):
        if not member(user, family_id):
            return fail("not_found", 404)
        return None

    @app.get("/api/v2/family/health")
    def health():
        return jsonify(ok=True, version=1, catalog_items=len(known))

    @app.post("/api/v2/family/signup")
    def signup():
        data = _json()
        email = str(data.get("email", "")).strip().lower()
        password = data.get("password", "")
        name = str(data.get("name", "")).strip()
        if not EMAIL.fullmatch(email) or not isinstance(password, str) or len(password) < 12 or len(password) > 256 or not 1 <= len(name) <= 48:
            return fail("invalid_registration")
        salt = secrets.token_hex(16)
        con = db()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO users(email,name,salt,password_hash) VALUES(?,?,?,?)",
                        (email, name, salt, _password(password, salt)))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            return fail("account_unavailable", 409)
        return jsonify(created=True), 201

    @app.post("/api/v2/family/login")
    def login():
        data = _json()
        email = str(data.get("email", "")).strip().lower()
        pw = data.get("password", "")
        if not isinstance(pw, str) or len(email) > 250:
            return fail("invalid_credentials", 401)
        con = db()
        key = _hash(email + ":" + request.remote_addr.__str__())
        throttle = con.execute("SELECT failures,first_at FROM login_throttle WHERE identity=?", (key,)).fetchone()
        now = _now()
        if throttle and throttle["failures"] >= 8 and now - throttle["first_at"] < 900:
            return fail("too_many_attempts", 429)
        row = con.execute("SELECT id,name,email,salt,password_hash FROM users WHERE email=?", (email,)).fetchone()
        valid = row is not None and hmac.compare_digest(_password(pw, row["salt"]), row["password_hash"])
        if not valid:
            fresh = not throttle or now-throttle["first_at"] >= 900
            first = now if fresh else throttle["first_at"]
            count = 1 if fresh else throttle["failures"]+1
            con.execute("INSERT OR REPLACE INTO login_throttle VALUES(?,?,?)", (key,count,first))
            return fail("invalid_credentials", 401)
        con.execute("DELETE FROM login_throttle WHERE identity=?", (key,))
        token = secrets.token_urlsafe(32)
        con.execute("INSERT INTO sessions VALUES(?,?,?)", (_hash(token),row["id"],now+7*86400))
        return jsonify(token=token, user={"id":row["id"],"name":row["name"]})

    @app.post("/api/v2/family/logout")
    @auth
    def logout(user):
        token = request.headers["Authorization"][7:]
        db().execute("DELETE FROM sessions WHERE token_hash=?", (_hash(token),))
        return jsonify(ok=True)

    @app.get("/api/v2/family/me")
    @auth
    def me(user):
        families = db().execute(
            """SELECT f.id,f.name FROM families f JOIN members m ON f.id=m.family_id
               WHERE m.user_id=? ORDER BY f.id""", (user["id"],)
        ).fetchall()
        return jsonify(user={"id":user["id"],"name":user["name"]},
                       families=[dict(row) for row in families])

    @app.post("/api/v2/family/groups")
    @auth
    def create_group(user):
        name = str(_json().get("name", "")).strip()
        if not 3 <= len(name) <= 50:
            return fail("invalid_group_name")
        con = db()
        con.execute("BEGIN IMMEDIATE")
        gid = con.execute("INSERT INTO families(name,owner_id) VALUES(?,?)",
                          (name,user["id"])).lastrowid
        con.execute("INSERT INTO members VALUES(?,?,?)",(gid,user["id"],_now()))
        con.commit()
        return jsonify(id=gid,name=name), 201

    @app.post("/api/v2/family/groups/<int:family_id>/invite")
    @auth
    def invite(user,family_id):
        family = db().execute("SELECT owner_id FROM families WHERE id=?", (family_id,)).fetchone()
        if not family or not member(user,family_id):
            return fail("not_found",404)
        if family["owner_id"] != user["id"]:
            return fail("owner_only",403)
        token = secrets.token_urlsafe(24)
        db().execute("INSERT INTO invitations(code_hash,family_id,expiry) VALUES(?,?,?)",
                     (_hash(token),family_id,_now()+48*3600))
        return jsonify(code=token,expires_in_hours=48), 201

    @app.post("/api/v2/family/invites/redeem")
    @auth
    def redeem(user):
        code = _json().get("code","")
        if not isinstance(code,str) or not 25 <= len(code) <= 80:
            return fail("invalid_invite")
        con = db()
        con.execute("BEGIN IMMEDIATE")
        invite_row = con.execute(
            "SELECT * FROM invitations WHERE code_hash=? AND expiry>? AND redeemed_by IS NULL",
            (_hash(code),_now())).fetchone()
        if not invite_row:
            con.rollback()
            return fail("invalid_invite")
        gid = invite_row["family_id"]
        if member(user,gid):
            con.rollback()
            return fail("already_member",409)
        count = con.execute("SELECT COUNT(*) FROM members WHERE family_id=?", (gid,)).fetchone()[0]
        if count >= MAX_MEMBERS:
            con.rollback()
            return fail("group_full",409)
        con.execute("INSERT INTO members VALUES(?,?,?)", (gid,user["id"],_now()))
        con.execute("UPDATE invitations SET redeemed_by=? WHERE code_hash=?", (user["id"],_hash(code)))
        con.commit()
        return jsonify(group_id=gid,joined=True)

    @app.post("/api/v2/family/groups/<int:family_id>/activity")
    @auth
    def record(user,family_id):
        access = family_guard(user,family_id)
        if access:
            return access
        data = _json()
        item = data.get("item_id")
        mode = data.get("mode")
        region = data.get("region")
        # NEVER accept client-supplied XP, difficulty, dates, outcomes or arbitrary item IDs.
        if not isinstance(item,str) or item not in known or not isinstance(mode,str) or mode not in MODES or not isinstance(region,str) or region not in REGIONS:
            return fail("invalid_activity")
        con = db()
        now = _now()
        day = datetime.fromtimestamp(now,timezone.utc).date().isoformat()
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute(
            """SELECT 1 FROM activities WHERE family_id=? AND user_id=? AND item_id=? AND mode=? AND day=?""",
            (family_id,user["id"],item,mode,day)).fetchone()
        if existing:
            con.rollback()
            return jsonify(accepted=False,reason="already_credited")
        # Count prior distinct days within the same family. Replaying remains personal effort;
        # expedition contribution tapers and cannot unlock all regions by rote repetition.
        repeats = con.execute(
            "SELECT COUNT(*) FROM activities WHERE family_id=? AND user_id=? AND item_id=? AND mode=?",
            (family_id,user["id"],item,mode)).fetchone()[0]
        tier = known[item]
        xp = TIERS[tier]
        expedition_xp = xp if repeats==0 else round(xp/2) if repeats==1 else 0
        row = con.execute("SELECT target FROM region_goals WHERE family_id=? AND region=?",
                          (family_id,region)).fetchone()
        if row is None:
            started = con.execute("SELECT COUNT(*) FROM region_goals WHERE family_id=?",
                                  (family_id,)).fetchone()[0]
            target = round(300*((1+.22*started)**1.35)/10)*10
            con.execute("INSERT INTO region_goals VALUES(?,?,?)",(family_id,region,target))
        else:
            target = row["target"]
        con.execute(
            """INSERT INTO activities(family_id,user_id,item_id,mode,day,tier,xp,expedition_xp,region,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (family_id,user["id"],item,mode,day,tier,xp,expedition_xp,region,now))
        con.commit()
        return jsonify(accepted=True,xp=xp,expedition_xp=expedition_xp,region=region,target=target), 201


    def _owner_guard(user, family_id):
        group = db().execute("SELECT owner_id FROM families WHERE id=?", (family_id,)).fetchone()
        if not group or not member(user, family_id):
            return fail("not_found", 404)
        if group["owner_id"] != user["id"]:
            return fail("owner_only", 403)
        return None

    def _purge_group(con, family_id):
        """Erase an entirely abandoned family and all identifiers in one transaction."""
        con.execute("DELETE FROM invitations WHERE family_id=?", (family_id,))
        con.execute("DELETE FROM activities WHERE family_id=?", (family_id,))
        con.execute("DELETE FROM region_goals WHERE family_id=?", (family_id,))
        con.execute("DELETE FROM members WHERE family_id=?", (family_id,))
        con.execute("DELETE FROM families WHERE id=?", (family_id,))

    @app.post("/api/v2/family/groups/<int:family_id>/invites/revoke")
    @auth
    def revoke_invites(user, family_id):
        access = _owner_guard(user, family_id)
        if access:
            return access
        con = db()
        con.execute("BEGIN IMMEDIATE")
        deleted = con.execute(
            "DELETE FROM invitations WHERE family_id=? AND redeemed_by IS NULL",
            (family_id,)
        ).rowcount
        con.commit()
        return jsonify(revoked=deleted)

    @app.post("/api/v2/family/groups/<int:family_id>/transfer")
    @auth
    def transfer_group(user, family_id):
        access = _owner_guard(user, family_id)
        if access:
            return access
        target = _json().get("new_owner_id")
        if type(target) is not int or target == user["id"]:
            return fail("invalid_new_owner")
        con = db()
        con.execute("BEGIN IMMEDIATE")
        if not con.execute(
            "SELECT 1 FROM members WHERE family_id=? AND user_id=?",
            (family_id, target)
        ).fetchone():
            con.rollback()
            return fail("new_owner_must_be_member", 400)
        con.execute("UPDATE families SET owner_id=? WHERE id=?", (target, family_id))
        con.commit()
        return jsonify(transferred=True, new_owner_id=target)

    @app.post("/api/v2/family/groups/<int:family_id>/leave")
    @auth
    def leave_group(user, family_id):
        if not member(user, family_id):
            return fail("not_found", 404)
        con = db()
        con.execute("BEGIN IMMEDIATE")
        group = con.execute("SELECT owner_id FROM families WHERE id=?", (family_id,)).fetchone()
        if not group:
            con.rollback()
            return fail("not_found", 404)
        if group["owner_id"] == user["id"]:
            others = con.execute(
                "SELECT 1 FROM members WHERE family_id=? AND user_id<>?",
                (family_id, user["id"])
            ).fetchone()
            if others:
                con.rollback()
                return fail("transfer_ownership_before_leaving", 409)
            _purge_group(con, family_id)
            erased = True
            removed = 0
        else:
            # Data minimization: do not retain linked activities after withdrawal.
            removed = con.execute(
                "DELETE FROM activities WHERE family_id=? AND user_id=?",
                (family_id, user["id"])
            ).rowcount
            con.execute("DELETE FROM members WHERE family_id=? AND user_id=?",
                        (family_id, user["id"]))
            erased = False
        con.commit()
        return jsonify(left=True, family_deleted=erased, removed_activities=removed)

    @app.get("/api/v2/family/account/export")
    @auth
    def export_account(user):
        con = db()
        owned = con.execute(
            """SELECT f.id,f.name,f.owner_id
               FROM families f JOIN members m ON f.id=m.family_id
               WHERE m.user_id=? ORDER BY f.id""", (user["id"],)
        ).fetchall()
        earned = con.execute(
            """SELECT family_id,item_id,mode,day,tier,xp,expedition_xp,region,created_at
               FROM activities WHERE user_id=? ORDER BY id""", (user["id"],)
        ).fetchall()
        return jsonify(version=1, exported_at=datetime.now(timezone.utc).isoformat(),
                       profile={"id":user["id"],"email":user["email"],"name":user["name"]},
                       families=[dict(row) for row in owned],
                       activities=[dict(row) for row in earned])

    @app.post("/api/v2/family/account/password")
    @auth
    def change_password(user):
        data = _json()
        current = data.get("current_password")
        new = data.get("new_password")
        if (not isinstance(current, str) or not isinstance(new, str) or
                not 12 <= len(new) <= 256 or current == new):
            return fail("invalid_password_change")
        con = db()
        row = con.execute("SELECT salt,password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
        if not row or not hmac.compare_digest(_password(current, row["salt"]), row["password_hash"]):
            return fail("invalid_credentials", 401)
        salt = secrets.token_hex(16)
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE users SET salt=?,password_hash=? WHERE id=?",
                    (salt, _password(new, salt), user["id"]))
        con.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        con.commit()
        return jsonify(changed=True, sign_in_again=True)

    @app.post("/api/v2/family/account/delete")
    @auth
    def delete_account(user):
        data = _json()
        password = data.get("password")
        if data.get("confirmation") != "DELETE MY ACCOUNT" or not isinstance(password, str):
            return fail("explicit_confirmation_required")
        con = db()
        row = con.execute("SELECT salt,password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
        if not row or not hmac.compare_digest(_password(password, row["salt"]), row["password_hash"]):
            return fail("invalid_credentials", 401)
        con.execute("BEGIN IMMEDIATE")
        owned = con.execute("SELECT id FROM families WHERE owner_id=?", (user["id"],)).fetchall()
        for entry in owned:
            other = con.execute(
                "SELECT 1 FROM members WHERE family_id=? AND user_id<>?",
                (entry["id"],user["id"])
            ).fetchone()
            if other:
                con.rollback()
                return fail("transfer_ownership_before_deletion", 409)
        for entry in owned:
            _purge_group(con, entry["id"])
        # Revocation MUST delete consumed invites, never make one-use codes reusable.
        con.execute("DELETE FROM invitations WHERE redeemed_by=?", (user["id"],))
        con.execute("DELETE FROM activities WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM members WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM users WHERE id=?", (user["id"],))
        con.commit()
        return jsonify(deleted=True)

    @app.get("/api/v2/family/groups/<int:family_id>/summary")
    @auth
    def summary(user,family_id):
        access = family_guard(user,family_id)
        if access:
            return access
        con = db()
        family=con.execute("SELECT name,owner_id FROM families WHERE id=?", (family_id,)).fetchone()
        # Weekly league uses UTC Monday; ISO weeks ensure identical results across devices.
        now=datetime.now(timezone.utc)
        week_start = int((now.replace(hour=0,minute=0,second=0,microsecond=0)
                          - __import__("datetime").timedelta(days=now.weekday())).timestamp())
        members = con.execute(
            """SELECT u.id,u.name,COALESCE(SUM(a.xp),0) AS weekly_xp,
               COUNT(DISTINCT a.day) AS active_days,COALESCE(MAX(a.tier),0) AS highest_tier,
               COALESCE(SUM(a.expedition_xp),0) AS team_xp
               FROM members m JOIN users u ON m.user_id=u.id
               LEFT JOIN activities a ON a.user_id=u.id AND a.family_id=m.family_id
                   AND a.created_at>=?
               WHERE m.family_id=? GROUP BY u.id,u.name ORDER BY weekly_xp DESC,u.name""",
            (week_start,family_id)).fetchall()
        goals = con.execute(
            """SELECT r.region,r.target,COALESCE(SUM(a.expedition_xp),0) AS earned
               FROM region_goals r LEFT JOIN activities a ON a.region=r.region AND a.family_id=r.family_id
               WHERE r.family_id=? GROUP BY r.region,r.target ORDER BY r.region""",
            (family_id,)).fetchall()
        return jsonify(group={"id":family_id,"name":family["name"],"can_invite":user["id"]==family["owner_id"]},
                       members=[dict(x) for x in members],
                       regions=[dict(x) | {"unlocked":x["earned"]>=x["target"]} for x in goals],
                       recognition={"improvement":"pending_validated_evidence"},
                       totals={"weekly_xp":sum(x["weekly_xp"] for x in members),
                               "regions_unlocked":sum(x["earned"]>=x["target"] for x in goals)})

    return app


if __name__ == "__main__":
    create_app().run(port=8016,debug=False)
