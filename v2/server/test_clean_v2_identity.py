"""Clean V2 login reuse: one migrated V1 verifier, no migrated learning history.

All tests use SQLite fixtures and inert mailbox names, never live Neon.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from werkzeug.security import generate_password_hash
from family_api import create_app, _password, LEGACY_SCRYPT_SALT
from manual_tester_setup import provision_test_group

class CleanIdentityResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=str(self.root/"v2.sqlite")
        self.catalog=self.root/"lessons.json"
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[{
            "id":"practice","items":[{"id":"practice:0","polish":"Cześć"}]}]}),encoding="utf-8")
        self.app=create_app(database_path=self.db,catalog_path=str(self.catalog),
                            allowed_origins=("http://localhost:4173",),
                            pilot_adult_emails=(),owner_delivered_test_codes=True)
        self.client=self.app.test_client()
        self.owner="legacy@example.test"
        self.password="original-legacy-login-passphrase"
        self.hash=generate_password_hash(self.password,method="scrypt")
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO users(email,name,salt,password_hash) VALUES(?,?,?,?)",
                       (self.owner,"Original Learner",LEGACY_SCRYPT_SALT,self.hash))
            db.commit()
    def tearDown(self):
        self.tmp.cleanup()
    def connection(self):
        db=sqlite3.connect(self.db,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db
    def login(self,password):
        return self.client.post("/api/v2/family/login",
                                json={"email":self.owner,"password":password})
    def verify_owner(self):
        with self.connection() as db:
            db.execute("INSERT INTO email_verifications(user_id,verified_at) VALUES(1,111)")
    def test_existing_password_only_works_after_verified_identity_and_rehashes_once(self):
        self.assertEqual(self.login(self.password).status_code,403)
        with self.connection() as db:
            self.assertEqual(db.execute("SELECT salt FROM users WHERE id=1").fetchone()["salt"],LEGACY_SCRYPT_SALT)
        self.verify_owner()
        self.assertEqual(self.login("invalid-original-password").status_code,401)
        with self.connection() as db:
            self.assertEqual(db.execute("SELECT salt FROM users WHERE id=1").fetchone()["salt"],LEGACY_SCRYPT_SALT)
        good=self.login(self.password)
        self.assertEqual(good.status_code,200,good.json)
        self.assertGreaterEqual(len(good.json["token"]),32)
        with self.connection() as db:
            row=db.execute("SELECT salt,password_hash FROM users WHERE id=1").fetchone()
            self.assertNotEqual(row["salt"],LEGACY_SCRYPT_SALT)
            self.assertEqual(len(row["salt"]),32)
            self.assertNotEqual(row["password_hash"],self.hash)
            self.assertEqual(row["password_hash"],_password(self.password,row["salt"]))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM activities").fetchone()[0],0)
        self.assertEqual(self.login(self.password).status_code,200)
    def test_valid_legacy_user_can_rotate_password_without_v1_access(self):
        self.verify_owner()
        good=self.login(self.password)
        self.assertEqual(good.status_code,200)
        res=self.client.post("/api/v2/family/account/password",
            headers={"Authorization":"Bearer "+good.json["token"]},
            json={"current_password":self.password,"new_password":"a-better-password-unique"})
        self.assertEqual(res.status_code,200,res.json)
        self.assertEqual(self.login(self.password).status_code,401)
        self.assertEqual(self.login("a-better-password-unique").status_code,200)
    def test_legacy_verifier_never_approves_non_scrypt_or_bad_salt(self):
        self.verify_owner()
        with self.connection() as db:
            db.execute("UPDATE users SET password_hash=? WHERE id=1",("pbkdf2:sha256:1$bogus$hash",))
        self.assertEqual(self.login(self.password).status_code,401)
    def test_provision_reuses_existing_verified_organizer_and_three_new_accounts(self):
        self.verify_owner()
        manifest={"group_name":"Fresh Learning Group","organizer_email":self.owner,"members":[
            {"email":self.owner,"name":"Original Learner"},
            {"email":"first@example.test","name":"First"},
            {"email":"second@example.test","name":"Second"},
            {"email":"third@example.test","name":"Third"}
        ]}
        with self.connection() as con:
            receipt=provision_test_group(con,manifest,reuse_existing_organizer=True)
        self.assertEqual(len(receipt["participants"]),4)
        organizer=next(x for x in receipt["participants"] if x["email"]==self.owner)
        self.assertTrue(organizer["existing_account"])
        self.assertNotIn("temporary_password",organizer)
        self.assertNotIn("activation_code",organizer)
        pending=[p for p in receipt["participants"] if not p["existing_account"]]
        self.assertEqual(len(pending),3)
        self.assertEqual(len({p["temporary_password"] for p in pending}),3)
        self.assertEqual(len({p["activation_code"] for p in pending}),3)
        with self.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0],4)
            self.assertEqual(con.execute("SELECT owner_id FROM families").fetchone()[0],1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM members").fetchone()[0],4)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM activities").fetchone()[0],0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM verification_tokens").fetchone()[0],3)
            self.assertEqual(con.execute("SELECT password_hash FROM users WHERE id=1").fetchone()[0],self.hash)
            with self.assertRaisesRegex(ValueError,"account already exists"):
                provision_test_group(con,manifest,reuse_existing_organizer=True)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM families").fetchone()[0],1)
    def test_missing_migrated_organizer_does_not_silently_create_a_new_identity(self):
        self.verify_owner()
        with self.connection() as con:
            con.execute("DELETE FROM email_verifications")
            con.execute("DELETE FROM users")
            manifest={"group_name":"New Team","organizer_email":self.owner,"members":[
                {"email":self.owner,"name":"Owner"},
                {"email":"teammate@example.test","name":"Teammate"}]}
            with self.assertRaisesRegex(ValueError,"not migrated"):
                provision_test_group(con,manifest,reuse_existing_organizer=True)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0],0)

if __name__=="__main__":unittest.main()
