"""V2 family password-recovery delivery; no dev-token endpoint or mail logging.

Only authenticated SMTP over implicit TLS is allowed. Tests inject a mail sender
directly into create_app. Absent full SMTP configuration, recovery is unavailable.
"""
from __future__ import annotations

from email.message import EmailMessage
import os
import smtplib
import ssl
from typing import Callable


def configured_sender(purpose: str = "recovery") -> Callable[[str, str], None] | None:
    if purpose not in ("recovery", "verification"):
        raise ValueError("Unsupported mail purpose")
    names = ("PTP_FAMILY_SMTP_HOST", "PTP_FAMILY_SMTP_USER",
             "PTP_FAMILY_SMTP_PASSWORD", "PTP_FAMILY_SMTP_FROM")
    fields = [os.environ.get(key, "") for key in names]
    if not any(fields):
        return None
    if not all(fields):
        raise RuntimeError("Incomplete secure family mail configuration")
    host, username, password, sender = fields
    if any("\n" in value or "\r" in value for value in (host, username, sender)):
        raise RuntimeError("Invalid mail configuration")
    raw_port = os.environ.get("PTP_FAMILY_SMTP_PORT", "465")
    try:
        port = int(raw_port)
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError as exc:
        raise RuntimeError("Invalid secure SMTP port") from exc

    def deliver(recipient: str, code: str) -> None:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        if purpose == "verification":
            message["Subject"] = "Verify your Path to Polish family email"
            message.set_content(
                "Confirm the email address for your Path to Polish family account.\n"
                "Enter this one-time verification code in the app within 30 minutes:\n\n"
                + code + "\n\nIf you did not register, ignore this email.\n"
                "Do not share the code.\n"
            )
        else:
            message["Subject"] = "Path to Polish family account recovery"
            message.set_content(
                "A request was made to reset your private Path to Polish family password.\n"
                "Enter this one-time recovery code in the app within 15 minutes:\n\n"
                + code + "\n\nIf you did not request a reset, ignore this email.\n"
                "Do not share the code. Your family learning activity is not changed.\n"
            )
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=10) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    return deliver
