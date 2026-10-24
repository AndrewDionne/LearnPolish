"""One-time private tester accounts. NO mail vendor, public sign-up or chat secrets.

Operator runs this locally with a private, restricted Neon runtime connection.
Each recipient gets their OWN unique temporary password plus a separate 7-day
activation code by organizer-delivered email/message. No plaintext credentials
are placed in GitHub, provider logs, user browser bundles or the database.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.parse import urlparse

from family_api import _hash, _password, EMAIL, MAX_MEMBERS
from postgres_storage import open_postgres

ONE_WEEK = 7 * 86400
DISPLAY = re.compile(r"^[^\r\n\x00-\x1f]{1,48}$")


def read_manifest(data: dict) -> tuple[str, str, list[dict]]:
    if not isinstance(data, dict) or set(data) != {"group_name", "organizer_email", "members"}:
        raise ValueError("Provide group_name, organizer_email and members only")
    name = data["group_name"]
    owner = data["organizer_email"]
    members = data["members"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 50 or not DISPLAY.fullmatch(name.strip()):
        raise ValueError("Invalid group name")
    if not isinstance(owner, str) or not isinstance(members, list) or not 2 <= len(members) <= MAX_MEMBERS:
        raise ValueError("One organizer and at least one tester (up to 12 members) are required")
    cleaned = []
    emails = set()
    for person in members:
        if not isinstance(person, dict) or set(person) != {"name", "email"}:
            raise ValueError("Each member needs name and email only")
        email = person["email"]
        display = person["name"]
        if (not isinstance(display, str) or not DISPLAY.fullmatch(display.strip()) or
                not isinstance(email, str) or not EMAIL.fullmatch(email.strip().lower()) or
                "*" in email or len(email) > 250):
            raise ValueError("Invalid member name or address")
        email = email.strip().lower()
        if email in emails:
            raise ValueError("Duplicate tester email")
        emails.add(email)
        cleaned.append({"name": display.strip(), "email": email})
    if owner.strip().lower() not in emails:
        raise ValueError("Organizer email must correspond to one member")
    return name.strip(), owner.strip().lower(), cleaned


def provision_test_group(connection, manifest: dict, now: int | None = None, before_commit=None) -> dict:
    """Atomically provision 1 group + unique pending accounts, no shared credentials.

    Caller commits and distributes the private returned receipt; never print it.
    Every account MUST complete one-use verification before login works.
    """
    group, owner, people = read_manifest(manifest)
    epoch = int(time.time()) if now is None else int(now)
    packs = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        for person in people:
            email = person["email"]
            if connection.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
                raise ValueError("An account already exists; no passwords or groups were replaced")
            pw = secrets.token_urlsafe(32)
            code = secrets.token_urlsafe(32)
            salt = secrets.token_hex(16)
            user_id = connection.execute(
                "INSERT INTO users(email,name,salt,password_hash) VALUES(?,?,?,?) RETURNING id",
                (email,person["name"],salt,_password(pw,salt)),
            ).fetchone()["id"]
            connection.execute(
                "INSERT INTO verification_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (_hash(code),user_id,epoch+ONE_WEEK),
            )
            packs.append({"name":person["name"],"email":email,
                          "temporary_password":pw,"activation_code":code,
                          "activation_expires_at":epoch+ONE_WEEK,
                          "user_id":user_id})
        organizer = next(person for person in packs if person["email"] == owner)
        group_id = connection.execute(
            "INSERT INTO families(name,owner_id) VALUES(?,?) RETURNING id",
            (group,organizer["user_id"]),
        ).fetchone()["id"]
        for person in packs:
            connection.execute("INSERT INTO members(family_id,user_id,joined_at) VALUES(?,?,?)",
                               (group_id,person["user_id"],epoch))
        # Write the private receipt BEFORE the Neon transaction commits, so a
        # crash cannot create accounts whose activation secrets were lost.
        # No plaintext password/code is ever committed to the database.
        details={"group_name":group,
                 "participants":[{k:v for k,v in pack.items() if k!="user_id"} for pack in packs],
                 "delivery":"Send each participant only THEIR OWN private details. Organizer delivers manually.",
                 "verification":"Recipient enters the activation code in the app after the temporary-password sign-in prompt. Change the temporary password after signing in."}
        if before_commit is not None:
            before_commit(details)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return details


def _private_write(path: Path, data: dict) -> None:
    """No stdout disclosure; refuse clobbering an existing secret receipt."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path,flags,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            json.dump(data,handle,ensure_ascii=False,indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description="Private one-time Path to Polish group tester setup")
    parser.add_argument("--manifest",required=True,help="Private local JSON with organizer and member addresses")
    parser.add_argument("--output",help="New private 0600 file of individual activation details")
    parser.add_argument("--apply",action="store_true",help="Actually create pending users in restricted Neon")
    args=parser.parse_args(argv)
    info=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    group,owner,people=read_manifest(info)
    if not args.apply:
        print(json.dumps({"status":"DRY_RUN_ONLY","participants":len(people),
                          "organizer_included":owner in [x["email"] for x in people],
                          "group_name":group,"accounts_created":0}))
        return
    if not args.output:
        parser.error("--output required with --apply")
    out=Path(args.output)
    if out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
        raise RuntimeError("Output must be a new private local file in an existing directory")
    url=os.environ.get("PTP_FAMILY_DATABASE_URL","")
    if urlparse(url).username != "ptp_v2_runtime":
        raise RuntimeError("Use only PTP_FAMILY_DATABASE_URL for least-privileged ptp_v2_runtime; never owner/V1")
    connection=open_postgres(url)
    try:
        try:
            provision_test_group(connection,info,before_commit=lambda details:_private_write(out,details))
        except BaseException:
            out.unlink(missing_ok=True)
            raise
    finally:
        connection.close()
    print(json.dumps({"status":"PENDING_MANUAL_ACTIVATION","accounts_created":len(people),
                      "group_created":True,"private_file":str(out)}))
    print("Deliver only each person's unique private login and activation code to their personal inbox.")
    print("No sender service required. Activation codes expire after 7 days.")


if __name__=="__main__":
    main()
