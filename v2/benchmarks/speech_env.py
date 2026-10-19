#!/usr/bin/env python3
"""Owner-local durable Azure Speech credentials, never committed or printed.

Use PathToPolish-Private-AI/.env.azure-speech (chmod 600), under its
chmod-700 parent. This is a strict data file, NOT a shell script or an
arbitrary dotenv interpreter. It cannot execute code or expand variables.

The private file takes precedence over shell variables so stale ~/.zshrc
exports never override the owner's explicitly installed Speech resource.
If there is NO file, existing environment-only workflows still work.
No Azure/network calls occur here. Consent to upload remains per test.
"""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import stat
from typing import Mapping

FILENAME = ".env.azure-speech"
REGION = "germanywestcentral"
PRIVATE_FOLDER = "PathToPolish-Private-AI"
_KEYS = frozenset(("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"))
_MAX_FILE_BYTES = 1024


def _root(root: Path | None = None) -> Path:
    return root if root is not None else Path(__file__).resolve().parents[2]


def _credentials_valid(key: str | None, region: str | None) -> None:
    if not key or not key.isascii() or not key.isprintable() or key != key.strip() or (
        any(x in key for x in ("…", "\r", "\n")) or
        key in ("...", "[REDACTED]", "REDACTED", "<KEY>", "YOUR_AZURE_SPEECH_KEY") or
        len(key) > 512
    ):
        raise ValueError("Azure Speech key is missing or invalid; use the real regional resource key privately")
    if region != REGION:
        raise ValueError("Azure Speech region must be germanywestcentral for this resource")


def _private_paths(root: Path | None = None) -> tuple[Path, Path]:
    folder = _root(root) / PRIVATE_FOLDER
    return folder, folder / FILENAME


def _check_directory(folder: Path, *, create: bool = False) -> None:
    if not folder.exists() and not folder.is_symlink() and create:
        folder.mkdir(mode=0o700)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Private Speech configuration folder is missing or invalid")
    mode = folder.stat()
    if mode.st_uid != os.getuid() or stat.S_IMODE(mode.st_mode) & 0o077:
        raise ValueError("Private Speech configuration folder must be owned by you and chmod 700")


def _check_file(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("Private Speech configuration cannot be a symbolic link")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or (
        stat.S_IMODE(info.st_mode) & 0o077
    ) or info.st_size < 8 or info.st_size > _MAX_FILE_BYTES:
        raise ValueError("Private Speech configuration must be a regular owner-only chmod-600 file")


def read_private_config(root: Path | None = None) -> tuple[str, str] | None:
    folder, path = _private_paths(root)
    if not path.exists() and not path.is_symlink():
        return None
    _check_directory(folder)
    _check_file(path)
    try:
        # O_NOFOLLOW closes the final symlink race on supported macOS/Linux.
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            data = handle.read(_MAX_FILE_BYTES + 1)
    except (OSError, UnicodeError):
        raise ValueError("Could not read private Azure Speech configuration safely") from None
    if len(data.encode("utf-8")) > _MAX_FILE_BYTES or "\r" in data or "\x00" in data:
        raise ValueError("Private Speech configuration has invalid encoding or size")
    entries: dict[str, str] = {}
    for line in data.splitlines():
        if not line or "=" not in line:
            raise ValueError("Private Speech configuration contains unsupported lines")
        name, value = line.split("=", 1)
        if name not in _KEYS or name in entries:
            raise ValueError("Private Speech configuration allows only the two Speech fields")
        entries[name] = value
    if set(entries) != _KEYS:
        raise ValueError("Private Speech configuration requires both Speech key and region")
    _credentials_valid(entries["AZURE_SPEECH_KEY"], entries["AZURE_SPEECH_REGION"])
    return entries["AZURE_SPEECH_KEY"], entries["AZURE_SPEECH_REGION"]


def speech_credentials(
    *, root: Path | None = None, environ: Mapping[str, str] | None = None
) -> tuple[str | None, str | None]:
    """Prefer installed local file; otherwise preserve existing shell workflow.

    Does not initiate network requests and never alters os.environ.
    No lookup is needed for preview/offline summarization.
    """
    stored = read_private_config(root)
    if stored is not None:
        return stored
    env = os.environ if environ is None else environ
    return env.get("AZURE_SPEECH_KEY"), env.get("AZURE_SPEECH_REGION")


def save_private_config(
    key: str, region: str, *, root: Path | None = None, replace: bool = False
) -> None:
    """Owner-only setup. Never silently overwrite/print a secret."""
    _credentials_valid(key, region)
    folder, path = _private_paths(root)
    _check_directory(folder, create=True)
    if path.exists() or path.is_symlink():
        if not replace:
            raise ValueError("Private Speech configuration already exists; no overwrite performed")
        _check_file(path)
    elif replace:
        raise ValueError("No installed private Speech configuration to replace")
    data = f"AZURE_SPEECH_KEY={key}\nAZURE_SPEECH_REGION={region}\n".encode("utf-8")
    if len(data) > _MAX_FILE_BYTES:
        raise ValueError("Private Speech configuration exceeds length cap")
    if replace:
        # Build exclusively in the same 0700 directory. Replace atomically
        # after validation, leaving no world-readable intermediary.
        import tempfile
        fd, name = tempfile.mkstemp(prefix=".speech-write-", dir=folder)
        try:
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install/show status of local private Azure Speech config (zero Azure requests)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--save-current", action="store_true",
                       help="Install currently exported Speech key once (never displays it)")
    group.add_argument("--setup", action="store_true",
                       help="Ask securely for a new Speech key (hidden input)")
    group.add_argument("--status", action="store_true",
                       help="Check local config and permissions only (no credentials printed)")
    parser.add_argument("--replace", action="store_true",
                        help="Explicitly replace existing private file when rotating a key")
    args = parser.parse_args()
    if args.replace and args.status:
        parser.error("--replace requires --setup or --save-current")
    try:
        if args.status:
            file_values = read_private_config()
            if file_values:
                print("Azure Speech configuration: private file installed and valid (no network requests)")
            else:
                print("Azure Speech configuration: no private file; shell variables are fallback only")
            return 0
        if args.save_current:
            key = os.environ.get("AZURE_SPEECH_KEY", "")
            region = os.environ.get("AZURE_SPEECH_REGION", "")
        else:
            key = getpass.getpass("Paste Azure Speech F0 key (hidden): ")
            region = REGION
        save_private_config(key, region, replace=args.replace)
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        # Do not propagate raw filesystem errors/paths or input content.
        parser.error("Private configuration not saved. Check real key/region, folder chmod 700, and existing-file policy")
    print("Azure Speech private configuration saved (owner-only; no key printed, no network requests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
