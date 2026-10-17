"""Local-only CI family-service entrypoint. NEVER use in deployment.

Writes verification codes to a private runner-only file for Playwright tests.
This file is not part of the production family API and has no HTTP outbox route.
"""
import json
import os
from pathlib import Path
import stat

from family_api import create_app

if __name__ == "__main__":
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("CI family sender is permitted only in GitHub Actions")
    outbox = Path(os.environ["PTP_CI_VERIFICATION_OUTBOX"])
    if not outbox.is_absolute() or outbox.is_symlink():
        raise RuntimeError("CI outbox must be an absolute regular path")
    mode = outbox.parent.stat().st_mode
    if mode & 0o077 or not stat.S_ISDIR(mode):
        raise RuntimeError("CI outbox directory must be private")

    def write_code(email: str, code: str) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(outbox, flags, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"email": email, "code": code}) + "\n")

    create_app(verification_sender=write_code, recovery_sender=write_code).run(
        host="127.0.0.1",port=8016,debug=False)
