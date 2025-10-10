# app/emailer.py
"""
Unified email sender for Path to POLISH.

Supports providers:
- EMAIL_PROVIDER=ses_smtp   (AWS SES via SMTP; recommended for prod)
- EMAIL_PROVIDER=gmail      (Gmail SMTP with app password)
- EMAIL_PROVIDER=console    (prints to stdout; good for dev)

Render env (SES):
  EMAIL_PROVIDER=ses_smtp
  SES_SMTP_SERVER=email-smtp.eu-north-1.amazonaws.com
  SES_SMTP_USER=<<from SES SMTP credentials>>
  SES_SMTP_PASS=<<from SES SMTP credentials>>
  FROM_EMAIL=no-reply@polishpath.com
  FROM_NAME=Path to POLISH
"""

from __future__ import annotations
import os, ssl, smtplib
from email.message import EmailMessage

# ---- Provider + config ----
PROVIDER = (os.environ.get("EMAIL_PROVIDER") or "console").lower()

# Common "From"
FROM_EMAIL = os.environ.get("FROM_EMAIL") or os.environ.get("GMAIL_USER") or "no-reply@localhost"
FROM_NAME  = os.environ.get("FROM_NAME") or "Path to POLISH"

# Gmail (optional)
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")

# SES SMTP
SES_SMTP_SERVER = (
    os.environ.get("SES_SMTP_SERVER")
    or f"email-smtp.{os.environ.get('AWS_SES_REGION','eu-north-1')}.amazonaws.com"
)
SES_SMTP_USER = os.environ.get("SES_SMTP_USER")
SES_SMTP_PASS = os.environ.get("SES_SMTP_PASS")


def _as_list(x) -> list[str]:
    if not x:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i).strip() for i in x if i]
    return [s.strip() for s in str(x).split(",") if s.strip()]


def _build_message(*, subject: str, text: str | None, html: str | None,
                   to_list: list[str], bcc_list: list[str], reply_to: str | None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    # Always include a To header (even with BCC-only)
    msg["To"] = ", ".join(to_list) if to_list else "undisclosed-recipients:;"
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")
    # Do NOT set Return-Path; SES handles it via your MAIL FROM domain.
    return msg


def _send_via_smtp(server: str, username: str, password: str, msg: EmailMessage, rcpts: list[str]) -> None:
    """Try SMTPS (465) first, then STARTTLS (587)."""
    if not rcpts:
        raise ValueError("No recipients provided (need 'to' and/or 'bcc').")

    last_err = None
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(server, 465, context=context, timeout=20) as smtp:
            smtp.login(username, password)
            result = smtp.send_message(msg, to_addrs=rcpts)
            if result:  # dict of refused recipients
                raise smtplib.SMTPRecipientsRefused(result)
        return
    except Exception as e:
        last_err = e

    try:
        with smtplib.SMTP(server, 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            try:
                smtp.noop()
            except Exception:
                pass
            smtp.login(username, password)
            result = smtp.send_message(msg, to_addrs=rcpts)
            if result:
                raise smtplib.SMTPRecipientsRefused(result)
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
    to_list = _as_list(to)
    bcc_list = _as_list(bcc)
    rcpts = [*to_list, *bcc_list]

    if PROVIDER == "console":
        print("---- EMAIL (console) ----")
        print("From:", f"{FROM_NAME} <{FROM_EMAIL}>")
        print("To:", ", ".join(to_list) if to_list else "undisclosed-recipients:;")
        print("Bcc:", ", ".join(bcc_list))
        print("Subject:", subject)
        print("Text:", (text or "")[:500])
        print("HTML present:", bool(html))
        print("-------------------------")
        return

    msg = _build_message(
        subject=subject, text=text, html=html,
        to_list=to_list, bcc_list=bcc_list, reply_to=reply_to
    )

    if PROVIDER in ("ses", "ses_smtp"):
        if not (SES_SMTP_USER and SES_SMTP_PASS and SES_SMTP_SERVER):
            raise RuntimeError("SES SMTP env vars missing: SES_SMTP_SERVER, SES_SMTP_USER, SES_SMTP_PASS")
        _send_via_smtp(SES_SMTP_SERVER, SES_SMTP_USER, SES_SMTP_PASS, msg, rcpts)
        return

    if PROVIDER == "gmail":
        if not (GMAIL_USER and GMAIL_APP_PASSWORD):
            raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD are not set")
        # When using Gmail SMTP, ensure FROM_EMAIL matches GMAIL_USER or an allowed alias
        _send_via_smtp("smtp.gmail.com", GMAIL_USER, GMAIL_APP_PASSWORD, msg, rcpts)
        return

    raise RuntimeError(f"Unsupported EMAIL_PROVIDER={PROVIDER!r}. Use 'ses_smtp', 'gmail', or 'console'.")
