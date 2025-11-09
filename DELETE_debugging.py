#!/usr/bin/env python3
"""
Debug external connections for Path to POLISH.

What it checks (read-only by default):
  - Render backend health + CORS preflight (/api/healthz, OPTIONS to /api/token)
  - GitHub API auth (token scopes), repo access
  - Cloudflare R2 (upload tiny object, read back, delete)
  - Email (SMTP login; optionally send a message)

Optional write checks (explicit flags):
  - --push: create+push a temporary branch 'debug-conn-<ts>' then delete it
  - --email you@domain: actually send a test email

Run examples:
  python debugging.py --all
  python debugging.py --render --origin https://andrewdionne.github.io
  python debugging.py --r2
  python debugging.py --github --push
  python debugging.py --email you@example.com
"""

import os, sys, time, argparse, subprocess, tempfile, hashlib
from datetime import datetime, timezone
import requests

# Auto-load .env if present (pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- Pretty output ----------------------------------------------------------
def ok(msg):    print(f"✅ {msg}")
def warn(msg):  print(f"⚠️  {msg}")
def err(msg):   print(f"❌ {msg}")

# ---- Env helpers ------------------------------------------------------------
def need(name, default=None):
    v = os.getenv(name, default)
    if v is None or (isinstance(v,str) and v.strip()==""):
        raise SystemExit(f"Missing required env: {name}")
    return v

# ---- Render test ------------------------------------------------------------
def test_render(base, origin, timeout=45):
    base = base.rstrip("/")
    candidates = ["/api/healthz", "/healthz", "/api/ping", "/ping", "/"]
    ok_ep = None
    for ep in candidates:
        try:
            r = requests.get(f"{base}{ep}", headers={"Origin": origin}, timeout=timeout)
            r.raise_for_status()
            ao = r.headers.get("Access-Control-Allow-Origin")
            ok(f"Render GET {ep}: {r.status_code}; ACAO={ao!r}")
            ok_ep = ep
            break
        except Exception as e:
            warn(f"GET {ep} failed: {e}")
    if not ok_ep:
        err("All health endpoints failed")
        return False

    try:
        h = {
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        r = requests.options(f"{base}/api/token", headers=h, timeout=timeout)
        if r.status_code in (200, 204):
            ao = r.headers.get("Access-Control-Allow-Origin")
            am = r.headers.get("Access-Control-Allow-Methods")
            ah = r.headers.get("Access-Control-Allow-Headers")
            ok(f"Render preflight OK: {r.status_code}; ACAO={ao!r}; Methods={am!r}; Headers={ah!r}")
        else:
            warn(f"Render preflight returned {r.status_code} (expected 204/200)")
    except Exception as e:
        err(f"Render preflight failed: {e}")
        return False
    return True


# ---- GitHub tests -----------------------------------------------------------
def _detect_repo():
    try:
        url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
        # formats: https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if url.startswith("git@"):
            # git@github.com:owner/repo.git
            path = url.split(":",1)[1]
        else:
            # https://.../owner/repo.git
            path = url.split("github.com/",1)[1]
        if path.endswith(".git"): path = path[:-4]
        owner, repo = path.split("/",1)
        return owner, repo
    except Exception:
        return None, None

def test_github_api(token, owner=None, repo=None):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    try:
        u = s.get("https://api.github.com/user", timeout=15)
        u.raise_for_status()
        scopes = u.headers.get("X-OAuth-Scopes","")
        ok(f"GitHub token OK; scopes={scopes}")
    except Exception as e:
        err(f"GitHub /user failed: {e}")
        return False

    if not (owner and repo):
        d_owner, d_repo = _detect_repo()
        owner = owner or d_owner
        repo  = repo or d_repo
    if not (owner and repo):
        warn("Could not detect owner/repo from git; skipping repo access check.")
        return True

    try:
        r = s.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=15)
        r.raise_for_status()
        default_branch = (r.json().get("default_branch") or "main")
        ok(f"Repo access OK: {owner}/{repo} (default={default_branch})")
        return True
    except Exception as e:
        err(f"GitHub repo access failed: {e}")
        return False

def test_github_push(token, owner=None, repo=None):
    # Create a temp branch, push, then delete. Requires 'repo' scope.
    owner, repo = owner or _detect_repo()[0], repo or _detect_repo()[1]
    if not (owner and repo):
        err("Cannot resolve owner/repo for push test.")
        return False

    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    branch = f"debug-conn-{now}"

    # Create commit with tiny file (no-op content)
    try:
        with open(".debug_connection.txt", "w", encoding="utf-8") as f:
            f.write(f"debug connection {now}\n")
        subprocess.check_call(["git", "add", ".debug_connection.txt"])
        subprocess.check_call(["git", "commit", "-m", f"chore: debug connection {now} [skip ci]"])
    except subprocess.CalledProcessError as e:
        err(f"git add/commit failed (do you have a clean repo?): {e}")
        return False

    try:
        subprocess.check_call(["git", "branch", branch])
        subprocess.check_call(["git", "push", "-u", "origin", branch])
        ok(f"Pushed branch {branch} to origin")
    except subprocess.CalledProcessError as e:
        err(f"Push failed: {e}")
        return False
    finally:
        # clean local branch
        try: subprocess.check_call(["git", "switch", "-"])  # back to previous
        except Exception: pass
        try: subprocess.check_call(["git", "branch", "-D", branch])
        except Exception: pass
        # keep the debug file but unstage it
        try: subprocess.check_call(["git", "reset", "HEAD", ".debug_connection.txt"])
        except Exception: pass

    # Delete remote branch via API
    try:
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {token}"
        r = s.delete(f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}", timeout=15)
        # GitHub returns 204 on success
        if r.status_code == 204:
            ok(f"Deleted remote branch {branch}")
        else:
            warn(f"Remote branch delete returned {r.status_code} (you can delete manually).")
        return True
    except Exception as e:
        warn(f"Failed to delete remote branch: {e} (delete manually if needed).")
        return True

