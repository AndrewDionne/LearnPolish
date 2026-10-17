"""Private family recovery contract: single-use, expiration, revocation, enumeration safety."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from family_api import create_app


class FamilyRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        catalog = folder / "lessons.json"
        catalog.write_text(json.dumps({
            "schemaVersion": 1, "lessons": [
                {"id": "first", "items": [{"id": "first:0", "polish": "cześć"}]}
            ]}), encoding="utf-8")
        self.database = str(folder / "family.sqlite")
        self.catalog = str(catalog)
        self.sent = []
        self.app = create_app(self.database, self.catalog, ("http://localhost:5173",),
                              recovery_sender=lambda email, code: self.sent.append((email, code)))
        self.client = self.app.test_client()
        self.email = "parent@example.com"
        self.old_password = "original-private-passphrase-2026"
        self.new_password = "renewed-private-passphrase-2026"
        assert self.client.post("/api/v2/family/signup", json={
            "email": self.email, "name": "Parent", "password": self.old_password
        }).status_code == 201

    def tearDown(self):
        self.temp.cleanup()

    def request(self, email=None):
        return self.client.post("/api/v2/family/recovery/request",
                                json={"email": email or self.email})

    def complete(self, code, password=None):
        return self.client.post("/api/v2/family/recovery/complete", json={
            "code": code, "new_password": password or self.new_password
        })

    def login(self, password=None):
        return self.client.post("/api/v2/family/login",
                                json={"email": self.email, "password": password or self.old_password})

    def test_recovery_resets_credentials_invalidates_sessions_and_code(self):
        original = self.login()
        self.assertEqual(original.status_code, 200)
        auth = {"Authorization": "Bearer " + original.json["token"]}
        self.assertEqual(self.request().status_code, 202)
        self.assertEqual(len(self.sent), 1)
        code = self.sent[0][1]
        self.assertEqual(len(code), 43)
        with sqlite3.connect(self.database) as con:
            stored = con.execute("SELECT token_hash FROM password_reset_tokens").fetchone()[0]
            self.assertNotEqual(stored, code)
            self.assertEqual(len(stored), 64)
        self.assertEqual(self.complete(code).status_code, 200)
        self.assertEqual(self.client.get("/api/v2/family/me", headers=auth).status_code, 401)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(self.new_password).status_code, 200)
        self.assertEqual(self.complete(code).status_code, 400)

    def test_unknown_account_is_indistinguishable_and_has_no_mail(self):
        unknown = self.request("not-registered@example.com")
        known = self.request()
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.json, known.json)
        self.assertEqual([email for email, _ in self.sent], [self.email])
        self.assertNotIn(self.email, str(known.json))
        self.assertNotIn(self.sent[0][1], str(known.json))

    def test_reissue_invalidates_old_code_and_rate_limits_email(self):
        self.request()
        first = self.sent[-1][1]
        self.request()
        second = self.sent[-1][1]
        self.assertNotEqual(first, second)
        self.assertEqual(self.complete(first).status_code, 400)
        self.request()
        self.assertEqual(len(self.sent), 3)
        self.request()
        self.assertEqual(len(self.sent), 3)
        # Last code still works after throttled retry.
        self.assertEqual(self.complete(self.sent[-1][1]).status_code, 200)

    def test_token_expiration_and_invalid_input(self):
        with patch("family_api._now", return_value=100000):
            self.request()
        code = self.sent[-1][1]
        with patch("family_api._now", return_value=100901):
            self.assertEqual(self.complete(code).status_code, 400)
        for bad in ("", "short", "a" * 400, "<script>", 5, None):
            self.assertEqual(self.complete(bad).status_code, 400)
        self.assertEqual(self.complete(code, "short").status_code, 400)

    def test_change_password_and_deletion_revoke_pending_codes(self):
        self.request()
        code = self.sent[-1][1]
        login = self.login()
        auth = {"Authorization": "Bearer " + login.json["token"]}
        changed = self.client.post("/api/v2/family/account/password", headers=auth, json={
            "current_password": self.old_password, "new_password": self.new_password
        })
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.complete(code).status_code, 400)
        self.request()
        later_code = self.sent[-1][1]
        renewed = self.login(self.new_password)
        auth2 = {"Authorization": "Bearer " + renewed.json["token"]}
        deleted = self.client.post("/api/v2/family/account/delete", headers=auth2, json={
            "password": self.new_password, "confirmation": "DELETE MY ACCOUNT"
        })
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.complete(later_code).status_code, 400)
        with sqlite3.connect(self.database) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM password_reset_tokens").fetchone()[0], 0)

    def test_mail_delivery_failure_is_generic_and_token_removed(self):
        failing = create_app(self.database, self.catalog, ("http://localhost:5173",),
                             recovery_sender=lambda *_: (_ for _ in ()).throw(RuntimeError("SMTP failure")))
        response = failing.test_client().post("/api/v2/family/recovery/request",
                                              json={"email": self.email})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json, {"accepted": True})
        with sqlite3.connect(self.database) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM password_reset_tokens").fetchone()[0], 0)

    def test_without_delivery_recovery_fails_closed(self):
        plain = create_app(self.database, self.catalog, ("http://localhost:5173",))
        client = plain.test_client()
        self.assertFalse(client.get("/api/v2/family/health").json["password_recovery_available"])
        self.assertEqual(client.post("/api/v2/family/recovery/request",
                         json={"email": self.email}).status_code, 503)
        self.assertEqual(client.post("/api/v2/family/recovery/complete",
                         json={"code": "x"*43, "new_password": self.new_password}).status_code, 503)


if __name__ == "__main__":
    unittest.main()
