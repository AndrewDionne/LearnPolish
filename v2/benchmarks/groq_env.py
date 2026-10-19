#!/usr/bin/env python3
"""Persist a Groq API key in an owner-only, Git-ignored local config asset.

Saved at PathToPolish-Private-AI/.env.groq (mode 0600; parent 0700).
The file is plain data, never evaluated or sourced as a shell script.
Installed key takes precedence over stale Terminal environment variables.
No network access, inference or voice upload in this module.
"""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import stat
import tempfile
from typing import Mapping

from speech_env import _root, _check_directory, _check_file, PRIVATE_FOLDER

FILENAME = ".env.groq"
MAX_BYTES = 1024


def _paths(root: Path | None = None) -> tuple[Path, Path]:
    folder = _root(root) / PRIVATE_FOLDER
    return folder, folder / FILENAME


def _valid_key(key: str | None) -> str:
    if (not isinstance(key, str) or not key or len(key) > 512
            or not key.isascii() or not key.isprintable()
            or key != key.strip() or "…" in key
            or key in ("...", "[REDACTED]", "REDACTED", "<KEY>", "YOUR_GROQ_API_KEY")
            or '"' in key or "'" in key):
        raise ValueError("Groq key missing, malformed or placeholder; restore the actual key privately")
    return key


def read_private_groq(root: Path | None = None) -> str | None:
    folder, path = _paths(root)
    if not path.exists() and not path.is_symlink():
        return None
    _check_directory(folder)
    _check_file(path)
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            data = stream.read(MAX_BYTES + 1)
    except (OSError, UnicodeError):
        raise ValueError("Cannot safely read private Groq configuration") from None
    if (len(data.encode("utf-8")) > MAX_BYTES or "\r" in data or "\x00" in data
            or len(data.splitlines()) != 1
            or not data.startswith("GROQ_API_KEY=")):
        raise ValueError("Private Groq config must contain exactly GROQ_API_KEY")
    return _valid_key(data.split("=", 1)[1].rstrip("\n"))


def groq_key(*, root: Path | None = None,
             environ: Mapping[str, str] | None = None) -> str | None:
    """Read private file first, shell environment only when none exists."""
    stored = read_private_groq(root)
    if stored is not None:
        return stored
    env = os.environ if environ is None else environ
    return env.get("GROQ_API_KEY")


def save_private_groq(key: str, *, root: Path | None = None,
                      replace: bool = False) -> None:
    _valid_key(key)
    folder, path = _paths(root)
    if replace and not folder.exists() and not folder.is_symlink():
        raise ValueError("No installed Groq config to rotate")
    _check_directory(folder, create=True)
    if path.exists() or path.is_symlink():
        if not replace:
            raise ValueError("Groq private config already exists; use --status, not a second installation")
        _check_file(path)
    elif replace:
        raise ValueError("No installed Groq config to rotate")
    data = f"GROQ_API_KEY={key}\n".encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("Groq private configuration exceeds size limit")
    if replace:
        fd, temp_name = tempfile.mkstemp(prefix=".groq-new-", dir=folder)
        try:
            with os.fdopen(fd, "wb") as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.lexists(temp_name):
                os.unlink(temp_name)
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise


def main() -> int:
    p = argparse.ArgumentParser(description="Private Groq credential setup; zero API requests")
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--save-current", action="store_true",
                       help="Save currently exported Groq key, without displaying it")
    modes.add_argument("--setup", action="store_true",
                       help="Prompt privately for Groq key, with hidden input")
    modes.add_argument("--status", action="store_true",
                       help="Check installed Groq credential file, without displaying it")
    p.add_argument("--replace", action="store_true",
                   help="Explicitly rotate an existing key; never overwrite by default")
    args = p.parse_args()
    if args.replace and args.status:
        p.error("--replace is only for --setup or --save-current")
    try:
        if args.status:
            stored = read_private_groq()
            print("Groq: private key installed (no network)" if stored is not None
                  else "Groq: no private key file; shell environment fallback only")
            return 0
        key = (os.environ.get("GROQ_API_KEY", "") if args.save_current
               else getpass.getpass("Paste Groq API key (hidden): "))
        save_private_groq(key, replace=args.replace)
    except (ValueError, OSError, EOFError, KeyboardInterrupt):
        p.error("Groq key not saved. Check private file ownership/permissions, key shape and existing-file policy; do not share the key")
    print("Groq: private key saved successfully (no network, no value printed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
