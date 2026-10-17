"""Verification required before creating private family sessions or redeeming invitations."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from family_api import create_app


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.db=str(root/"family.sqlite")
        self.catalog=str(root/"lessons.json")
        Path(self.catalog).write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"base","items":[{"id":"base:0","polish":"dzień"}]}
        ]}), encoding="utf-8")
        self.messages=[]
        self.address="member@example.test"
        self.secret="secure-private-family-passphrase"
        self.app=create_app(self.db,self.catalog,("http://localhost:5173",),
                            verification_sender=lambda email,code:self.messages.append((email,code)))
        self.client=self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def signup(self):
        return self.client.post("/api/v2/family/signup",json={
            "email":self.address,"name":"Member","password":self.secret})

    def verify(self,code=None,email=None):
        return self.client.post("/api/v2/family/verification/confirm",json={
            "email":email or self.address,"code":code or self.messages[-1][1]})

    def login(self):
        return self.client.post("/api/v2/family/login",json={
            "email":self.address,"password":self.secret})

    def test_signup_requires_mail_control_before_account_access(self):
        self.assertEqual(self.signup().status_code,201)
        self.assertEqual(self.login().status_code,403)
        self.assertEqual(self.login().json["error"],"email_verification_required")
        self.assertEqual(self.verify().status_code,200)
        self.assertEqual(self.verify().status_code,400)
        response=self.login()
        self.assertEqual(response.status_code,200)
        bearer={"Authorization":"Bearer "+response.json["token"]}
        self.assertEqual(self.client.post("/api/v2/family/groups",headers=bearer,
                         json={"name":"Poland explorers"}).status_code,201)
        with sqlite3.connect(self.db) as connection:
            verified=connection.execute("SELECT COUNT(*) FROM email_verifications").fetchone()[0]
            pending=connection.execute("SELECT COUNT(*) FROM verification_tokens").fetchone()[0]
        self.assertEqual((verified,pending),(1,0))

    def test_hash_scope_and_expiration(self):
        with patch("family_api._now",return_value=100000):
            self.signup()
        code=self.messages[-1][1]
        self.assertEqual(len(code),43)
        with sqlite3.connect(self.db) as con:
            stored=con.execute("SELECT token_hash FROM verification_tokens").fetchone()[0]
        self.assertNotEqual(code,stored)
        self.assertEqual(len(stored),64)
        self.assertEqual(self.verify(code,email="outsider@example.test").status_code,400)
        with patch("family_api._now",return_value=101801):
            self.assertEqual(self.verify(code).status_code,400)

    def test_resend_requires_password_does_not_expose_existing_accounts(self):
        self.signup()
        previous=self.messages[-1][1]
        wrong=self.client.post("/api/v2/family/verification/resend",json={
            "email":self.address,"password":"wrong-password"})
        absent=self.client.post("/api/v2/family/verification/resend",json={
            "email":"unknown@example.test","password":self.secret})
        self.assertEqual((wrong.status_code,absent.status_code),(202,202))
        self.assertEqual(wrong.json,absent.json)
        self.assertEqual(len(self.messages),1)
        correct=self.client.post("/api/v2/family/verification/resend",json={
            "email":self.address,"password":self.secret})
        self.assertEqual(correct.status_code,202)
        self.assertEqual(len(self.messages),2)
        self.assertEqual(self.verify(previous).status_code,400)
        self.assertEqual(self.verify().status_code,200)
        self.client.post("/api/v2/family/verification/resend",json={
            "email":self.address,"password":self.secret})
        self.assertEqual(len(self.messages),2)

    def test_verification_request_is_throttled(self):
        self.signup()
        for _ in range(4):
            self.assertEqual(self.client.post("/api/v2/family/verification/resend",json={
                "email":self.address,"password":self.secret}).status_code,202)
        self.assertEqual(len(self.messages),4)  # initial signup + max 3 resends
        self.assertEqual(self.verify().status_code,200)

    def test_fail_closed_and_failed_delivery_leaves_no_ghost_account(self):
        no_mail=create_app(self.db,self.catalog,("http://localhost:5173",))
        self.assertFalse(no_mail.test_client().get("/api/v2/family/health").json["email_verification_available"])
        self.assertEqual(no_mail.test_client().post("/api/v2/family/signup",json={
            "email":self.address,"name":"Member","password":self.secret}).status_code,503)
        broken=create_app(self.db,self.catalog,("http://localhost:5173",),
            verification_sender=lambda *_: (_ for _ in ()).throw(RuntimeError("offline mail")))
        result=broken.test_client().post("/api/v2/family/signup",json={
            "email":self.address,"name":"Member","password":self.secret})
        self.assertEqual(result.status_code,503)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0],0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM verification_tokens").fetchone()[0],0)

    def test_legacy_accounts_require_verification_including_old_active_sessions(self):
        self.signup()
        self.verify()
        session=self.login().json["token"]
        bearer={"Authorization":"Bearer "+session}
        self.assertEqual(self.client.get("/api/v2/family/me",headers=bearer).status_code,200)
        with sqlite3.connect(self.db) as con:
            con.execute("DELETE FROM email_verifications")
        self.assertEqual(self.client.get("/api/v2/family/me",headers=bearer).status_code,401)
        self.assertEqual(self.login().status_code,403)
        self.assertEqual(self.client.post("/api/v2/family/verification/resend",json={
            "email":self.address,"password":self.secret}).status_code,202)
        self.assertEqual(self.verify().status_code,200)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=bearer).status_code,200)

    def test_reset_does_not_bypass_unverified_email_gate(self):
        self.signup()
        mail=[]
        reset_server=create_app(self.db,self.catalog,("http://localhost:5173",),
                                recovery_sender=lambda email,code:mail.append((email,code)),
                                verification_sender=lambda email,code:self.messages.append((email,code)))
        client=reset_server.test_client()
        self.assertEqual(client.post("/api/v2/family/recovery/request",
            json={"email":self.address}).status_code,202)
        self.assertEqual(client.post("/api/v2/family/recovery/complete",json={
            "code":mail[-1][1],"new_password":"reset-private-family-password"}).status_code,200)
        self.assertEqual(client.post("/api/v2/family/login",json={
            "email":self.address,"password":"reset-private-family-password"}).status_code,403)
        self.assertEqual(self.verify().status_code,200)
        self.assertEqual(client.post("/api/v2/family/login",json={
            "email":self.address,"password":"reset-private-family-password"}).status_code,200)


if __name__=="__main__":
    unittest.main()
