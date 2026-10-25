# FAM-R04 — Clean V2 learning history; retain established V1 login

**Owner choice, 2026-10-25:** Delete old V1 learning data and begin every learner at **zero V2 XP / zero study history**, while retaining existing account identities and working passwords. This decision expressly supersedes the earlier proposal to carry Robert's 27 scores / 23 set associations / 11 session histories forward. Retain account data, **not** old learning activity.

## Verified current layout

Live Neon `Path_to_Polish_DB` / `public.users` contains exactly one existing user, corresponding to Robert Dionne, with an established Werkzeug **scrypt** password verifier. Exact matching for Jill Osborne, Laurel Dionne and Dale Dionne finds no V1 users. V1 has **27 scores, 23 user-set rows, 11 saved session rows**, zero ratings and group rows; no V2 accounts or activities initially. Do not commit personal emails/password hashes into GitHub. V2 is deliberately isolated in `ptp_v2`; existing browser V1 JWT sessions do **not** confer V2 authorization.

## One-time recovery point

Neon branch `backup-v1-before-v2-identity-clean-reset-20261025` (`br-plain-silence-aga8uz8l`) was created from production main **without compute** before any deletion or import. It retains the original records for disaster recovery without adding a running paid service. Do not delete or publicly share this backup branch until the owner has accepted the new V2 setup. Backup is a rollback measure, not material exposed to learners.

## Certified code requirement BEFORE migration/reset

`family_api.py` accepts an explicitly marked V1 `scrypt` verifier copied *within Neon* into the V2-only user's `password_hash`, with sentinel `salt=legacy_werkzeug_scrypt_v1`. A correct original password grants a V2 session only after the V2 identity is marked verified and immediately rotates the verifier to V2's existing PBKDF2-SHA256 format with a fresh salt; incorrect/malformed legacy verifiers never grant access. No password is retrieved into chat, exposed to JS, or sent to Render. V2 group members and XP remain completely fresh.

`manual_tester_setup.py --reuse-existing-organizer` requires Robert's V2 identity **already present and verified**. It **never resets his password** or hands him a temporary activation code. Within one atomic transaction it creates separate new *pending* accounts for the three unmatched invitees, one new Robert-owned V2 group, four memberships, three separate hashed seven-day activation tokens (and private local one-time packs). Repeated executions are refused. Original four-new-account mode remains available only for unrelated projects; never use it for this group.

## Ordered live database action after 4/4 CI + merge

1. **Confirm** V1 account is the expected organizer by exact known email match, matches one and only one public.users row, has a recognized `scrypt` hash, V2 table has zero matching email and backup branch exists.
2. Inside the database (no verifier output): copy the one existing V1 user's `email`, `name` and `password_hash` into `ptp_v2.users`, with sentinel legacy salt, and insert one `ptp_v2.email_verifications` record for this pre-existing owner; V1 user stays untouched. This is safe to authenticate only after merged code handles the marker.
3. Verify V2 has one matching identity with sentinel format and **zero V2 `activities`/sessions**; no other V2 accounts.
4. **Delete only legacy learning data** from `public.scores`, `public.user_sets`, `public.session_state`, `public.ratings`, `public.group_memberships`, `public.groups` in one transaction; expect all zero. **Never delete `public.users`** or its preserved old password/identity; leave Alembic metadata/schema intact. No historical XP, ratings, saved responses, scores, progress, or group memberships imported into V2. The pre-reset Neon backup branch remains available.
5. Keep `ptp_v2_runtime` `NOLOGIN` until the owner privately completes restricted role/Render Free secret configuration. Do not try to route database passwords through chat/GitHub. The secure operator script later uses the confirmed four-person private roster; invoke its underlying provisioner with `--reuse-existing-organizer` after host passes health. Use Robert's **existing password** at first login, which then becomes a current V2 hash; new members activate using their distinct owner-delivered codes and replace initial passwords.
6. Test four separate logins, zero initial XP/sessions, privacy boundaries, opted-in family group scoring and data persistence. Old V1 pages could still be accessed with the preserved V1 identity but have no saved learning state.

**Boundary:** This is a clean learning-data reset, **not a user-account deletion**, not a credential reset, not permission to activate public/minor signups, not a curriculum/tutor feature. Keep umbrella issue #2 open until actual hosted activation and physical acceptance.