# ---- Cloudflare R2 (S3-compatible) -----------------------------------------
def test_r2(endpoint, access_key, secret_key, bucket):
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except Exception:
        err("boto3 not installed. pip install boto3")
        return False

    sess = boto3.session.Session()
    s3 = sess.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=BotoConfig(s3={"addressing_style": "virtual"}),
    )
    key = f"debug/conn-{int(time.time())}.txt"
    body = b"ok"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/plain")
        ok(f"R2 put_object s3://{bucket}/{key}")
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj["Body"].read()
        if data != body:
            raise RuntimeError("R2 read mismatch")
        ok("R2 get_object verified")
        s3.delete_object(Bucket=bucket, Key=key)
        ok("R2 delete_object OK")
        return True
    except Exception as e:
        err(f"R2 test failed: {e}")
        return False

# ---- Email (SMTP) ----------------------------------------------------------
def test_email(smtp_host, smtp_port, user, pwd, to_addr=None, from_addr=None, from_name=None):
    import smtplib, ssl
    from email.message import EmailMessage
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as s:
            s.ehlo()
            # TLS for 587; if you switch to 465 you’d use SMTP_SSL instead
            s.starttls(context=ctx)
            s.ehlo()
            s.login(user, pwd)
            ok(f"SMTP login OK: {smtp_host}:{smtp_port} as {user}")
            if to_addr:
                msg = EmailMessage()
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                sender = f"{from_name} <{from_addr}>" if from_name and from_addr else (from_addr or user)
                msg["From"] = sender
                msg["To"] = to_addr
                msg["Subject"] = f"Path to POLISH: debug email {now}"
                msg.set_content(f"This is a debug email sent at {now}.")
                s.send_message(msg)
                ok(f"Test email sent to {to_addr}")
        return True
    except Exception as e:
        err(f"SMTP test failed: {e}")
        return False


# ---- CLI -------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Path to POLISH external connections debug")
    p.add_argument("--all", action="store_true", help="Run all tests (read-only; no push, no email send)")
    p.add_argument("--render", action="store_true")
    p.add_argument("--origin", default="https://andrewdionne.github.io", help="Origin to use for preflight")
    p.add_argument("--github", action="store_true")
    p.add_argument("--push", action="store_true", help="Actually push a temporary branch to origin and delete it")
    p.add_argument("--r2", action="store_true")
    p.add_argument("--email", metavar="ADDR", help="Send a test email to ADDR (otherwise login-only)")
    p.add_argument("--owner", help="GitHub owner override")
    p.add_argument("--repo", help="GitHub repo override")
    args = p.parse_args()

    if args.all:
        args.render = args.github = args.r2 = True

    any_run = False

    # Render
    if args.render:
        any_run = True
        base = os.getenv("RENDER_BASE", "https://path-to-polish.onrender.com")
        ok(f"Testing Render at {base}")
        test_render(base, args.origin)

    # GitHub
    if args.github:
        any_run = True
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            raise SystemExit("Missing required env: GITHUB_TOKEN or GH_TOKEN")
        owner = args.owner or os.getenv("GITHUB_OWNER")
        repo  = args.repo  or os.getenv("GITHUB_REPO")
        ok("Testing GitHub API")
        if test_github_api(token, owner, repo) and args.push:
            ok("Testing Git push (temp branch)")
            test_github_push(token, owner, repo)


    # R2
    if args.r2:
        any_run = True
        endpoint   = need("R2_ENDPOINT")      # e.g. https://<accountid>.r2.cloudflarestorage.com
        access_key = need("R2_ACCESS_KEY_ID")
        secret_key = need("R2_SECRET_ACCESS_KEY")
        bucket     = need("R2_BUCKET")
        ok(f"Testing R2 bucket {bucket} at {endpoint}")
        test_r2(endpoint, access_key, secret_key, bucket)

    # Email
    if args.email is not None or os.getenv("EMAIL_CHECK"):
        any_run = True
        provider = (os.getenv("EMAIL_PROVIDER", "")).lower()
        from_addr = os.getenv("FROM_EMAIL") or None
        from_name = os.getenv("FROM_NAME") or None

        if provider == "ses_smtp":
            smtp_host = os.getenv("SES_SMTP_SERVER", "email-smtp.eu-north-1.amazonaws.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            user = need("SES_SMTP_USER")
            pwd  = need("SES_SMTP_PASS")
        else:
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("EMAIL_USER")
            pwd  = os.getenv("EMAIL_PASS")
            if not (user and pwd):
                raise SystemExit("Missing required env: EMAIL_USER and EMAIL_PASS (or set EMAIL_PROVIDER=ses_smtp and SES_SMTP_* vars)")

        ok(f"Testing SMTP at {smtp_host}:{smtp_port}")
        test_email(smtp_host, smtp_port, user, pwd, args.email, from_addr=from_addr, from_name=from_name)

    if not any_run:
        p.print_help()

if __name__ == "__main__":
    main()
