# app/debug_trace.py
from __future__ import annotations

import os
import re
import time
import json
import shlex
import threading
import subprocess
from functools import wraps
from typing import Any, Callable, Dict, List
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app

from .auth import token_required  # for admin-only endpoints

# --- Internal state -----------------------------------------------------------
TRACE_STATE = {
    "on": False,
    "capture_bodies": True,
    # Which URL paths to log request bodies for (substring match)
        "watch_paths": ["/api/"],  # capture every API call

    # Optional: limit to specific function names; empty = all decorated
    "watch_funcs": set(),  # e.g., {"_git_add_commit_push"}
}
_MAX = 800  # ring buffer size
_LOG: List[Dict[str, Any]] = []
_LOCK = threading.Lock()

# --- Helpers -----------------------------------------------------------------
def _redact(s: str | None) -> str | None:
    if not isinstance(s, str):
        return s
    redactions = [os.getenv("GITHUB_TOKEN") or "", os.getenv("GH_TOKEN") or ""]
    out = s
    for tok in redactions:
        if tok:
            out = out.replace(tok, "****")
    # Authorization: Bearer <...>
    out = re.sub(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9_\-\.=]+", r"\1****", out, flags=re.I)
    # PAT in URLs
    out = re.sub(r"https://([^:@/]+):[^@/]+@github\.com", r"https://\1:****@github.com", out)
    return out

def _append(kind: str, data: Dict[str, Any]) -> None:
    rec = {"ts": time.time(), "kind": kind, **data}
    with _LOCK:
        _LOG.append(rec)
        if len(_LOG) > _MAX:
            del _LOG[: len(_LOG) - _MAX]

def trace(func: Callable) -> Callable:
    """Decorator for function call tracing."""
    fname = func.__name__

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not TRACE_STATE["on"]:
            return func(*args, **kwargs)
        if TRACE_STATE["watch_funcs"] and fname not in TRACE_STATE["watch_funcs"]:
            return func(*args, **kwargs)
        t0 = time.time()
        meta = {"func": fname}
        # Avoid dumping giant objects; keep arg names only
        try:
            meta["args"] = [type(a).__name__ for a in args]
            meta["kwargs"] = {k: type(v).__name__ for k, v in kwargs.items()}
        except Exception:
            pass
        _append("call", meta)
        try:
            res = func(*args, **kwargs)
            _append("ret", {"func": fname, "ms": int((time.time() - t0) * 1000)})
            return res
        except Exception as e:
            _append("err", {"func": fname, "ms": int((time.time() - t0) * 1000), "error": str(e)})
            raise

    return wrapper

def _git(cmd: str, root: Path) -> str:
    """Run a git command for env dump (non-fatal)."""
    try:
        out = subprocess.check_output(shlex.split(cmd), cwd=str(root))
        return out.decode("utf-8", "ignore").strip()
    except Exception as e:
        return f"ERROR: {e!r}"

# --- Blueprint ---------------------------------------------------------------
debug_api = Blueprint("debug_api", __name__)

@debug_api.before_app_request
def _log_request():
    if not TRACE_STATE["on"]:
        return
    p = request.path or ""
    watched = any(w in p for w in TRACE_STATE["watch_paths"])
    if not watched:
        return
    rec: Dict[str, Any] = {
        "path": p,
        "method": request.method,
        "remote_addr": request.remote_addr,
    }
    try:
        # Redact auth header
        hdrs = {k: ("****" if k.lower() == "authorization" else v) for k, v in request.headers.items()}
        rec["headers"] = hdrs
        if TRACE_STATE["capture_bodies"] and request.method in ("POST", "PUT", "PATCH"):
            body = request.get_data(as_text=True) or ""
            rec["body"] = _redact(body)[:4000]
    except Exception:
        pass
    _append("request", rec)

# Admin: enable tracing
@debug_api.route("/admin/trace_on", methods=["POST"])
@token_required
def trace_on(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    body = request.get_json(silent=True) or {}
    TRACE_STATE["on"] = True
    TRACE_STATE["capture_bodies"] = bool(body.get("capture_bodies", True))
    # optional filters
    paths = body.get("watch_paths")
    if isinstance(paths, list) and paths:
        TRACE_STATE["watch_paths"] = [str(p) for p in paths]
    funcs = body.get("watch_funcs")
    if isinstance(funcs, list):
        TRACE_STATE["watch_funcs"] = set(str(x) for x in funcs)
    _append("note", {"msg": "trace_on", "state": {**TRACE_STATE, "watch_funcs": list(TRACE_STATE["watch_funcs"])}})
    return jsonify({"ok": True, "trace": {**TRACE_STATE, "watch_funcs": list(TRACE_STATE["watch_funcs"])}})

# Admin: disable tracing
@debug_api.route("/admin/trace_off", methods=["POST"])
@token_required
def trace_off(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    TRACE_STATE["on"] = False
    TRACE_STATE["watch_funcs"] = set()
    return jsonify({"ok": True})

# Admin: dump trace
@debug_api.route("/admin/trace_dump", methods=["GET"])
@token_required
def trace_dump(current_user):
    _append("request", {"path": request.path, "method": request.method})
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    with _LOCK:
        out = list(_LOG)
    # redact any leftover secrets in string fields
    for rec in out:
        for k, v in list(rec.items()):
            if isinstance(v, str):
                rec[k] = _redact(v)
    return jsonify({"ok": True, "events": out})

# Admin: clear trace
@debug_api.route("/admin/trace_clear", methods=["POST"])
@token_required
def trace_clear(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    with _LOCK:
        _LOG.clear()
    return jsonify({"ok": True})

# Admin: quick env + git snapshot
@debug_api.route("/admin/env_dump", methods=["GET"])
@token_required
def env_dump(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    root = Path(current_app.root_path).parent
    # redact remote URLs
    remotes = _redact(_git("git remote -v", root))
    return jsonify({
        "ok": True,
        "env": {
            "HAS_GITHUB_TOKEN": bool(os.getenv("GITHUB_TOKEN")),
            "GITHUB_REPO_SLUG": os.getenv("GITHUB_REPO_SLUG"),
            "GIT_BRANCH": os.getenv("GIT_BRANCH"),
        },
        "git": {
            "branch": _git("git rev-parse --abbrev-ref HEAD", root),
            "status": _git("git status --porcelain", root),
            "remotes": remotes,
            "last_commit": _git("git log -1 --oneline", root),
        }
    })
# --- route inspector ----------------------------------------------------------
@debug_api.route("/admin/routes", methods=["GET"])
@token_required
def list_routes(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    rm = []
    for r in current_app.url_map.iter_rules():
        rm.append({
            "rule": str(r),
            "endpoint": r.endpoint,
            "methods": sorted(m for m in r.methods if m not in {"HEAD", "OPTIONS"}),
        })
    rm.sort(key=lambda x: x["rule"])
    return jsonify({"ok": True, "routes": rm})

@debug_api.route("/admin/which_handler", methods=["GET"])
@token_required
def which_handler(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    path = (request.args.get("path") or "").strip()
    if not path:
        return jsonify({"ok": False, "error": "path required, e.g. /api/create_set_v2"}), 400
    matches = []
    for r in current_app.url_map.iter_rules():
        if str(r) == path:
            matches.append({"rule": str(r), "endpoint": r.endpoint, "methods": sorted(r.methods)})
    return jsonify({"ok": True, "matches": matches})
