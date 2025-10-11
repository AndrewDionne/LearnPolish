# app/emailer.py
"""
Unified email sender for Path to POLISH.

Usage:
    from .emailer import send_email

    send_email(
        subject="Hello",
        text="Plain text body",
        html="<p>HTML body</p>",
        to=["person@example.com"],     # optional
        bcc=["a@x.com","b@y.com"],    # optional
        reply_to="you@domain.com"     # optional
    )

Providers:
- EMAIL_PROVIDER=ses_smtp   (requires SES_SMTP_USER/SES_SMTP_PASS; optionally SES_REGION/SES_SMTP_HOST/PORT)
- EMAIL_PROVIDER=gmail      (requires GMAIL_USER/GMAIL_APP_PASSWORD)
- EMAIL_PROVIDER=console    (prints to logs; dev only)
"""

from __future__ import annotations
import os, ssl, smtplib, socket
from email.message import EmailMessage

# -------- env --------
PROVIDER = (os.environ.get("EMAIL_PROVIDER") or "console").lower()

# Common “from”
FROM_EMAIL = os.environ.get("FROM_EMAIL") or os.environ.get("GMAIL_USER") or "no-reply@localhost"
FROM_NAME  = os.environ.get("FROM_NAME")  or "Path to POLISH"

# Gmail
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")

# SES SMTP
SES_REGION     = os.environ.get("SES_REGION") or "eu-north-1"
SES_SMTP_HOST  = os.environ.get("SES_SMTP_HOST") or f"email-smtp.{SES_REGION}.amazonaws.com"
SES_SMTP_PORT  = int(os.environ.get("SES_SMTP_PORT") or "587")   # STARTTLS default
SES_SMTP_USER  = os.environ.get("SES_SMTP_USER") or ""
SES_SMTP_PASS  = os.environ.get("SES_SMTP_PASS") or ""

# Timeouts (seconds)
SMTP_TIMEOUT = int(os.environ.get("SMTP_TIMEOUT") or "30")

def _as_list(x) -> list[str]:
    if not x:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i).strip() for i in x if i]
    return [s.strip() for s in str(x).split(",") if s.strip()]

def _build_message(*, subject:str, text:str|None, html:str|None, to:list[str], bcc:list[str], reply_to:str|None) -> tuple[EmailMessage, list[str]]:
    rcpts = [*(to or []), *(bcc or [])]
    if not rcpts:
        raise ValueError("No recipients provided (need 'to' and/or 'bcc').")

    msg = EmailMessage()
    msg["Subject"] = subject
    from_header = f"{FROM_NAME} <{FROM_EMAIL}>" if FROM_NAME else FROM_EMAIL
    msg["From"] = from_header
    # Always include a To header (even with BCC-only)
    msg["To"] = ", ".join(to) if to else "undisclosed-recipients:;"
    if reply_to:
        msg["Reply-To"] = reply_to

    # Text + optional HTML
    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")
    return msg, rcpts

def _send_smtp_starttls(host:str, port:int, user:str, password:str, msg:EmailMessage, rcpts:list[str]) -> None:
    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ctx)
        smtp.ehlo()
        smtp.login(user, password)
        refused = smtp.send_message(msg, to_addrs=rcpts)
        if refused:
            # Dict of refused recipients -> raise an informative error
            raise smtplib.SMTPRecipientsRefused(refused)

def _send_smtp_ssl(host:str, port:int, user:str, password:str, msg:EmailMessage, rcpts:list[str]) -> None:
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=SMTP_TIMEOUT) as smtp:
        smtp.login(user, password)
        refused = smtp.send_message(msg, to_addrs=rcpts)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)

def _send_gmail(msg:EmailMessage, rcpts:list[str]) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD are not set")

    # Try SMTPS 465, then STARTTLS 587
    last_err = None
    try:
        _send_smtp_ssl("smtp.gmail.com", 465, GMAIL_USER, GMAIL_APP_PASSWORD, msg, rcpts)
        return
    except Exception as e:
        last_err = e
    try:
        _send_smtp_starttls("smtp.gmail.com", 587, GMAIL_USER, GMAIL_APP_PASSWORD, msg, rcpts)
        return
    except Exception as e:
        raise last_err or e

def _send_ses(msg:EmailMessage, rcpts:list[str]) -> None:
    if not SES_SMTP_USER or not SES_SMTP_PASS:
        raise RuntimeError("SES_SMTP_USER / SES_SMTP_PASS are not set")
    # Prefer STARTTLS: SES is happiest on 587 in many PaaS networks
    last_err = None
    try:
        _send_smtp_starttls(SES_SMTP_HOST, SES_SMTP_PORT, SES_SMTP_USER, SES_SMTP_PASS, msg, rcpts)
        return
    except (socket.timeout, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
        last_err = e
    # Fallback: SSL on 465
    try:
        _send_smtp_ssl(SES_SMTP_HOST, 465, SES_SMTP_USER, SES_SMTP_PASS, msg, rcpts)
        return
    except Exception as e:
        raise last_err or e

def send_email(
    *,
    subject: str,
    text: str | None = None,
    html: str | None = None,
    to: list[str] | str | None = None,
    bcc: list[str] | str | None = None,
    reply_to: str | None = None,
) -> None:
    """Send an email using the configured provider."""
    to_list  = _as_list(to)
    bcc_list = _as_list(bcc)

    msg, rcpts = _build_message(
        subject=subject, text=text, html=html,
        to=to_list, bcc=bcc_list, reply_to=reply_to
    )

    if PROVIDER == "console":
        print("---- EMAIL (console) ----")
        print("From:", msg["From"])
        print("To:", msg["To"])
        print("Bcc:", ", ".join(bcc_list))
        print("Subject:", subject)
        print("Text:", (text or "")[:500])
        print("HTML present:", bool(html))
        print("-------------------------")
        return

    if PROVIDER == "gmail":
        _send_gmail(msg, rcpts)
        return

    if PROVIDER in {"ses", "ses_smtp"}:
        _send_ses(msg, rcpts)
        return

    raise RuntimeError(f"Unsupported EMAIL_PROVIDER={PROVIDER!r}. Use 'ses_smtp', 'gmail', or 'console'.")
