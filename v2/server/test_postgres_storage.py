"""No-network Neon adapter tests; never touch the owner's live V1 database."""
import unittest
from unittest.mock import patch

import postgres_storage as pg


class StubCursor:
    rowcount = 3

    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        result, self.rows = self.rows, []
        return result


class StubConnection:
    def __init__(self):
        self.statements = []
        self.closed = False

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        return StubCursor([{"id": 13, "name": "Cześć"}])

    def close(self):
        self.closed = True


class NeonAdapterTests(unittest.TestCase):
    def test_sql_only_converts_parameters_not_text(self):
        self.assertEqual(pg.bound_sql("SELECT id FROM users WHERE id=? AND email=?"),
                         "SELECT id FROM users WHERE id=%s AND email=%s")
        for sql in ("", "INSERT OR REPLACE INTO users VALUES(?)", "PRAGMA foreign_keys=ON"):
            with self.assertRaises(ValueError):
                pg.bound_sql(sql)

    def test_rows_support_sqlite_name_and_numeric_conventions(self):
        row = pg.HybridRow({"id": 13, "name": "Cześć"})
        self.assertEqual(row["id"], 13)
        self.assertEqual(row[0], 13)
        self.assertEqual(dict(row), {"id": 13, "name": "Cześć"})
        self.assertEqual(pg.PgCursor(StubCursor([{"id": 13}])).fetchone()["id"], 13)
        self.assertIsNone(pg.PgCursor(StubCursor()).fetchone())

    def test_begin_immediate_serializes_neon_transactions_and_commit(self):
        raw = StubConnection()
        con = pg.PgConnection(raw)
        con.execute("BEGIN IMMEDIATE")
        with self.assertRaises(RuntimeError):
            con.execute("BEGIN IMMEDIATE")
        result = con.execute("INSERT INTO users(email) VALUES(?) RETURNING id", ("a@example.com",))
        self.assertEqual(result.fetchone()["id"], 13)
        self.assertEqual(result.rowcount, 3)
        con.commit()
        self.assertEqual(raw.statements, [
            ("BEGIN", ()),
            ("SELECT pg_advisory_xact_lock(742631159)", ()),
            ("INSERT INTO users(email) VALUES(%s) RETURNING id", ("a@example.com",)),
            ("COMMIT", ()),
        ])
        con.execute("BEGIN IMMEDIATE")
        con.rollback()
        self.assertEqual(raw.statements[-1], ("ROLLBACK", ()))
        con.close()
        self.assertTrue(raw.closed)

    def test_pg_url_must_be_external_authenticated(self):
        for url in ("", "sqlite:///tmp/family.sqlite",
                    "postgresql://localhost/neondb",
                    "postgresql://u:p@localhost/neondb",
                    "https://neon.example.com",
                    "postgresql://u@neon.example.com/neondb"):
            with self.assertRaises(RuntimeError):
                pg._validate_url(url)
        self.assertEqual(
            pg._validate_url("postgresql://user:secret@db.eu-central-1.aws.neon.tech/family"),
            "postgresql://user:secret@db.eu-central-1.aws.neon.tech/family",
        )

    def test_platform_ca_bundles_preserve_verified_tls_on_mac_and_render(self):
        # Neon macOS workaround must NOT disable hostname or CA validation.
        for platform_name, root in (
            ("darwin", "/etc/ssl/cert.pem"),
            ("linux", "/etc/ssl/certs/ca-certificates.crt"),
        ):
            with self.subTest(platform_name=platform_name):
                with patch.object(pg, "host_platform", platform_name), \
                     patch.object(pg.Path, "is_file", autospec=True,
                                  side_effect=lambda p: str(p) == root):
                    self.assertEqual(pg._trusted_sslrootcert(), root)

        # Missing roots retain the existing strict libpq system trust path,
        # never fall back to sslmode=require or unverified connections.
        with patch.object(pg, "host_platform", "darwin"), \
             patch.object(pg.Path, "is_file", return_value=False):
            self.assertEqual(pg._trusted_sslrootcert(), "system")

    def test_open_postgres_keeps_verify_full_with_explicit_macos_ca(self):
        from unittest.mock import Mock

        raw = StubConnection()

        def probe_schema(sql):
            self.assertEqual(sql, "SELECT current_schema() AS schema")
            return StubCursor([{"schema": "ptp_v2"}])

        raw.execute = probe_schema
        client = Mock()
        client.connect.return_value = raw
        url = "postgresql://ptp_v2_runtime:secret@neon.example.com/family"
        with patch.object(pg, "psycopg", client), \
             patch.object(pg, "_trusted_sslrootcert",
                          return_value="/etc/ssl/cert.pem"):
            con = pg.open_postgres(url)
        args, kwargs = client.connect.call_args
        self.assertEqual(args, (url,))
        self.assertEqual(kwargs["sslmode"], "verify-full")
        self.assertEqual(kwargs["sslrootcert"], "/etc/ssl/cert.pem")
        self.assertEqual(kwargs["options"], "-c search_path=ptp_v2")
        con.close()
        self.assertTrue(raw.closed)

    def test_unavailable_neon_fails_closed_without_exposing_credentials(self):
        self.assertFalse(pg.postgres_ready("postgresql://bad:secret@neon.example.com/neondb"))
        with patch.object(pg, "open_postgres", side_effect=RuntimeError("private secret password")):
            self.assertFalse(pg.postgres_ready("postgresql://u:p@neon.example.com/neondb"))

    def test_public_safe_startup_diagnostic_never_exposes_libpq_secrets(self):
        cases = {
            "password authentication failed for user ptp_v2_runtime": "authentication_rejected",
            "certificate verify failed at db.example.com": "tls_cert_chain_untrusted",
            "root certificate file missing from /root/.postgresql/root.crt": "tls_ca_bundle_unavailable",
            "server certificate for db does not match host": "tls_hostname_mismatch",
            "could not translate host name private-host": "dns_resolution_failed",
            "connection refused at private-host": "network_unavailable",
            "database private_db does not exist": "database_not_found",
            "random unexpected text password=very-secret": "connection_unavailable",
            "An explicit credentialled Postgres database URL is required":
                "connection_url_invalid",
        }
        for error_text, expected_code in cases.items():
            with self.subTest(code=expected_code):
                with patch.object(pg, "open_postgres", side_effect=RuntimeError(error_text)):
                    status = pg.postgres_readiness_status("postgresql://u:very-secret@host/db")
                self.assertEqual(status, expected_code)
                self.assertNotIn("very-secret", status)
                self.assertNotIn("private-host", status)
                self.assertNotIn("ptp_v2_runtime", status)

    def test_safe_postgres_probe_preserves_boolean_contract(self):
        db = StubConnection()
        with patch.object(pg, "open_postgres", return_value=pg.PgConnection(db)):
            self.assertFalse(pg.postgres_ready("postgresql://u:secret@host/db"))
        with patch.object(pg, "open_postgres", side_effect=RuntimeError("password=secret")):
            self.assertEqual(pg.postgres_readiness_status("postgresql://u:secret@host/db"),
                             "connection_unavailable")



if __name__ == "__main__":
    unittest.main()
