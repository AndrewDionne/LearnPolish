"""Hosted family pilot registration must stay closed without a verified adult allowlist.

These tests use private temporary SQLite + injected sender. They never send
real email or create any Neon/Render users.
"""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from family_api import create_app
from render_app import create_render_app

class AdultPilotAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.db=str(root / "family.sqlite")
        self.catalog=str(root / "lessons.json")
        Path(self.catalog).write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"practice","items":[{"id":"practice:0","polish":"Dzień dobry"}]}
        ]}),encoding="utf-8")
        self.sent=[]
        self.email="invited@example.test"
        self.password="a-long-private-test-passphrase"
        self.original={"email":self.email,"name":"Tester","password":self.password}
    def tearDown(self):
        self.temp.cleanup()
    def app(self,allowed):
        return create_app(
            database_path=self.db,catalog_path=self.catalog,
            allowed_origins=("http://localhost:4173",),
            pilot_adult_emails=allowed,
            verification_sender=lambda email,code:self.sent.append((email,code)))
    def user_count(self):
        with sqlite3.connect(self.db) as db:
            return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    def test_closed_mode_denies_account_creation_without_user_or_mail(self):
        client=self.app(()).test_client()
        health=client.get("/api/v2/family/health").json
        self.assertEqual(health["registration_mode"],"closed")
        self.assertFalse(health["registration_available"])
        response=client.post("/api/v2/family/signup",json={
            **self.original,"adult_confirmed":True})
        self.assertEqual((response.status_code,response.json["error"]),
                         (503,"registration_unavailable"))
        self.assertEqual(self.user_count(),0)
        self.assertFalse(self.sent)
    def test_allowlist_requires_true_boolean_and_whole_exact_email(self):
        client=self.app((self.email,)).test_client()
        self.assertEqual(client.get("/api/v2/family/health").json["registration_mode"],"adult_pilot")
        self.assertTrue(client.get("/api/v2/family/health").json["registration_available"])
        for detail in (
            self.original, {**self.original,"adult_confirmed":False},
            {**self.original,"adult_confirmed":"true"},
            {**self.original,"adult_confirmed":1},
            {**self.original,"adult_confirmed":True,"email":"outsider@example.test"},
            {**self.original,"adult_confirmed":True,"email":"invited+other@example.test"},
        ):
            reply=client.post("/api/v2/family/signup",json=detail)
            self.assertEqual(reply.status_code,403,reply.json)
        self.assertEqual(self.user_count(),0)
        self.assertFalse(self.sent)
        success=client.post("/api/v2/family/signup",json={
            **self.original,"adult_confirmed":True})
        self.assertEqual(success.status_code,201,success.json)
        self.assertEqual(self.sent[0][0],self.email)
        self.assertEqual(client.post("/api/v2/family/login",json=self.original).status_code,403)
        self.assertEqual(client.post("/api/v2/family/verification/confirm",json={
            "email":self.email,"code":self.sent[-1][1]}).status_code,200)
        signed_in=client.post("/api/v2/family/login",json=self.original)
        self.assertEqual(signed_in.status_code,200)
        bearer={"Authorization":"Bearer "+signed_in.json["token"]}
        self.assertEqual(client.post("/api/v2/family/groups",headers=bearer,
            json={"name":"Test adults"}).status_code,201)
    def test_free_render_fails_closed_if_online_accounts_use_ephemeral_sqlite(self):
        with patch.dict(os.environ,{"RENDER":"true","PTP_FAMILY_SIGNUP_MODE":"adult-pilot",
                                    "PTP_FAMILY_PILOT_EMAILS":self.email}):
            with self.assertRaisesRegex(RuntimeError,"durable restricted Neon"):
                create_render_app(dist_path=self._dist(),family_mode="enabled",
                    database_path=self.db,public_origin="https://example.com",require_email=False)
    def test_render_staging_rejects_unapproved_or_empty_admission(self):
        with patch.dict(os.environ,{"PTP_FAMILY_SIGNUP_MODE":"public",
                                    "PTP_FAMILY_PILOT_EMAILS":self.email}):
            with self.assertRaisesRegex(RuntimeError,"Public/minor"):
                create_render_app(dist_path=self._dist(),family_mode="enabled",
                    database_path=self.db,public_origin="https://example.com",require_email=False)
        with patch.dict(os.environ,{"PTP_FAMILY_SIGNUP_MODE":"adult-pilot",
                                    "PTP_FAMILY_PILOT_EMAILS":""}):
            with self.assertRaisesRegex(RuntimeError,"requires an email allowlist"):
                create_render_app(dist_path=self._dist(),family_mode="enabled",
                    database_path=self.db,public_origin="https://example.com",require_email=False)
        with patch.dict(os.environ,{"PTP_FAMILY_SIGNUP_MODE":"adult-pilot",
                                    "PTP_FAMILY_PILOT_EMAILS":"invited@example.test,invited@example.test"}):
            with self.assertRaisesRegex(RuntimeError,"Invalid adult pilot"):
                create_render_app(dist_path=self._dist(),family_mode="enabled",
                    database_path=self.db,public_origin="https://example.com",require_email=False)
    def test_allowlist_policy_rejects_wildcard_ambiguous_duplicates(self):
        for allowed in (("adult@example.test","adult@example.test"),("*@example.test",),
                        (" INVITED@example.test ",),tuple(f"a{x}@test.example" for x in range(13))):
            with self.assertRaisesRegex(RuntimeError,"Invalid restricted adult pilot"):
                self.app(allowed)
    def _dist(self):
        root=Path(self.temp.name)/"dist"
        (root/"generated").mkdir(parents=True,exist_ok=True)
        for name,content in (("index.html","<html></html>"),("sw.js","//sw"),
                             ("generated/lessons.json",Path(self.catalog).read_text())):
            (root/name).write_text(content,encoding="utf-8")
        return root

if __name__=="__main__":unittest.main()
