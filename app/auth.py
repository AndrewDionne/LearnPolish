# app/auth.py
from flask import Blueprint, request, jsonify, current_app, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt, datetime
import os, re

from flask_cors import cross_origin

from .models import db, User
from .config import ADMIN_EMAIL
from .emailer import send_email

try:
    import boto3
    from botocore.exceptions import ClientError
except Exception:
    boto3 = None
    class ClientError(Exception):
        pass

auth_bp = Blueprint("auth", __name__)

# ----------------------------
# JWT helpers
# ----------------------------
def create_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def _get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return request.args.get("token") or None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow CORS preflight without auth
        if request.method == "OPTIONS":
            return ("", 204)

        token = _get_bearer_token()
        if not token:
            return jsonify({"message": "Authorization token is missing"}), 401
        try:
            data = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
            user = User.query.get(data["sub"])
            if not user:
                raise ValueError("User not found")
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Authorization token has expired"}), 401
        except Exception as e:
            return jsonify({"message": "Authorization token is invalid", "error": str(e)}), 401
        return f(user, *args, **kwargs)
    return decorated


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            base = (current_app.config.get("FRONTEND_BASE_URL") or "").rstrip("/")
            login_url = (base + "/login.html") if base else "/login.html"
            return redirect(login_url)

        try:
            data = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
            user = User.query.get(data["sub"])
            if not user:
                base = (current_app.config.get("FRONTEND_BASE_URL") or "").rstrip("/")
                login_url = (base + "/login.html") if base else "/login.html"
                return redirect(login_url)
        except Exception:
            base = (current_app.config.get("FRONTEND_BASE_URL") or "").rstrip("/")
            login_url = (base + "/login.html") if base else "/login.html"
            return redirect(login_url)
        return f(user, *args, **kwargs)
    return decorated_function


# ----------------------------
# API bootstrap admin
# ----------------------------
@auth_bp.route("/admin/promote_me", methods=["POST", "OPTIONS"])
@cross_origin()
@token_required
def promote_me(current_user):
    admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    if not admin_email:
        return jsonify({"ok": False, "error": "ADMIN_EMAIL not set"}), 400

    if (current_user.email or "").lower() != admin_email:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    current_user.is_admin = True
    db.session.commit()
    return jsonify({"ok": True, "email": current_user.email, "is_admin": True})


# ----------------------------
# Auth routes
# ----------------------------
@auth_bp.route("/signup", methods=["POST", "OPTIONS"])
@cross_origin()
def signup():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    name = (data.get("name") or "").strip()

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "A user with this email already exists"}), 400

    pw_hash = generate_password_hash(password)
    user = User(email=email, password_hash=pw_hash, name=name)
    if ADMIN_EMAIL and email == (ADMIN_EMAIL or "").lower():
        user.is_admin = True

    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}
    }), 201


@auth_bp.route("/login", methods=["POST", "OPTIONS"])
@cross_origin()
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    if not getattr(user, "password_hash", None):
        current_app.logger.warning("User %s missing password hash", email)
        return jsonify({"message": "Password not set for this account. Use the reset link to create one."}), 400

    try:
        valid = check_password_hash(user.password_hash, password)
    except Exception as exc:
        current_app.logger.exception("Password hash check failed for user %s: %s", user.id, exc)
        return jsonify({"message": "Invalid email or password"}), 401

    if not valid:
        return jsonify({"message": "Invalid email or password"}), 401

    token = create_token(user.id)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}
    }), 200


@auth_bp.route("/token", methods=["GET"])
@cross_origin()
def token_ping():
    return jsonify({"ok": True, "authenticated": bool(_get_bearer_token())})


@auth_bp.route("/me", methods=["GET", "OPTIONS"])
@cross_origin()
@token_required
def me(current_user):
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_admin": current_user.is_admin
    })


