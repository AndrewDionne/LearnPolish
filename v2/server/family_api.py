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
from typing import Callable

from flask import Flask, g, jsonify, request
from private_storage import prepare_database
from postgres_storage import PgIntegrityError, open_postgres, postgres_ready
from recovery_mail import configured_sender
from speech_assessment import InvalidAudio, checked_wav, assessment_from_sdk, azure_scripted_assess, MAX_WAV_BYTES
from speech_blend import blend_assessment, groq_whisper_transcribe

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
CREATE TABLE IF NOT EXISTS speech_usage(
 user_id INTEGER NOT NULL REFERENCES users(id), day TEXT NOT NULL,
 requests INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(user_id,day)
);

CREATE TABLE IF NOT EXISTS login_throttle(
 identity TEXT PRIMARY KEY, failures INTEGER NOT NULL, first_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS password_reset_tokens(
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
 expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS email_verifications(
 user_id INTEGER PRIMARY KEY REFERENCES users(id), verified_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_tokens(
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
 expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS verification_token_user ON verification_tokens(user_id);
CREATE TABLE IF NOT EXISTS verification_throttle(
 identity TEXT PRIMARY KEY, attempts INTEGER NOT NULL, first_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS password_reset_user ON password_reset_tokens(user_id);
CREATE TABLE IF NOT EXISTS recovery_throttle(
 identity TEXT PRIMARY KEY, attempts INTEGER NOT NULL, first_at INTEGER NOT NULL
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
               allowed_origins: tuple[str, ...] | None = None,
               recovery_sender: Callable[[str, str], None] | None = None,
               verification_sender: Callable[[str, str], None] | None = None,
               speech_enabled: bool | None = None,
               speech_assessor: Callable | None = None,
               postgres_url: str | None = None,
               speech_blend_enabled: bool | None = None,
               speech_transcriber: Callable | None = None) -> Flask:
    pg_url = postgres_url or os.environ.get("PTP_FAMILY_DATABASE_URL")
    path = database_path or os.environ.get("PTP_FAMILY_DB")
    catalog = catalog_path or os.environ.get("PTP_FAMILY_CATALOG")
    if not catalog or (not path and not pg_url) or path == ":memory:":
        raise RuntimeError("Explicit durable Postgres or SQLite and PTP_FAMILY_CATALOG required")
    if pg_url and path:
        raise RuntimeError("Select exactly one V2 account storage backend")
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
    speech_references = {
        item["id"]: item["polish"] for lesson in raw["lessons"]
        for item in lesson["items"]
        if isinstance(item.get("polish"), str) and 1 <= len(item["polish"]) <= 300
        and item.get("referenceReview") != "practice_only"
    }
    speech_segments = {
        item["id"]: item["pronunciationSegments"]["segments"]
        for lesson in raw["lessons"] for item in lesson["items"]
        if item["id"] in speech_references and
        isinstance(item.get("pronunciationSegments"), dict) and
        item["pronunciationSegments"].get("method") in ("authored-v1", "editorial-draft-v1", "draft-orthographic-v1") and
        isinstance(item["pronunciationSegments"].get("segments"), list) and
        1 <= len(item["pronunciationSegments"]["segments"]) <= 32 and
        all(isinstance(part, str) and part for part in item["pronunciationSegments"]["segments"]) and
        "".join(item["pronunciationSegments"]["segments"]) == item["polish"]
    }
    speech_active = (os.environ.get("PTP_SPEECH_ENABLED") == "1") if speech_enabled is None else speech_enabled
    blend_active = (os.environ.get("PTP_SPEECH_BLEND_ENABLED") == "1") if speech_blend_enabled is None else speech_blend_enabled
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if blend_active and not speech_active:
        raise RuntimeError("Speech blend cannot run without explicitly enabled Azure speech")
    if blend_active and speech_transcriber is None and (
        os.environ.get("PTP_GROQ_FREE_CONFIRMED") != "1" or
        os.environ.get("PTP_GROQ_NO_PAID_BILLING") != "1" or
        not groq_key or not groq_key.isascii() or not groq_key.isprintable()
    ):
        raise RuntimeError("Speech blend requires explicitly confirmed no-paid Groq plan and a private API key")
    speech_key = os.environ.get("AZURE_SPEECH_KEY", "")
    speech_region = os.environ.get("AZURE_SPEECH_REGION", "")
    if speech_active and speech_assessor is None:
        if (os.environ.get("PTP_SPEECH_F0_CONFIRMED") != "1" or
                os.environ.get("PTP_SPEECH_NO_PAID_BILLING") != "1" or
                not speech_key or not speech_key.isascii() or not speech_key.isprintable() or
                speech_region != "germanywestcentral"):
            raise RuntimeError("Speak assessment requires explicitly confirmed F0/no-paid resource and valid private Azure key/region")
    assess = speech_assessor or azure_scripted_assess
    transcribe = speech_transcriber or groq_whisper_transcribe
    origins = allowed_origins if allowed_origins is not None else tuple(
        x.strip() for x in os.getenv("PTP_FAMILY_ORIGINS", "").split(",") if x.strip()
    )
    if any("*" in x or not x.startswith(("https://", "http://localhost:", "http://127.0.0.1:")) for x in origins):
        raise RuntimeError("Family origins must be exact HTTPS or local development URLs")
    mail_sender = recovery_sender or configured_sender("recovery")
    signup_sender = verification_sender or configured_sender("verification")
    app = Flask(__name__)
    # WAV uploads are allowed only on the authenticated opt-in speech route.
    # All other routes preserve their previous 16 kB request limit.
    app.config["MAX_CONTENT_LENGTH"] = MAX_WAV_BYTES + 2000
    app.config["JSON_SORT_KEYS"] = True
    if pg_url:
        # Fail closed: schema migration is a separate reviewed operator action.
        # Never create/overwrite V1 public tables or identities at app startup.
        if not postgres_ready(pg_url):
            raise RuntimeError("Required isolated ptp_v2 Neon schema is unavailable")
    else:
        # SQLite remains for local development and existing hermetic CI.
        # Production Render Free must never persist accounts to its ephemeral disk.
        path = prepare_database(path)
        with sqlite3.connect(path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            con.executescript(DDL)

    def db():
        if "db" not in g:
            if pg_url:
                g.db = open_postgres(pg_url)
            else:
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
            # Expose strictly duration-only metrics; never provider transcripts,
            # request identifiers, credentials or audio metadata.
            response.headers["Access-Control-Expose-Headers"] = "Server-Timing"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.before_request
    def guard():
        if (request.path not in ("/api/v2/family/speech/assess",
                                  "/api/v2/family/speech/assess-blend") and
                request.content_length is not None and request.content_length > 16_000):
            return jsonify(error="request_too_large"), 413
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
                   JOIN email_verifications v ON v.user_id=u.id
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

    @app.post("/api/v2/family/speech/assess")
    @auth
    def assess_speech(user):
        """Explicit adult/user-authorized provider upload, no persisted voice or score."""
        if not speech_active:
            return fail("speech_assessment_unavailable", 503)
        if (request.mimetype != "multipart/form-data" or
                request.form.get("approve_azure_audio_upload") != "yes"):
            return fail("explicit_voice_upload_consent_required")
        item_id = request.form.get("item_id")
        if not isinstance(item_id, str) or item_id not in speech_references:
            return fail("built_in_lesson_item_required")
        audio = request.files.get("audio")
        if audio is None or audio.mimetype not in ("audio/wav", "audio/x-wav", "audio/wave"):
            return fail("invalid_audio")
        try:
            raw_audio = audio.read(MAX_WAV_BYTES + 1)
            duration, checked = checked_wav(raw_audio)
        except InvalidAudio as exc:
            return fail(str(exc))
        # Record request allowance atomically BEFORE the provider SDK invocation.
        # This is a durable cap across processes/restarts; do not auto-refund
        # failures (the SDK may have consumed the provider request).
        day = datetime.now(timezone.utc).date().isoformat()
        con = db()
        con.execute("BEGIN IMMEDIATE")
        local = con.execute(
            "SELECT requests FROM speech_usage WHERE user_id=? AND day=?",
            (user["id"], day)).fetchone()
        global_count = con.execute(
            "SELECT COALESCE(SUM(requests),0) FROM speech_usage WHERE day=?",
            (day,)).fetchone()[0]
        if (local and local["requests"] >= 12) or global_count >= 30:
            con.rollback()
            return fail("speech_daily_free_quota_guard", 429)
        con.execute(
            """INSERT INTO speech_usage(user_id,day,requests) VALUES(?,?,1)
               ON CONFLICT(user_id,day) DO UPDATE SET requests=requests+1""",
            (user["id"], day))
        con.commit()
        sdk_started = time.perf_counter()
        try:
            payload = assess(checked, speech_references[item_id], speech_key, speech_region)
            result = assessment_from_sdk(payload)
        except Exception:
            result = {"status": "inconclusive", "reason": "provider_unavailable"}
        sdk_ms = round(max(0, time.perf_counter() - sdk_started) * 1000, 1)
        # These are ephemeral response-header durations, never database logs,
        # persistent telemetry, private speech identifiers or a score.
        # SDK time includes recognition setup, transport and remote processing.
        # The service intentionally does not write raw voice, transcriptions,
        # word/phoneme scores or result history. Never award XP using raw PA.
        response = jsonify({"item_id": item_id, "engine": "azure-pl-PL-scripted",
                            "audio_seconds": round(duration, 2), **result})
        response.headers["Server-Timing"] = f"speech-sdk;dur={sdk_ms}"
        return response

    @app.post("/api/v2/family/speech/assess-blend")
    @auth
    def assess_blended_speech(user):
        """One explicitly approved recording to Azure then Groq, no history."""
        if not speech_active or not blend_active:
            return fail("speech_blend_unavailable", 503)
        if (request.mimetype != "multipart/form-data" or
                request.form.get("approve_azure_audio_upload") != "yes" or
                request.form.get("approve_groq_audio_upload") != "yes"):
            return fail("explicit_both_voice_upload_consents_required")
        item_id = request.form.get("item_id")
        if (not isinstance(item_id, str) or
                item_id not in speech_references or item_id not in speech_segments):
            return fail("pronunciation_segments_required")
        audio = request.files.get("audio")
        if audio is None or audio.mimetype not in ("audio/wav","audio/x-wav","audio/wave"):
            return fail("invalid_audio")
        try:
            duration, checked = checked_wav(audio.read(MAX_WAV_BYTES+1))
        except InvalidAudio as exc:
            return fail(str(exc))
        # Existing durable per-user/global limit counts each attempt before
        # external requests. No automatic retry or provider cost refund.
        day=datetime.now(timezone.utc).date().isoformat()
        con=db()
        con.execute("BEGIN IMMEDIATE")
        local=con.execute("SELECT requests FROM speech_usage WHERE user_id=? AND day=?",
                          (user["id"],day)).fetchone()
        total=con.execute("SELECT COALESCE(SUM(requests),0) FROM speech_usage WHERE day=?",
                          (day,)).fetchone()[0]
        if (local and local["requests"]>=12) or total>=30:
            con.rollback()
            return fail("speech_daily_free_quota_guard",429)
        con.execute("""INSERT INTO speech_usage(user_id,day,requests) VALUES(?,?,1)
                    ON CONFLICT(user_id,day) DO UPDATE SET requests=requests+1""",
                    (user["id"],day))
        con.commit()
        started=time.perf_counter()
        try:
            azure=assessment_from_sdk(assess(checked,speech_references[item_id],
                                              speech_key,speech_region))
            if azure["status"]=="ok":
                hypothesis=transcribe(checked,groq_key)
                result=blend_assessment(azure,speech_references[item_id],
                                        speech_segments[item_id],hypothesis)
            else:
                result={"status":"inconclusive","reason":"provider_inconclusive"}
        except Exception:
            # Never expose/persist recording, raw Whisper text or provider error.
            result={"status":"inconclusive","reason":"provider_unavailable"}
        elapsed=round(max(0,time.perf_counter()-started)*1000,1)
        response=jsonify({"item_id":item_id,"audio_seconds":round(duration,2),**result})
        response.headers["Server-Timing"]=f"speech-blend;dur={elapsed}"
        return response

    @app.get("/api/v2/family/health")
    def health():
        return jsonify(ok=True, version=1, catalog_items=len(known),
                       password_recovery_available=mail_sender is not None,
                       email_verification_available=signup_sender is not None)

    def verification_limit(identity: str, threshold: int, now: int) -> bool:
        con = db()
        row = con.execute("SELECT attempts,first_at FROM verification_throttle WHERE identity=?",
                          (identity,)).fetchone()
        fresh = not row or now-row["first_at"] >= 3600
        attempts = 1 if fresh else row["attempts"] + 1
        con.execute("""INSERT INTO verification_throttle(identity,attempts,first_at) VALUES(?,?,?)
                 ON CONFLICT(identity) DO UPDATE
                 SET attempts=excluded.attempts,first_at=excluded.first_at""",
                    (identity, attempts, now if fresh else row["first_at"]))
        return attempts > threshold

    def issue_verification(user_id: int, email: str, now: int) -> bool:
        """Persist a hashed, replaceable proof of mailbox control before mailing."""
        con = db()
        code = secrets.token_urlsafe(32)
        hashed = _hash(code)
        con.execute("DELETE FROM verification_tokens WHERE user_id=?", (user_id,))
        con.execute("INSERT INTO verification_tokens VALUES(?,?,?)",
                    (hashed, user_id, now+1800))
        try:
            signup_sender(email, code)
        except Exception:
            con.execute("DELETE FROM verification_tokens WHERE token_hash=?", (hashed,))
            return False
        return True

    @app.post("/api/v2/family/signup")
    def signup():
        if signup_sender is None:
            return fail("email_verification_unavailable", 503)
        data = _json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        if (not isinstance(email,str) or not isinstance(name,str) or
                not isinstance(password,str)):
            return fail("invalid_registration")
        email = email.strip().lower()
        name = name.strip()
        if (not EMAIL.fullmatch(email) or not 12 <= len(password) <= 256 or
                not 1 <= len(name) <= 48):
            return fail("invalid_registration")
        salt = secrets.token_hex(16)
        con = db()
        now = _now()
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM verification_throttle WHERE first_at<?",(now-3600,))
        limited_email = verification_limit("registration:email:"+_hash(email),3,now)
        limited_network = verification_limit(
            "registration:network:"+_hash(str(request.remote_addr)),20,now)
        if limited_email or limited_network:
            con.commit()
            return fail("too_many_attempts",429)
        try:
            user_id = con.execute(
                "INSERT INTO users(email,name,salt,password_hash) VALUES(?,?,?,?) RETURNING id",
                (email,name,salt,_password(password,salt))).fetchone()["id"]
        except (sqlite3.IntegrityError, PgIntegrityError):
            con.rollback()
            return fail("account_unavailable",409)
        # A pending signup never becomes an authenticated family member.
        # Mail failure removes the incomplete account to allow a clean retry.
        if not issue_verification(user_id,email,now):
            con.execute("DELETE FROM users WHERE id=?", (user_id,))
            con.commit()
            return fail("verification_delivery_unavailable",503)
        con.commit()
        return jsonify(created=True,verification_required=True),201

    @app.post("/api/v2/family/verification/resend")
    def resend_verification():
        if signup_sender is None:
            return fail("email_verification_unavailable",503)
        data = _json()
        email = data.get("email")
        password = data.get("password")
        if not isinstance(email,str) or not EMAIL.fullmatch(email.strip().lower()) or not isinstance(password,str):
            return fail("invalid_credentials",401)
        email = email.strip().lower()
        con = db()
        now = _now()
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM verification_throttle WHERE first_at<?", (now-3600,))
        by_email = verification_limit("email:"+_hash(email),3,now)
        by_network = verification_limit("network:"+_hash(str(request.remote_addr)),20,now)
        row = con.execute("""SELECT u.id,u.salt,u.password_hash,v.verified_at
                             FROM users u LEFT JOIN email_verifications v ON v.user_id=u.id
                             WHERE u.email=?""",(email,)).fetchone()
        if (not row or row["verified_at"] is not None or by_email or by_network or
                not hmac.compare_digest(_password(password,row["salt"]),row["password_hash"])):
            con.commit()
            return jsonify(accepted=True),202
        issue_verification(row["id"],email,now)
        con.commit()
        return jsonify(accepted=True),202

    @app.post("/api/v2/family/verification/confirm")
    def confirm_verification():
        if signup_sender is None:
            return fail("email_verification_unavailable",503)
        data = _json()
        email = data.get("email")
        code = data.get("code")
        if (not isinstance(email,str) or not EMAIL.fullmatch(email.strip().lower()) or
                not isinstance(code,str) or re.fullmatch(r"[A-Za-z0-9_-]{43}",code) is None):
            return fail("invalid_or_expired_code")
        con = db()
        now = _now()
        con.execute("BEGIN IMMEDIATE")
        record = con.execute(
            """SELECT u.id FROM verification_tokens t
               JOIN users u ON u.id=t.user_id
               LEFT JOIN email_verifications v ON v.user_id=u.id
               WHERE u.email=? AND t.token_hash=? AND t.expires_at>? AND v.user_id IS NULL""",
            (email.strip().lower(),_hash(code),now)).fetchone()
        if not record:
            con.rollback()
            return fail("invalid_or_expired_code")
        con.execute("INSERT INTO email_verifications VALUES(?,?)",(record["id"],now))
        con.execute("DELETE FROM verification_tokens WHERE user_id=?", (record["id"],))
        # Legacy unverified sessions must never revive automatically after verification.
        con.execute("DELETE FROM sessions WHERE user_id=?", (record["id"],))
        con.commit()
        return jsonify(verified=True),200

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
        row = con.execute("""SELECT u.id,u.name,u.email,u.salt,u.password_hash,
                             v.verified_at FROM users u
                             LEFT JOIN email_verifications v ON v.user_id=u.id
                             WHERE u.email=?""", (email,)).fetchone()
        valid = row is not None and hmac.compare_digest(_password(pw, row["salt"]), row["password_hash"])
        if not valid:
            fresh = not throttle or now-throttle["first_at"] >= 900
            first = now if fresh else throttle["first_at"]
            count = 1 if fresh else throttle["failures"]+1
            con.execute("""INSERT INTO login_throttle(identity,failures,first_at) VALUES(?,?,?)
                         ON CONFLICT(identity) DO UPDATE
                         SET failures=excluded.failures,first_at=excluded.first_at""", (key,count,first))
            return fail("invalid_credentials", 401)
        if row["verified_at"] is None:
            return fail("email_verification_required", 403)
        con.execute("DELETE FROM login_throttle WHERE identity=?", (key,))
        token = secrets.token_urlsafe(32)
        con.execute("INSERT INTO sessions VALUES(?,?,?)", (_hash(token),row["id"],now+7*86400))
        return jsonify(token=token, user={"id":row["id"],"name":row["name"]})

    def recovery_limit(identity: str, threshold: int, window: int, now: int) -> bool:
        """Bound mail requests for both destination and requesting network."""
        con = db()
        row = con.execute(
            "SELECT attempts,first_at FROM recovery_throttle WHERE identity=?", (identity,)
        ).fetchone()
        fresh = not row or now - row["first_at"] >= window
        attempts = 1 if fresh else row["attempts"] + 1
        first = now if fresh else row["first_at"]
        con.execute("""INSERT INTO recovery_throttle(identity,attempts,first_at) VALUES(?,?,?)
                 ON CONFLICT(identity) DO UPDATE
                 SET attempts=excluded.attempts,first_at=excluded.first_at""",
                    (identity, attempts, first))
        return attempts > threshold

    @app.post("/api/v2/family/recovery/request")
    def request_recovery():
        if mail_sender is None:
            return fail("password_recovery_unavailable", 503)
        value = _json().get("email")
        if not isinstance(value, str) or not EMAIL.fullmatch(value.strip().lower()):
            return fail("invalid_email")
        email = value.strip().lower()
        now = _now()
        con = db()
        # Never include email, token, SMTP exception, or account existence in response/logs.
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM password_reset_tokens WHERE expires_at<=?", (now,))
        con.execute("DELETE FROM recovery_throttle WHERE first_at<?", (now-3600,))
        limited_email = recovery_limit("email:"+_hash(email), 3, 3600, now)
        limited_ip = recovery_limit("network:"+_hash(str(request.remote_addr)), 20, 3600, now)
        row = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not row or limited_email or limited_ip:
            con.commit()
            return jsonify(accepted=True), 202
        code = secrets.token_urlsafe(32)
        token_hash = _hash(code)
        con.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["id"],))
        con.execute("INSERT INTO password_reset_tokens VALUES(?,?,?)",
                    (token_hash, row["id"], now+900))
        con.commit()
        try:
            mail_sender(email, code)
        except Exception:
            # Do not expose delivery success or existence; discard undelivered token.
            con.execute("DELETE FROM password_reset_tokens WHERE token_hash=?", (token_hash,))
        return jsonify(accepted=True), 202

    @app.post("/api/v2/family/recovery/complete")
    def complete_recovery():
        if mail_sender is None:
            return fail("password_recovery_unavailable", 503)
        data = _json()
        code = data.get("code")
        password = data.get("new_password")
        if (not isinstance(code, str) or
                re.fullmatch(r"[A-Za-z0-9_-]{43}", code) is None or
                not isinstance(password, str) or not 12 <= len(password) <= 256):
            return fail("invalid_or_expired_code")
        con = db()
        now = _now()
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            """SELECT t.user_id,u.salt,u.password_hash
               FROM password_reset_tokens t JOIN users u ON t.user_id=u.id
               WHERE t.token_hash=? AND t.expires_at>?""",
            (_hash(code), now)
        ).fetchone()
        if not row:
            con.rollback()
            return fail("invalid_or_expired_code")
        salt = secrets.token_hex(16)
        con.execute("UPDATE users SET salt=?, password_hash=? WHERE id=?",
                    (salt, _password(password, salt), row["user_id"]))
        con.execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
        con.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["user_id"],))
        con.commit()
        return jsonify(reset=True, sign_in_again=True)

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
        gid = con.execute("INSERT INTO families(name,owner_id) VALUES(?,?) RETURNING id",
                          (name,user["id"])).fetchone()["id"]
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

    @app.post("/api/v2/family/groups/<int:family_id>/members/remove")
    @auth
    def remove_member(user, family_id):
        """An organizer may expel another member and erase their group activity.

        An authenticated session for the removed user still exists for their
        own account and unrelated groups; every group route enforces membership.
        Previously redeemed invites stay consumed.
        """
        access = _owner_guard(user, family_id)
        if access:
            return access
        target = _json().get("member_id")
        if type(target) is not int or target <= 0 or target == user["id"]:
            return fail("invalid_member")
        con = db()
        con.execute("BEGIN IMMEDIATE")
        owner = con.execute("SELECT owner_id FROM families WHERE id=?",
                            (family_id,)).fetchone()
        if not owner or owner["owner_id"] != user["id"]:
            con.rollback()
            return fail("owner_only", 403)
        present = con.execute(
            "SELECT 1 FROM members WHERE family_id=? AND user_id=?",
            (family_id, target)).fetchone()
        if not present:
            con.rollback()
            return fail("member_not_found", 404)
        removed = con.execute(
            "DELETE FROM activities WHERE family_id=? AND user_id=?",
            (family_id, target)).rowcount
        con.execute("DELETE FROM members WHERE family_id=? AND user_id=?",
                    (family_id, target))
        # Any other leaked unused code could otherwise let an expelled member
        # rejoin immediately. Invalidate pending invitations together with removal.
        revoked = con.execute(
            "DELETE FROM invitations WHERE family_id=? AND redeemed_by IS NULL",
            (family_id,)).rowcount
        con.commit()
        return jsonify(removed=True, member_id=target, removed_activities=removed,
                       revoked_invites=revoked)

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
        con.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user["id"],))
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
        con.execute("DELETE FROM speech_usage WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM members WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM verification_tokens WHERE user_id=?", (user["id"],))
        con.execute("DELETE FROM email_verifications WHERE user_id=?", (user["id"],))
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
