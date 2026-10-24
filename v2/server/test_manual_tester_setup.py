"""Hermetic private-group setup tests: no real Neon, Render or email provider."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time
import unittest
from unittest.mock import patch

from family_api import create_app
from manual_tester_setup import (ONE_WEEK, _private_write, provision_test_group, read_manifest)
from render_app import create_render_app


class PrivateTestGroupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=str(self.root/"private.sqlite")
        self.catalog=self.root/"lessons.json"
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"practice","kind":"vocabulary","items":[{"id":"practice:0","polish":"Dzień dobry"}]}
        ]}),encoding="utf-8")
        self.people={"group_name":"Polish Explorers",
                     "organizer_email":"owner@example.test","members":[
          {"name":"Organizer","email":"owner@example.test"},
          {"name":"Tester One","email":"one@example.test"},
          {"name":"Tester Two","email":"two@example.test"}
        ]}
        self.app=create_app(database_path=self.db,catalog_path=str(self.catalog),
                            allowed_origins=("http://127.0.0.1:4173",),
                            pilot_adult_emails=(),owner_delivered_test_codes=True)
    def tearDown(self):
        self.tmp.cleanup()
    def provision(self,now=None):
        with sqlite3.connect(self.db,isolation_level=None) as db:
            db.row_factory=sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            return provision_test_group(db,self.people,now)
    def login(self,email,password):
        return self.app.test_client().post("/api/v2/family/login",
            json={"email":email,"password":password})
    def test_group_has_distinct_private_passwords_and_one_use_code_and_shared_group(self):
        receipt=self.provision()
        packs=receipt["participants"]
        self.assertEqual(len(packs),3)
        self.assertEqual(len({x["temporary_password"] for x in packs}),3)
        self.assertEqual(len({x["activation_code"] for x in packs}),3)
        self.assertTrue(all(len(p["activation_code"])==43 for p in packs))
        client=self.app.test_client()
        self.assertEqual(client.get("/api/v2/family/health").json["registration_mode"],"closed")
        self.assertTrue(client.get("/api/v2/family/health").json["owner_delivered_activation_available"])
        self.assertFalse(client.get("/api/v2/family/health").json["registration_available"])
        self.assertEqual(client.post("/api/v2/family/signup",json={
            "email":"intruder@example.test","name":"Intruder",
            "password":"long-password-unauthorized"}).status_code,503)
        for p in packs:
            self.assertEqual(self.login(p["email"],p["temporary_password"]).status_code,403)
            denied=client.post("/api/v2/family/verification/confirm",
                json={"email":p["email"],"code":"bad-code"})
            self.assertEqual(denied.status_code,400)
            response=client.post("/api/v2/family/verification/confirm",
                json={"email":p["email"],"code":p["activation_code"]})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(client.post("/api/v2/family/verification/confirm",
                json={"email":p["email"],"code":p["activation_code"]}).status_code,400)
            result=self.login(p["email"],p["temporary_password"])
            self.assertEqual(result.status_code,200)
            bearer={"Authorization":"Bearer "+result.json["token"]}
            me=client.get("/api/v2/family/me",headers=bearer)
            self.assertEqual(me.status_code,200)
            self.assertEqual(me.json["families"][0]["name"],"Polish Explorers")
            gid=me.json["families"][0]["id"]
            summary=client.get(f"/api/v2/family/groups/{gid}/summary",headers=bearer)
            self.assertEqual(summary.status_code,200)
            self.assertEqual(len(summary.json["members"]),3)
            self.assertEqual(summary.json["totals"]["weekly_xp"],0)
        with sqlite3.connect(self.db) as db:
            usernames=db.execute("SELECT email,salt,password_hash FROM users").fetchall()
            secrets_at_rest="\n".join(str(x) for x in usernames)
            self.assertNotIn(packs[0]["temporary_password"],secrets_at_rest)
            self.assertNotIn(packs[0]["activation_code"],secrets_at_rest)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM email_verifications").fetchone()[0],3)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM verification_tokens").fetchone()[0],0)
    def test_group_provisioning_is_atomic_if_email_already_exists(self):
        self.provision()
        with sqlite3.connect(self.db) as db:
            old=(db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                 db.execute("SELECT COUNT(*) FROM families").fetchone()[0])
        with self.assertRaisesRegex(ValueError,"already exists"):
            self.provision()
        with sqlite3.connect(self.db) as db:
            self.assertEqual((db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                 db.execute("SELECT COUNT(*) FROM families").fetchone()[0]),old)
    def test_private_receipt_exclusive_mode_0600_and_never_overwritten(self):
        p=self.root/"private-credentials.json"
        receipt={"password":"private","activation_code":"not-real"}
        _private_write(p,receipt)
        self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
        self.assertIn("private",p.read_text())
        with self.assertRaises(FileExistsError):
            _private_write(p,{"password":"leak"})
        self.assertNotIn("leak",p.read_text())
    def test_expired_codes_fail_without_email_resend_or_registration(self):
        initial=1000000
        receipt=self.provision(now=initial)
        person=receipt["participants"][0]
        with patch("family_api._now",return_value=initial+ONE_WEEK+1):
            x=self.app.test_client().post("/api/v2/family/verification/confirm",
                json={"email":person["email"],"code":person["activation_code"]})
        self.assertEqual(x.status_code,400)
        self.assertEqual(self.login(person["email"],person["temporary_password"]).status_code,403)
        self.assertEqual(self.app.test_client().post("/api/v2/family/verification/resend",json={
            "email":person["email"],"password":person["temporary_password"]}).status_code,503)
    def test_rejects_bad_or_duplicate_manifest_before_writing(self):
        cases=[
          {**self.people,"organizer_email":"unknown@example.test"},
          {**self.people,"members":[self.people["members"][0]]},
          {**self.people,"members":[self.people["members"][0]]*2},
          {**self.people,"members":[{"name":"Tester","email":"someone@bad\nmail.test"},
                                      *self.people["members"][1:]]},
          {**self.people,"members":[{"name":"Hacker\nInjected","email":"owner@example.test"},
                                      *self.people["members"][1:]]},
        ]
        for m in cases:
            with self.assertRaises(ValueError):
                read_manifest(m)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users").fetchone()[0],0)
    def test_owner_delivered_codes_are_not_open_signup_or_auto_email_bypass(self):
        for wrong in [
           {"pilot_adult_emails":None,"owner_delivered_test_codes":True},
           {"pilot_adult_emails":("adult@example.test",),"owner_delivered_test_codes":True},
           {"pilot_adult_emails":(),"owner_delivered_test_codes":True,
            "verification_sender":lambda *_:None},
        ]:
            with self.assertRaisesRegex(RuntimeError,"requires closed hosted signup"):
                create_app(database_path=self.db,catalog_path=str(self.catalog),
                           allowed_origins=("http://127.0.0.1:4173",),**wrong)
    def test_render_requires_explicit_owner_mode_with_closed_signups_and_durable_neon(self):
        dist=self.root/"dist"
        (dist/"generated").mkdir(parents=True,exist_ok=True)
        (dist/"index.html").write_text("<div id='root'></div>")
        (dist/"sw.js").write_text("sw")
        (dist/"generated"/"lessons.json").write_text(self.catalog.read_text())
        with patch.dict(os.environ,{"RENDER":"true","PTP_FAMILY_TESTER_ACTIVATION":"owner-delivered",
                                    "PTP_FAMILY_SIGNUP_MODE":"closed"}):
            with self.assertRaisesRegex(RuntimeError,"durable restricted Neon"):
                create_render_app(dist_path=dist,family_mode="enabled",database_path=self.db)
        with patch.dict(os.environ,{"PTP_FAMILY_TESTER_ACTIVATION":"owner-delivered",
                                    "PTP_FAMILY_SIGNUP_MODE":"adult-pilot"}):
            with self.assertRaisesRegex(RuntimeError,"requires closed registration"):
                create_render_app(dist_path=dist,family_mode="enabled",database_path=self.db)
        from flask import Flask
        import render_app
        recorded=[]
        def fake_backend(**kwargs):
            recorded.append(kwargs)
            return Flask("manual-backend-test")
        url="postgresql://ptp_v2_runtime:secret@neon.example.test/Path_to_Polish_DB"
        with patch.dict(os.environ,{"PTP_FAMILY_TESTER_ACTIVATION":"owner-delivered",
                                    "PTP_FAMILY_SIGNUP_MODE":"closed"}), \
             patch.object(render_app,"create_family_app",side_effect=fake_backend):
            app=create_render_app(dist_path=dist,family_mode="enabled",
                                  postgres_url=url,public_origin="https://path-to-polish-v2.onrender.com")
        self.assertIsNotNone(app)
        self.assertEqual(recorded[0]["pilot_adult_emails"],())
        self.assertTrue(recorded[0]["owner_delivered_test_codes"])
        self.assertEqual(recorded[0]["postgres_url"],url)


if __name__=="__main__":unittest.main()
