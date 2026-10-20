"""Neon Postgres adapter for V2 family API; deliberately keeps V1 public schema untouched.

Only the separately migrated "ptp_v2" schema is accessible via search_path.
A direct, TLS-verified database connection is intentional here because the
small family API uses explicit multi-statement transactions/advisory locks.
All user values remain bound parameters, never interpolated into SQL.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite-only developer/CI environments remain supported.
    psycopg = None
    dict_row = None


class _UninstalledPGError(Exception):
    pass


PgIntegrityError = psycopg.IntegrityError if psycopg is not None else _UninstalledPGError


class HybridRow(dict):
    """Keep sqlite3.Row's by-name AND by-index lookups for existing V2 API."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class PgCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return None if row is None else HybridRow(row)

    def fetchall(self):
        return [HybridRow(row) for row in self._cursor.fetchall()]

    @property
    def rowcount(self):
        return self._cursor.rowcount


def bound_sql(sql: str) -> str:
    """Translate only sqlite3's positional qmarks: all SQL is trusted source."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Invalid SQL")
    if "INSERT OR REPLACE" in sql.upper() or "PRAGMA" in sql.upper():
        raise ValueError("Unmigrated SQLite syntax in Postgres family API")
    return sql.replace("?", "%s")


class PgConnection:
    def __init__(self, connection):
        self._connection = connection
        self._transaction_open = False

    def execute(self, sql: str, params=()):
        if sql.strip().upper() == "BEGIN IMMEDIATE":
            if self._transaction_open:
                raise RuntimeError("Nested V2 transaction")
            self._connection.execute("BEGIN")
            # Serialize short account/signup/redeem/XP transactions to retain
            # SQLite BEGIN IMMEDIATE's effective atomic check-then-write logic.
            self._connection.execute("SELECT pg_advisory_xact_lock(742631159)")
            self._transaction_open = True
            return None
        return PgCursor(self._connection.execute(bound_sql(sql), params))

    def commit(self):
        if self._transaction_open:
            self._connection.execute("COMMIT")
            self._transaction_open = False

    def rollback(self):
        if self._transaction_open:
            self._connection.execute("ROLLBACK")
            self._transaction_open = False

    def close(self):
        self._connection.close()


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if (parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname or
            not parsed.username or not parsed.path.strip("/") or
            parsed.password is None or not parsed.password):
        raise RuntimeError("An explicit credentialled Postgres database URL is required")
    if parsed.hostname in ("localhost", "127.0.0.1"):
        raise RuntimeError("Hosted V2 Postgres must not use ephemeral loopback storage")
    return url


def open_postgres(url: str) -> PgConnection:
    _validate_url(url)
    if psycopg is None:
        raise RuntimeError("psycopg is required for V2 Neon account persistence")
    conn = psycopg.connect(
        url, autocommit=True, row_factory=dict_row,
        sslmode="verify-full", connect_timeout=8,
        options="-c search_path=ptp_v2",
    )
    # Fail closed if the configured connection escaped the V2-only schema.
    schema = conn.execute("SELECT current_schema() AS schema").fetchone()["schema"]
    if schema != "ptp_v2":
        conn.close()
        raise RuntimeError("V2 Neon schema missing: apply explicit migration first")
    return PgConnection(conn)


def postgres_ready(url: str) -> bool:
    """No side-effects. Successful connectivity plus required V2 schema."""
    try:
        con = open_postgres(url)
        try:
            exists = con.execute(
                "SELECT to_regclass('ptp_v2.users') IS NOT NULL AS ok"
            ).fetchone()["ok"]
            return bool(exists)
        finally:
            con.close()
    except Exception:
        # Deliberately never log database URLs, credentials or exception text.
        return False
