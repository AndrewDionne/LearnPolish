"""Private Path to Polish V2 verification/recovery mail, sent server-side only.

Render Free blocks outbound SMTP ports 25/465/587. Support an explicitly
configured HTTPS Resend API instead, without requiring a paid Render instance.
Never put credentials, recipients or codes in logs or browser bundles.
"""
from __future__ import annotations

from email.message import EmailMessage
import json
import os
import smtplib
import ssl
import urllib.request
from typing import Callable


def _message(purpose: str, code: str) -> tuple[str, str]:
    if purpose == "verification":
        return (
            "Verify your Path to Polish family email",
            "Confirm the email address for your Path to Polish family account.\n"
            "Enter this one-time verification code in the app within 30 minutes:\n\n"
            + code + "\n\nIf you did not register, ignore this email.\n"
            "Do not share the code.\n",
        )
    return (
        "Path to Polish family account recovery",
        "A request was made to reset your private Path to Polish family password.\n"
        "Enter this one-time recovery code in the app within 15 minutes:\n\n"
        + code + "\n\nIf you did not request a reset, ignore this email.\n"
        "Do not share the code. Your family learning activity is not changed.\n",
    )


def _validate_header(value: str) -> None:
    if not value.strip() or any(c in value for c in "\r\n\x00"):
        raise RuntimeError("Invalid email sender configuration")


def configured_sender(purpose: str = "recovery") -> Callable[[str, str], None] | None:
    if purpose not in ("recovery", "verification"):
        raise ValueError("Unsupported mail purpose")

    api_key = os.environ.get("PTP_FAMILY_RESEND_API_KEY", "")
    api_from = os.environ.get("PTP_FAMILY_RESEND_FROM", "")
    smtp_names = ("PTP_FAMILY_SMTP_HOST", "PTP_FAMILY_SMTP_USER",
                  "PTP_FAMILY_SMTP_PASSWORD", "PTP_FAMILY_SMTP_FROM")
    smtp_fields = [os.environ.get(key, "") for key in smtp_names]
    has_resend = bool(api_key or api_from)
    has_smtp = any(smtp_fields)
    if has_resend and has_smtp:
        raise RuntimeError("Configure exactly one private email delivery method")
    if has_resend:
        if not api_key or not api_from or not api_key.startswith("re_"):
            raise RuntimeError("Incomplete secure HTTPS mail configuration")
        _validate_header(api_from)
        def deliver_http(recipient: str, code: str) -> None:
            # Do not accept arbitrary API endpoints or redirects from user input.
            subject, body = _message(purpose, code)
            data = json.dumps({
                "from": api_from, "to": [recipient], "subject": subject, "text": body
            }).encode("utf-8")
            request = urllib.request.Request(
                "https://api.resend.com/emails", data=data, method="POST",
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "path-to-polish-v2/1",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status not in (200, 201, 202):
                    raise RuntimeError("Account email delivery failed")
                payload = json.loads(response.read(4096))
                if not isinstance(payload, dict) or not payload.get("id"):
                    raise RuntimeError("Account email delivery failed")
        return deliver_http
    if not has_smtp:
        return None
    if not all(smtp_fields):
        raise RuntimeError("Incomplete secure family mail configuration")
    host, username, password, sender = smtp_fields
    _validate_header(host)
    _validate_header(username)
    _validate_header(sender)
    raw_port = os.environ.get("PTP_FAMILY_SMTP_PORT", "465")
    try:
        port = int(raw_port)
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError as exc:
        raise RuntimeError("Invalid secure SMTP port") from exc

    def deliver_smtp(recipient: str, code: str) -> None:
        subject, body = _message(purpose, code)
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=10) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    return deliver_smtp
