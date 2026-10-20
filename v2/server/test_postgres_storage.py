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

    def test_unavailable_neon_fails_closed_without_exposing_credentials(self):
        self.assertFalse(pg.postgres_ready("postgresql://bad:secret@neon.example.com/neondb"))
        with patch.object(pg, "open_postgres", side_effect=RuntimeError("private secret password")):
            self.assertFalse(pg.postgres_ready("postgresql://u:p@neon.example.com/neondb"))


if __name__ == "__main__":
    unittest.main()
