# V2 Private Family Service — not deployed

This is isolated V2 infrastructure, deliberately separate from legacy /api/auth and /api/score.
Requires a private persistent SQLite database; do not deploy on ephemeral storage. It has not undergone production security approval.

## Local setup

First run the V2 content build in v2/frontend to generate public/generated/lessons.json. Configure:

- PTP_FAMILY_DB: absolute path to a private, persistent SQLite database
- PTP_FAMILY_CATALOG: absolute path to the generated built-in lesson catalog
- PTP_FAMILY_ORIGINS: comma-separated exact frontend HTTPS origins (localhost allowed for development)
- VITE_FAMILY_API_URL: frontend build-time URL of the family API; absent means no live family service

Install Flask 3.1.1, set the environment variables, and run python v2/server/family_api.py.
Run Python tests: python -m unittest discover -s v2/server -p 'test_*.py' -v.

## Shipped contract

Email/password accounts with PBKDF2 salts, throttled login, hashed 7-day bearer sessions, logout; private owner-managed family groups; single-use 48-hour invitations, a 12-member limit, membership checks; server XP calculated only for catalog item IDs and bounded modes/regions, with deduplication by learner/item/mode/UTC day. Client-provided XP, scores, dates, and difficulty are ignored. Region prices freeze on first contribution. Weekly member recognition covers effort, regularity and highest built-in difficulty; improvement remains pending valid evidence.

## Trust boundary

A client claims completion; the server does not yet verify that the learner performed a real session. Server recomputation and deduplication do not make rankings tamper-proof. Keep this family-only and friendly. The API never accepts or transmits microphone audio and makes no AI calls.

Production deployment requires private persistent disk, TLS termination, backup/recovery, integration security review, verified frontend origin, parent/minor privacy controls, load/concurrency checks and operational monitoring. Do not put credentials, invitation codes, database files or speech recordings in GitHub.


## Family privacy and account lifecycle

Authenticated APIs, without automatic sharing or deletion:
- POST /api/v2/family/groups/:id/invites/revoke: owner revokes all unused invitation codes. Used codes are never reactivated.
- POST /api/v2/family/groups/:id/transfer: owner nominates an existing member (new_owner_id).
- POST /api/v2/family/groups/:id/leave: member leaves, with shared activity removed and rankings updated; owner must transfer first if others remain, while a sole owner closes the family.
- GET /api/v2/family/account/export: authenticated personal profile, membership and activity data; never password/session hashes.
- POST /api/v2/family/account/password: verifies current password, rotates hash/salt, invalidates all sessions; reauthentication required.
- POST /api/v2/family/account/delete: requires exact confirmation phrase DELETE MY ACCOUNT and password. Deletes service sessions, activity, memberships, account and associated redeemed invitations. Ownership transfer required if others are in an owned group.

Privacy precedence: member departure/deletion erases their server-linked contributions and may reduce shared XP or undo a prior region unlock; personal offline data is unaffected. Erasure is intentionally more important than the normal permanent-unlock game mechanic.

This is not privacy certification or live deployment. Parent/guardian policies, verified email, password recovery, retention, secure hosted storage, and production review remain open.
