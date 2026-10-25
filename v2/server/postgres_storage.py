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


def _safe_connection_error_code(error: Exception) -> str:
    """Return only a fixed category; NEVER print raw libpq errors or URLs.

    libpq's exception text may include hostname, username, or the configured
    connection string, so map to a finite vocabulary instead of logging it.
    """
    message = str(error).lower()
    if "password authentication failed" in message or "invalid password" in message:
        return "authentication_rejected"
    if "no pg_hba.conf entry" in message or "permission denied" in message:
        return "connection_denied"
    if "database" in message and "does not exist" in message:
        return "database_not_found"
    if ("certificate" in message or "ssl" in message or
            "tls" in message or "hostname mismatch" in message):
        return "tls_verification_failed"
    if ("could not translate host name" in message or "name or service not known" in message or
            "nodename nor servname provided" in message):
        return "dns_resolution_failed"
    if ("connection refused" in message or "connection timed out" in message or
            "timeout expired" in message or "network is unreachable" in message):
        return "network_unavailable"
    if ("invalid connection" in message or "invalid dsn" in message or
            "missing \"=\"" in message or "keyword/value" in message):
        return "connection_url_invalid"
    if "search_path" in message and "invalid" in message:
        return "connection_options_rejected"
    if "schema" in message and ("permission denied" in message or "does not exist" in message):
        return "schema_unavailable"
    if "An explicit credentialled Postgres database URL" in str(error):
        return "connection_url_invalid"
    return "connection_unavailable"


def postgres_readiness_status(url: str) -> str:
    """Pure read-only probe. Return a public-safe code, never the exception."""
    try:
        con = open_postgres(url)
        try:
            row = con.execute(
                "SELECT to_regclass('ptp_v2.users') IS NOT NULL AS ok"
            ).fetchone()
            return "ready" if row and row["ok"] else "v2_table_missing"
        finally:
            con.close()
    except RuntimeError as error:
        if "V2 Neon schema missing" in str(error):
            return "schema_unavailable"
        return _safe_connection_error_code(error)
    except Exception as error:
        return _safe_connection_error_code(error)


def postgres_ready(url: str) -> bool:
    """Retain boolean API, without disclosing connection credentials."""
    return postgres_readiness_status(url) == "ready"