# --- SES email identity helpers (admin-only) --------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _guess_ses_region() -> str:
    region = (
        os.getenv("SES_REGION")
        or os.getenv("AWS_SES_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
    )
    if region:
        return region

    host = os.getenv("SES_SMTP_SERVER") or os.getenv("SES_SMTP_HOST") or ""
    m = re.search(r"email-smtp\.([a-z0-9-]+)\.amazonaws\.com", host)
    return m.group(1) if m else "eu-north-1"


def _ses_client():
    if boto3 is None:
        raise RuntimeError("boto3 is not installed; add 'boto3>=1.34' to requirements.txt")

    region = _guess_ses_region()
    ak = os.getenv("SES_AWS_ACCESS_KEY_ID") or os.getenv("AWS_SES_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("SES_AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SES_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    if not ak or not sk:
        raise RuntimeError("Missing SES API creds: set SES_AWS_ACCESS_KEY_ID and SES_AWS_SECRET_ACCESS_KEY")

    session = boto3.Session(aws_access_key_id=ak, aws_secret_access_key=sk, region_name=region)
    return session.client("sesv2")


@auth_bp.route("/admin/ses/create_identity", methods=["POST", "OPTIONS"])
@cross_origin()
@token_required
def ses_create_identity(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "invalid_email"}), 400

    try:
        ses = _ses_client()
        resp = ses.create_email_identity(EmailIdentity=email)
        cfg = (os.getenv("SES_DEFAULT_CONFIG_SET") or "").strip()
        if cfg:
            try:
                ses.put_email_identity_configuration_set_attributes(
                    EmailIdentity=email,
                    ConfigurationSetName=cfg
                )
            except ClientError as e:
                return jsonify({
                    "ok": True,
                    "email": email,
                    "create": {
                        "IdentityType": resp.get("IdentityType"),
                        "VerifiedForSendingStatus": resp.get("VerifiedForSendingStatus"),
                    },
                    "warning": f"config_set_attach_failed: {e.response.get('Error', {}).get('Message', str(e))}"
                }), 200

        return jsonify({
            "ok": True,
            "email": email,
            "create": {
                "IdentityType": resp.get("IdentityType"),
                "VerifiedForSendingStatus": resp.get("VerifiedForSendingStatus"),
            }
        }), 200

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        msg  = e.response.get("Error", {}).get("Message", str(e))
        return jsonify({"ok": False, "error": code, "message": msg}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": "exception", "message": str(e)}), 500


@auth_bp.route("/admin/ses/get_identity", methods=["GET", "OPTIONS"])
@cross_origin()
@token_required
def ses_get_identity(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    email = (request.args.get("email") or "").strip()
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "invalid_email"}), 400

    try:
        ses = _ses_client()
        resp = ses.get_email_identity(EmailIdentity=email)
        return jsonify({
            "ok": True,
            "email": email,
            "status": resp.get("VerifiedStatus"),
            "sending_enabled": resp.get("VerifiedForSendingStatus"),
            "identity_type": resp.get("IdentityType"),
        }), 200
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        msg  = e.response.get("Error", {}).get("Message", str(e))
        return jsonify({"ok": False, "error": code, "message": msg}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": "exception", "message": str(e)}), 500


@auth_bp.route("/admin/ses/list_emails", methods=["GET", "OPTIONS"])
@cross_origin()
@token_required
def ses_list_emails(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    try:
        ses = _ses_client()
        out = []
        token = None
        while True:
            kwargs = {"PageSize": 50}
            if token:
                kwargs["NextToken"] = token
            resp = ses.list_email_identities(**kwargs)
            for item in resp.get("Items", []):
                if item.get("IdentityType") == "EMAIL_ADDRESS":
                    out.append({
                        "email": item.get("IdentityName"),
                        "sending_enabled": item.get("SendingEnabled"),
                    })
            token = resp.get("NextToken")
            if not token:
                break

        return jsonify({"ok": True, "items": out}), 200

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        msg  = e.response.get("Error", {}).get("Message", str(e))
        return jsonify({"ok": False, "error": code, "message": msg}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": "exception", "message": str(e)}), 500


# ----------------------------
# Password reset
# ----------------------------
@auth_bp.route("/reset_request", methods=["POST", "OPTIONS"])
@cross_origin()
def reset_request():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "If the email exists, a reset link has been sent."}), 200

    payload = {
        "sub": user.id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    token = token if isinstance(token, str) else token.decode("utf-8")

    base = (current_app.config.get("FRONTEND_BASE_URL")
            or current_app.config.get("APP_BASE_URL")
            or "").rstrip("/")
    reset_link = (base + "/reset_confirm.html?token=" + token) if base else ("/reset_confirm.html?token=" + token)

    try:
        subject = "Reset your Path to POLISH password"
        text = f"""Hi,

We received a request to reset your Path to POLISH password.

Reset your password using this link:
{reset_link}

If you didn’t request this, you can safely ignore this email.

Thanks,
Path to POLISH Support
"""
        html = f"""<html><body>
<p>Hi,</p>
<p>We received a request to reset your <b>Path to POLISH</b> password.</p>
<p><b>Reset your password using this link:</b><br>
<a href="{reset_link}">{reset_link}</a></p>
<p>If you didn’t request this, you can safely ignore this email.</p>
<p>Thanks,<br>Path to POLISH Support</p>
</body></html>"""
        send_email(subject=subject, text=text, html=html, to=[email], bcc=None, reply_to=None)
    except Exception as e:
        print("Reset email failed:", repr(e))

    return jsonify({"message": "If the email exists, a reset link has been sent."}), 200


@auth_bp.route("/reset_confirm", methods=["POST", "OPTIONS"])
@cross_origin()
def reset_confirm():
    data = request.get_json() or {}
    token = data.get("token")
    new_password = (data.get("password") or "").strip()

    if not token or not new_password:
        return jsonify({"message": "Token and new password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400

    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
        user = User.query.get(payload["sub"])
        if not user:
            return jsonify({"message": "User not found"}), 404

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({"message": "Password updated successfully"}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Reset token has expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid reset token"}), 400


# --- Compatibility + convenience routes ---
@auth_bp.route("/logout", methods=["POST", "OPTIONS"])
def logout():
    return ("", 204)


@auth_bp.route("/register", methods=["POST", "OPTIONS"])
def register():
    return signup()
