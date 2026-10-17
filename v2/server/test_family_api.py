"""Isolated family API authorization and server-calculated XP tests."""
import json
import pathlib
import tempfile
import unittest
from family_api import create_app

class FamilyApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=pathlib.Path(self.tmp.name)
        self.catalog=root/"lessons.json"
        self.catalog.write_text(json.dumps({"schemaVersion":1,"lessons":[
            {"id":"basic","kind":"vocabulary","items":[{"id":"basic:0","polish":"cześć"}]},
            {"id":"hard","kind":"reading","difficultyTier":3,
             "items":[{"id":"hard:0","polish":"Dzień dobry"}]}
        ]}),encoding="utf-8")
        self.verification_mail=[]
        self.app=create_app(str(root/"family.db"),str(self.catalog),("http://localhost:5173",),
                            verification_sender=lambda email,code:self.verification_mail.append((email,code)))
        self.client=self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def account(self,email,name):
        details={"email":email,"name":name,"password":"Private-family-passphrase-2026"}
        response=self.client.post("/api/v2/family/signup",json=details)
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(self.client.post("/api/v2/family/verification/confirm",json={
            "email":email,"code":self.verification_mail[-1][1]}).status_code,200)
        login=self.client.post("/api/v2/family/login",json=details)
        self.assertEqual(login.status_code,200,login.json)
        return {"Authorization":"Bearer "+login.json["token"]}

    def family(self):
        owner=self.account("parent@example.com","Parent")
        child=self.account("child@example.com","Learner")
        stranger=self.account("stranger@example.com","Stranger")
        made=self.client.post("/api/v2/family/groups",headers=owner,json={"name":"Family explorers"})
        self.assertEqual(made.status_code,201)
        return owner,child,stranger,made.json["id"]

    def test_private_membership_one_use_invites_and_owner_only_creation(self):
        owner,child,stranger,gid=self.family()
        summary=f"/api/v2/family/groups/{gid}/summary"
        self.assertEqual(self.client.get(summary,headers=stranger).status_code,404)
        self.assertEqual(self.client.post(f"/api/v2/family/groups/{gid}/invite",headers=child).status_code,404)
        code=self.client.post(f"/api/v2/family/groups/{gid}/invite",headers=owner).json["code"]
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",headers=child,json={"code":code}).status_code,200)
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",headers=stranger,json={"code":code}).status_code,400)
        self.assertFalse(self.client.get(summary,headers=child).json["group"]["can_invite"])
        self.assertTrue(self.client.get(summary,headers=owner).json["group"]["can_invite"])
        members=self.client.get(summary,headers=child).json["members"]
        self.assertEqual({person["name"] for person in members},{"Parent","Learner"})
        self.assertEqual(self.client.get(summary,headers=stranger).status_code,404)

    def test_server_authoritative_deduplicated_xp_and_rogue_destinations(self):
        owner,child,stranger,gid=self.family()
        code=self.client.post(f"/api/v2/family/groups/{gid}/invite",headers=owner).json["code"]
        self.client.post("/api/v2/family/invites/redeem",headers=child,json={"code":code})
        endpoint=f"/api/v2/family/groups/{gid}/activity"
        def send(headers,item,mode,region,**extras):
            return self.client.post(endpoint,headers=headers,json={
                "item_id":item,"mode":mode,"region":region,**extras})
        self.assertEqual(send(stranger,"basic:0","learn","pomorskie").status_code,404)
        self.assertEqual(send(owner,"fake:3","learn","pomorskie").status_code,400)
        self.assertEqual(send(owner,"basic:0","learn","fictional").status_code,400)
        self.assertEqual(send(owner,"basic:0",[],"pomorskie").status_code,400)
        self.assertEqual(send(owner,"basic:0","learn",[]).status_code,400)
        first=send(owner,"basic:0","learn","pomorskie",
                   xp=100000,tier=5,improvementXp=5000,created_at="2020-01-01")
        self.assertEqual(first.status_code,201)
        self.assertEqual(first.json["xp"],10)
        self.assertEqual(first.json["target"],300)
        self.assertFalse(send(owner,"basic:0","learn","małopolskie").json["accepted"])
        second=send(child,"hard:0","read","małopolskie")
        self.assertEqual(second.status_code,201)
        self.assertEqual(second.json["xp"],19)
        self.assertGreater(second.json["target"],300)
        summary=self.client.get(f"/api/v2/family/groups/{gid}/summary",headers=owner).json
        self.assertEqual(summary["totals"]["weekly_xp"],29)
        self.assertEqual({x["region"] for x in summary["regions"]},{"pomorskie","małopolskie"})
        self.assertEqual(summary["recognition"]["improvement"],"pending_validated_evidence")

    def test_salted_passwords_throttle_cors_and_logout(self):
        self.assertEqual(self.client.post("/api/v2/family/signup",json={
            "email":"a@example.com","name":"A","password":"short"}).status_code,400)
        owner=self.account("a@example.com","A")
        for _ in range(8):
            self.assertEqual(self.client.post("/api/v2/family/login",json={
                "email":"a@example.com","password":"wrong"}).status_code,401)
        self.assertEqual(self.client.post("/api/v2/family/login",json={
            "email":"a@example.com","password":"wrong"}).status_code,429)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=owner).status_code,200)
        self.assertEqual(self.client.post("/api/v2/family/logout",headers=owner).status_code,200)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=owner).status_code,401)
        self.assertEqual(self.client.get("/api/v2/family/health",
            headers={"Origin":"https://untrusted.example"}).status_code,403)
        allowed=self.client.get("/api/v2/family/health",headers={"Origin":"http://localhost:5173"})
        self.assertEqual(allowed.headers.get("Access-Control-Allow-Origin"),"http://localhost:5173")


    def test_revoke_invites_and_owner_transfer_then_leave(self):
        owner, child, stranger, gid = self.family()
        base = f"/api/v2/family/groups/{gid}"
        invite = self.client.post(base + "/invite", headers=owner).json["code"]
        self.assertEqual(self.client.post(base+"/invites/revoke",headers=child).status_code,404)
        self.assertEqual(self.client.post(base+"/invites/revoke",headers=stranger).status_code,404)
        self.assertEqual(self.client.post(base+"/invites/revoke",headers=owner).json["revoked"],1)
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",
                          headers=child,json={"code":invite}).status_code,400)
        valid = self.client.post(base+"/invite",headers=owner).json["code"]
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",
                          headers=child,json={"code":valid}).status_code,200)
        self.assertEqual(self.client.post(base+"/leave",headers=owner).status_code,409)
        self.assertEqual(self.client.post(base+"/transfer",headers=stranger,
                          json={"new_owner_id":2}).status_code,404)
        self.assertEqual(self.client.post(base+"/transfer",headers=child,
                          json={"new_owner_id":2}).status_code,403)
        self.assertEqual(self.client.post(base+"/transfer",headers=owner,
                          json={"new_owner_id":99999}).status_code,400)
        self.assertEqual(self.client.post(base+"/transfer",headers=owner,
                          json={"new_owner_id":"2"}).status_code,400)
        user_id=self.client.get("/api/v2/family/me",headers=child).json["user"]["id"]
        transferred=self.client.post(base+"/transfer",headers=owner,json={"new_owner_id":user_id})
        self.assertEqual(transferred.status_code,200)
        self.assertTrue(self.client.get(base+"/summary",headers=child).json["group"]["can_invite"])
        self.assertEqual(self.client.post(base+"/leave",headers=owner).status_code,200)
        self.assertEqual(self.client.get(base+"/summary",headers=owner).status_code,404)
        # Last owner can close the entire group; nothing readable remains.
        ended=self.client.post(base+"/leave",headers=child)
        self.assertEqual(ended.status_code,200)
        self.assertTrue(ended.json["family_deleted"])
        self.assertEqual(self.client.get(base+"/summary",headers=child).status_code,404)
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",
                          headers=stranger,json={"code":valid}).status_code,400)

    def test_leave_erases_member_activity_and_shared_region_credit(self):
        owner, child, stranger, gid = self.family()
        base=f"/api/v2/family/groups/{gid}"
        invitation=self.client.post(base+"/invite",headers=owner).json["code"]
        self.client.post("/api/v2/family/invites/redeem",headers=child,json={"code":invitation})
        endpoint=base+"/activity"
        self.assertEqual(self.client.post(endpoint,headers=child,json={
            "item_id":"basic:0","mode":"learn","region":"pomorskie"}).status_code,201)
        self.assertEqual(self.client.get(base+"/summary",headers=owner).json["regions"][0]["earned"],10)
        left=self.client.post(base+"/leave",headers=child)
        self.assertEqual(left.status_code,200)
        self.assertEqual(left.json["removed_activities"],1)
        fresh=self.client.get(base+"/summary",headers=owner).json
        self.assertEqual([member["name"] for member in fresh["members"]],["Parent"])
        self.assertEqual(fresh["regions"][0]["earned"],0)
        self.assertEqual(self.client.post(endpoint,headers=child,json={
            "item_id":"basic:0","mode":"read","region":"pomorskie"}).status_code,404)

    def test_account_export_password_change_deletion_and_forced_revocation(self):
        owner, child, stranger, gid = self.family()
        base=f"/api/v2/family/groups/{gid}"
        code=self.client.post(base+"/invite",headers=owner).json["code"]
        self.client.post("/api/v2/family/invites/redeem",headers=child,json={"code":code})
        self.client.post(base+"/activity",headers=child,json={
            "item_id":"hard:0","mode":"read","region":"małopolskie"})
        exported=self.client.get("/api/v2/family/account/export",headers=child)
        self.assertEqual(exported.status_code,200)
        self.assertEqual(exported.json["profile"]["name"],"Learner")
        self.assertEqual(exported.json["activities"][0]["xp"],19)
        self.assertNotIn("password_hash",exported.json)
        self.assertNotIn("token",exported.json)
        self.assertEqual(self.client.get("/api/v2/family/account/export",headers=stranger)
                         .json["activities"],[])
        changed=self.client.post("/api/v2/family/account/password",headers=child,json={
            "current_password":"Private-family-passphrase-2026",
            "new_password":"Updated-secure-passphrase-2026"})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=child).status_code,401)
        self.assertEqual(self.client.post("/api/v2/family/login",json={
            "email":"child@example.com","password":"Private-family-passphrase-2026"}).status_code,401)
        renewed=self.client.post("/api/v2/family/login",json={
            "email":"child@example.com","password":"Updated-secure-passphrase-2026"})
        child={"Authorization":"Bearer "+renewed.json["token"]}
        bad=self.client.post("/api/v2/family/account/delete",headers=child,json={
            "password":"wrong","confirmation":"DELETE MY ACCOUNT"})
        self.assertEqual(bad.status_code,401)
        bad=self.client.post("/api/v2/family/account/delete",headers=child,json={
            "password":"Updated-secure-passphrase-2026","confirmation":"please"})
        self.assertEqual(bad.status_code,400)
        removed=self.client.post("/api/v2/family/account/delete",headers=child,json={
            "password":"Updated-secure-passphrase-2026","confirmation":"DELETE MY ACCOUNT"})
        self.assertEqual(removed.status_code,200)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=child).status_code,401)
        group=self.client.get(base+"/summary",headers=owner).json
        self.assertEqual(len(group["members"]),1)
        self.assertEqual(group["regions"][0]["earned"],0)
        # Used invite MUST NOT reactivate when redeemed account is deleted.
        self.assertEqual(self.client.post("/api/v2/family/invites/redeem",headers=stranger,
                          json={"code":code}).status_code,400)
        blocked=self.client.post("/api/v2/family/account/delete",headers=owner,json={
            "password":"Private-family-passphrase-2026","confirmation":"DELETE MY ACCOUNT"})
        self.assertEqual(blocked.status_code,200)  # sole owner closes empty group
        self.assertEqual(self.client.get(base+"/summary",headers=stranger).status_code,404)

    def test_account_deletion_cannot_abandon_other_members(self):
        owner, child, _, gid=self.family()
        code=self.client.post(f"/api/v2/family/groups/{gid}/invite",headers=owner).json["code"]
        self.client.post("/api/v2/family/invites/redeem",headers=child,json={"code":code})
        failure=self.client.post("/api/v2/family/account/delete",headers=owner,json={
            "password":"Private-family-passphrase-2026","confirmation":"DELETE MY ACCOUNT"})
        self.assertEqual(failure.status_code,409)
        self.assertEqual(self.client.get("/api/v2/family/me",headers=owner).status_code,200)

    def test_fail_closed_config(self):
        with self.assertRaises(RuntimeError):
            create_app(None,None)
        with self.assertRaises(RuntimeError):
            create_app(str(pathlib.Path(self.tmp.name)/"x.db"),str(self.catalog),("*",))

if __name__=="__main__":
    unittest.main()
