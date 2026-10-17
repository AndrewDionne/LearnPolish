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


## Private database and tested recovery preparation

Startup now requires the **immediate database directory** to be owned by the service user
with permissions `0700`, and its SQLite database to be a regular non-symlink
owner-private file (`0600`). A new database is pre-created securely before
SQLite touches it. An existing insecure file/directory **fails closed**; audit
ownership/location before fixing permissions. Use an **absolute** database path.
Do not point the family API at `/tmp` itself or an ephemeral app filesystem.

The standard-library operator tool requires a **separate private backup directory**:

```bash
python v2/server/private_storage.py backup --database /private/family/live/family.sqlite --directory /private/family/backups
python v2/server/private_storage.py verify --backup /private/family/backups/<backup-name>.sqlite
python v2/server/private_storage.py restore-drill --backup /private/family/backups/<backup-name>.sqlite --target /private/family/rehearsal/restore.sqlite
```

The live backup uses SQLite's online backup API (including committed WAL data),
checks SQLite integrity/foreign keys, writes a SHA-256 size/filename manifest, and
will not overwrite existing snapshots. Restore rehearsals accept only matching
verified snapshots and **never overwrite an existing target**. The tool does not
delete, schedule, copy to cloud, or deploy a database. Run the restore drill on an
**isolated offline path**, not a mounted live-service path. CI tests exercise
successful backup/recovery, concurrent WAL commits, tampering, permissions,
symlinks and no-overwrite behavior.

**Deployment remains blocked.** These backups include sensitive user/account
records, password hashes, and session hashes. The checksum detects corruption,
not malicious modifications; encrypt private off-host copies and manage backup
keys, access, rotation and retention before deployment. Restoring an earlier
snapshot can resurrect previously deleted accounts, revoked invitations, or
erased learning contributions. No production restore is authorized without
deletion/consent reconciliation and a verified privacy/retention plan. Also
pending: TLS hosting, persistent disk/restore monitoring, account email
verification and recovery, parent/guardian controls, operator incident review,
and real multi-device/physical iOS tests. No production family accounts yet.
