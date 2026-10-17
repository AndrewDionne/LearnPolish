"""Private SQLite storage and offline backup/recovery drills for the V2 family service.

Backups contain sensitive family records, password hashes, and session hashes.
This tool deliberately has no scheduler, upload, retention purge, or live overwrite.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import tempfile


def _private_directory(path: Path, *, create: bool = False) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Storage directory must be an absolute, non-symlink path")
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    details = path.lstat()
    if not stat.S_ISDIR(details.st_mode):
        raise ValueError("Storage directory is not a directory")
    if os.name == "posix" and (details.st_uid != os.getuid() or details.st_mode & 0o077):
        raise PermissionError("Storage directory must be owned by this user and private (0700)")


def _private_file(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Storage file must be an absolute, non-symlink path")
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode):
        raise ValueError("Storage file must be a regular file")
    if os.name == "posix" and (details.st_uid != os.getuid() or details.st_mode & 0o077):
        raise PermissionError("Storage file must be owned by this user and private (0600)")


def prepare_database(path: str) -> str:
    """Create the DB file with private permissions BEFORE SQLite opens it."""
    database = Path(path)
    if not database.is_absolute() or str(database) == ":memory:":
        raise ValueError("PTP_FAMILY_DB must be an absolute on-disk filename")
    _private_directory(database.parent, create=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(database, flags, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(descriptor)
    _private_file(database)
    return str(database)


def _integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise ValueError("SQLite quick_check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("SQLite foreign_key_check failed")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _readonly(database: Path) -> sqlite3.Connection:
    return sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=15)


def _temporary_path(directory: Path, prefix: str) -> Path:
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=prefix)
    os.close(descriptor)
    return Path(name)


def backup_database(source: str, directory: str) -> Path:
    """Produce a consistent SQLite online snapshot and a checksum manifest."""
    database, root = Path(source), Path(directory)
    _private_directory(database.parent)
    _private_file(database)
    _private_directory(root, create=True)
    if root == database.parent:
        raise ValueError("Backups must use a separate private directory")
    name = datetime.now(timezone.utc).strftime("family-%Y%m%dT%H%M%SZ-") + secrets.token_hex(6) + ".sqlite"
    backup = root / name
    manifest = root / (name + ".json")
    pending = _temporary_path(root, ".family-backup-")
    pending_manifest = None
    try:
        with _readonly(database) as original, sqlite3.connect(str(pending)) as snapshot:
            original.backup(snapshot)
            _integrity(snapshot)
        _private_file(pending)
        data = {"format": 1, "filename": name, "size": pending.stat().st_size,
                "sha256": _hash_file(pending),
                "created_at_utc": datetime.now(timezone.utc).isoformat()}
        with pending.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(pending, backup)  # exclusive: never replace an older backup
        pending_manifest = _temporary_path(root, ".family-manifest-")
        with pending_manifest.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending_manifest, manifest)
        verify_backup(str(backup))
        return backup
    except Exception:
        backup.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    finally:
        pending.unlink(missing_ok=True)
        if pending_manifest:
            pending_manifest.unlink(missing_ok=True)


def verify_backup(filename: str) -> dict:
    backup = Path(filename)
    _private_directory(backup.parent)
    _private_file(backup)
    manifest = backup.with_name(backup.name + ".json")
    _private_file(manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("format") != 1 or
            data.get("filename") != backup.name or
            type(data.get("size")) is not int or data["size"] != backup.stat().st_size or
            not isinstance(data.get("sha256"), str) or data["sha256"] != _hash_file(backup)):
        raise ValueError("Backup manifest mismatch: refusing an unverified snapshot")
    with _readonly(backup) as connection:
        _integrity(connection)
    return {"filename": backup.name, "size": data["size"],
            "sha256": data["sha256"], "created_at_utc": data["created_at_utc"]}


def restore_rehearsal(source: str, target: str) -> Path:
    """Restore a *verified* backup to a NEW offline file, never the live DB."""
    backup = Path(source)
    destination = Path(target)
    verify_backup(str(backup))
    if not destination.is_absolute() or destination == backup or destination.is_symlink():
        raise ValueError("Recovery target must be a different absolute non-symlink path")
    _private_directory(destination.parent, create=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination, flags, 0o600)  # fails if target already exists
    os.close(descriptor)
    try:
        with _readonly(backup) as original, sqlite3.connect(str(destination)) as restored:
            original.backup(restored)
            _integrity(restored)
        _private_file(destination)
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Private, offline V2 family SQLite recovery tools")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup", help="Take a consistent online snapshot")
    create.add_argument("--database", required=True)
    create.add_argument("--directory", required=True)
    verify = commands.add_parser("verify", help="Verify checksum and SQLite integrity")
    verify.add_argument("--backup", required=True)
    drill = commands.add_parser("restore-drill", help="Restore ONLY to a new offline database")
    drill.add_argument("--backup", required=True)
    drill.add_argument("--target", required=True)
    args = parser.parse_args()
    if args.command == "backup":
        backup = backup_database(args.database, args.directory)
        print(json.dumps({"backup": str(backup), **verify_backup(str(backup))}))
    elif args.command == "verify":
        print(json.dumps(verify_backup(args.backup)))
    else:
        restored = restore_rehearsal(args.backup, args.target)
        print(json.dumps({"restored_to": str(restored), "verified_backup": args.backup}))


if __name__ == "__main__":
    main()
