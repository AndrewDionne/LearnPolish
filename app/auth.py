from flask import Blueprint, request, jsonify, current_app, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt, datetime

from .models import db, User
from .config import ADMIN_EMAIL   # still fine to use for initial admin flag
from flask_cors import cross_origin

auth_bp = Blueprint("auth", __name__)

# ----------------------------
# JWT helpers
# ----------------------------

def create_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),  # 7 days
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def _get_bearer_token():
    """Read Bearer token from header, or ?token= query (for HTML navigations)."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return request.args.get("token") or None


# Decorator for JSON API routes (returns JSON 401 on failure)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
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


# Decorator for (optional) server HTML routes: redirect to static /login.html on failure
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            # redirect to the static login page (works locally + GH Pages link if FRONTEND_BASE_URL set)
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
# API routes
# ----------------------------

@auth_bp.route("/signup", methods=["POST"])
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

    # Mark admin at creation if matches configured admin email
    if ADMIN_EMAIL and email == (ADMIN_EMAIL or "").lower():
        user.is_admin = True

    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}
    }), 201


@auth_bp.route("/login", methods=["POST"])
@cross_origin()
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password"}), 401

    token = create_token(user.id)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}
    }), 200


@auth_bp.route("/me", methods=["GET"])
@cross_origin()
@token_required
def me(current_user):
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_admin": current_user.is_admin
    })

# ----------------------------
# Password reset
# ----------------------------

@auth_bp.route("/reset_request", methods=["POST"])
@cross_origin()
def reset_request():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    # Privacy-friendly response (don’t reveal whether the email exists)
    if not user:
        return jsonify({"message": "If the email exists, a reset link has been sent."}), 200

    payload = {
        "sub": user.id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    token = token if isinstance(token, str) else token.decode("utf-8")

    # Build a link to the static reset page (works in GH Pages if FRONTEND_BASE_URL set)
    base = (current_app.config.get("FRONTEND_BASE_URL") or "").rstrip("/")
    reset_link = (base + "/reset_confirm.html?token=" + token) if base else ("/reset_confirm.html?token=" + token)

    # TODO: send via email service
    print("🔗 Password reset link:", reset_link)

    return jsonify({"message": "If the email exists, a reset link has been sent."}), 200


@auth_bp.route("/reset_confirm", methods=["POST"])
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
