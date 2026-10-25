# FAM-R03 — Private tester accounts, no automated email provider

Owner goal: one family group, with FOUR separate identities: organizer Robert Dionne plus Dale Dionne, Laurel Dionne, and Jill Osborne. Robert IS the organizer and must not have an extra duplicate account. They each have their own real email address and choose/use their own credentials. Do not invent email addresses, commit personal emails or add an automated mail provider. This is a private test, not a public child-account launch or tutor product.

## Implemented, default closed

- Operator-only v2/server/manual_tester_setup.py creates all new pending accounts, independent cryptographically random PBKDF2-hashed passwords, 43-character one-use activation tokens (only SHA-256 stored), and one shared group + membership atomically in the isolated ptp_v2 database. An account stays unable to login until the code is confirmed; group XP and profiles remain per person.
- Each code expires 7 days from private provisioning. No plaintext credentials are printed into logs/source/CI. A new local owner-private 0600 receipt with each person's temporary password and code is written *before commit*. Duplicate emails and partial failures fail closed. This provisioning script uses only a privately configured restricted ptp_v2_runtime Neon connection; it never uses the privileged owner or the old public user schema.
- Hosted API setting PTP_FAMILY_TESTER_ACTIVATION=owner-delivered with PTP_FAMILY_SIGNUP_MODE=closed allows confirmation of pre-staged one-use tokens, but does NOT enable public signup or self-registration. No SMTP, Resend, email dispatch or password recovery is represented as active. The organizer personally sends each person's activation details to that person's own inbox or a trusted private channel.
- V2 Learning groups interface shows sign-in, accepts the personal temporary password, then requests the manually delivered activation code. Resend and Create Account remain unavailable, and testers see the 7-day expiration notice. Group membership is prearranged; no invitation code or duplicated accounts are necessary.
- Render Free must always use durable restricted Neon for online account data, never ephemeral local SQLite. All previously built families/XP/map features remain unchanged.

## Private setup data (not in GitHub)

To actually provision, the group organizer must supply the **exact four distinct email addresses** (their own and the other three named testers). No name-to-address guesses. Prepare a private, gitignored JSON manifest at v2/server/tester-private/people.json with keys: group_name (e.g. Polish Explorers), organizer_email, and members (array of objects with name and email; organizer included). The script dry-run command is:

    mkdir -p -m 700 v2/server/tester-private
    python3 v2/server/manual_tester_setup.py --manifest v2/server/tester-private/people.json

Dry run reports only count and validation; no DB writes. For actual setup, install psycopg[binary], put the verified restricted Neon ptp_v2_runtime TLS URL into a private PTP_FAMILY_DATABASE_URL environment variable (never commit or paste it in chat), then run:

    python3 v2/server/manual_tester_setup.py --manifest v2/server/tester-private/people.json --output v2/server/tester-private/tester-activation-credentials.json --apply

Only the private operator file contains the four independent temporary passwords and activation codes. It is ignored by git and permissioned 0600. Do not rerun over an existing group. Deliver only the corresponding person's credentials/code to their personal inbox; each person must change their temporary password after signing in.

## Hosted service setup and test acceptance

Existing Render Free V2 web service remains disabled unless configured separately. Before testing, give restricted Neon role LOGIN with a new strong secret, configure its URL **only in Render runtime Environment**. Set PTP_RENDER_FAMILY_MODE=enabled, PTP_FAMILY_SIGNUP_MODE=closed, PTP_FAMILY_TESTER_ACTIVATION=owner-delivered and exact PTP_PUBLIC_ORIGIN=https://path-to-polish-v2.onrender.com. Keep no SMTP/Resend keys, no PTP_FAMILY_DB and PTP_SPEECH_ENABLED=0. Rebuild V2 with the **non-secret Docker build arg** PTP_FAMILY_UI_MODE=same-origin so the frontend targets its own API. Reconcile Render actual auto-deploy/checksPass and /health/ready service settings; changing render.yaml alone does not update an existing service.

Smoke tests: /health/ready family_available true; /api/v2/family/health reports registration_mode closed and owner_delivered_activation_available true; stranger signup 503; unverified login 403; one-use code confirms once; expired/repeated/incorrect code rejected; each of four separate accounts sees the one group; shared opted-in XP and leaderboards update correctly and remain after Render restart; personal profile/password/session controls work. Hosted reality, private permission/guardian decisions (especially any minor), backup/privacy and live browser tests are independent of synthetic CI. There is NO CLAIM of real live account creation until actual email addresses are supplied and Neon/Render provisioning and smoke tests have run.

GitHub remains the authoritative continuity source; release issue #2 must stay open for live acceptance. No tutor or curriculum expansion.

## R03a: real participant roster correction and password setup (2026-10-25)

The owner explicitly identified **Robert Dionne as the organizer**, not a fifth participant. Correct pilot membership is **four individual people**: Robert (organizer), Jill Osborne, Laurel Dionne, and Dale Dionne. The actual addresses were provided privately in chat but must NOT be saved into GitHub or published documentation. **One entered school-domain spelling differs from the other**; confirm Dale's exact address with the owner before issuing an account. Do not silently rewrite it or send secrets to a guessed mailbox. When private addresses are confirmed, use one four-member private manifest and one group. The currently connected Neon production schema was checked and had **0 existing V2 user accounts, 0 groups, 0 memberships and 0 activation tokens**, while runtime role was still NOLOGIN; no live provision has taken place.

Invited members initially receive a unique temporary password; backend already supports authenticated password change and revokes their sessions. The account profile now also offers **Change password** so each user can set a personally chosen password, immediately clearing the old local session and family-sharing selection. This is a necessary account setup control, not a curriculum or tutor feature.
