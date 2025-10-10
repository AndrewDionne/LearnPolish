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

Supports:
- EMAIL_PROVIDER=gmail  (requires GMAIL_USER and GMAIL_APP_PASSWORD)
- EMAIL_PROVIDER=console  (prints to stdout; useful for dev)

Gmail notes:
- Requires a Google "App Password" (16 chars, no spaces) with 2-step verification enabled.
- We send via SMTP over SSL (port 465).
"""

from __future__ import annotations
import os, ssl, smtplib
from email.message import EmailMessage

PROVIDER = (os.environ.get("EMAIL_PROVIDER") or "gmail").lower()

GMAIL_USER = os.environ.get("GMAIL_USER")
# remove spaces in case the app password was pasted with spaces
GMAIL_APP_PASSWORD = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")


def _as_list(x) -> list[str]:
    if not x:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i).strip() for i in x if i]
    # allow comma-separated string
    return [s.strip() for s in str(x).split(",") if s.strip()]


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
        print("From:", f"Path to POLISH <{GMAIL_USER or 'no-reply@localhost'}>")
        print("To:", ", ".join(to_list) if to_list else "undisclosed-recipients:;")
        print("Bcc:", ", ".join(bcc_list))
        print("Subject:", subject)
        print("Text:", (text or "")[:500])
        print("HTML present:", bool(html))
        print("-------------------------")
        print(f"[emailer] provider={PROVIDER} from={GMAIL_USER} rcpts={rcpts}")
        return

    if PROVIDER != "gmail":
        raise RuntimeError(f"Unsupported EMAIL_PROVIDER={PROVIDER!r}. Use 'gmail' or 'console'.")

    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD are not set")

    if not rcpts:
        raise ValueError("No recipients provided (need 'to' and/or 'bcc').")

    # Build message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Path to POLISH <{GMAIL_USER}>"
    # Always include a To header (even with BCC-only)
    msg["To"] = ", ".join(to_list) if to_list else "undisclosed-recipients:;"
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")

    # Try SMTPS 465, then STARTTLS 587
    last_err = None
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=20) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            result = smtp.send_message(msg, to_addrs=rcpts)
            if result:  # dict of refused recipients
                raise smtplib.SMTPRecipientsRefused(result)
        return
    except Exception as e:
        last_err = e

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            try:
                smtp.noop()  # harmless keepalive; helps on flaky nets
            except Exception:
                pass
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            result = smtp.send_message(msg, to_addrs=rcpts)
            if result:  # dict of refused recipients
                raise smtplib.SMTPRecipientsRefused(result)
        return
    except Exception as e:
        # If 587 also fails, raise the most informative error
        raise last_err or e

