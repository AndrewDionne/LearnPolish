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


## Family organizer controls are not guardian authority

The invite owner is a **group organizer**, not a verified parent or guardian. An emailed code verifies control of a mailbox, not age, legal guardianship, consent or responsibility for a child. Members currently register their own accounts. Do **not** deploy family accounts for minors, enable speech provider transfer for children, or describe the service as parent-authorized until a separate verified guardian enrollment and consent lifecycle is built and reviewed. This tranche only permits an organizer to stop unwanted group access and erase shared data.

## Family privacy and account lifecycle

Authenticated APIs, without automatic sharing or deletion:
- POST /api/v2/family/groups/:id/invites/revoke: owner revokes all unused invitation codes. Used codes are never reactivated.
- POST /api/v2/family/groups/:id/transfer: owner nominates an existing member (new_owner_id).
- POST /api/v2/family/groups/:id/leave: member leaves, with shared activity removed and rankings updated; owner must transfer first if others remain, while a sole owner closes the family.
- POST /api/v2/family/groups/:id/members/remove: owner-only removal of a **different** current member via `{member_id: integer}`. Deletes that member's activity and membership within this group atomically; once removed, the existing bearer session cannot read/submit further activity to this group. Other family memberships, personal account, and offline progress are untouched. Previously spent invitations stay spent; the owner cannot remove themself or another group's member. The client clears stale shared/map state upon a group-summary HTTP 404 on load or refresh.
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


## Private password recovery (SMTP delivery, not hosted)

The private family service now supports **email-code password recovery** when an
operator has configured actual secure SMTP delivery. It does not simulate or log
recovery tokens. Configure these environment variables **outside the repository**:

- `PTP_FAMILY_SMTP_HOST`: trusted provider SMTP hostname
- `PTP_FAMILY_SMTP_PORT`: implicit-TLS SMTP port (defaults to 465)
- `PTP_FAMILY_SMTP_USER`, `PTP_FAMILY_SMTP_PASSWORD`: dedicated mail account
- `PTP_FAMILY_SMTP_FROM`: verified sending address authorized by the provider

Only verified-certificate **SMTP over implicit TLS** is supported. Partial SMTP
configuration prevents API startup rather than silently claiming recovery works.
Without SMTP configured, the `/api/v2/family/health` capability reports
`password_recovery_available:false`; the browser hides **Forgot password?**
and recovery endpoints fail closed (503). No tokens are printed to logs or
written to web URLs, and the frontend requires manual code entry from email.

Flow: `POST /api/v2/family/recovery/request` accepts an email and returns the
same generic 202 response for known, unknown and throttled accounts when
delivery is configured. New 256-bit one-use codes expire in **15 minutes**,
invalidate the prior code, are stored only by SHA-256 hash and may be requested
at most three times per email/hour (plus a network-wide guard). The app emails
the code directly, not a clickable token-bearing URL. `POST
/api/v2/family/recovery/complete` accepts code plus a 12–256-character new
password; it rotates the salted PBKDF2 password hash, removes every existing
session and all outstanding codes. Normal authenticated password change and
account erasure also invalidate recovery codes. Mailer failures return the
same generic response and discard the undelivered code. Database and CI
security regression cases cover expiry, reuse, throttling, missing SMTP,
session invalidation, account deletion and delivery failures.

**Not email ownership verification:** current sign-up still accepts an
unverified address and does not require mailbox verification to join a group.
Before public rollout, enforce verified email at onboarding, design rate-limit
and bounce/abuse handling across IPs/providers, implement guardian/child account
authorization, choose a permitted email delivery service, and test actual mail
deliverability and spam handling. No real SMTP messages are sent in CI; tests
inject an isolated synthetic sender. This tranche does not make hosted family
accounts ready for users.


## Mandatory email verification before private family sign-in

Family registration is now **fail-closed without configured secure SMTP**.
The same private SMTP environment variables listed for password recovery
deliver a distinct **account verification** email; no fake local code is
exposed to users. New `POST /api/v2/family/signup` requests create pending
accounts and send a one-use 256-bit code (30-minute lifetime), **not a
bearer token or immediate login**. The browser asks for the emailed code
before signing in. The server stores only SHA-256 code fingerprints.

- `POST /api/v2/family/verification/confirm` with email + code confirms
  mailbox access once, clears pending codes and revokes any old sessions.
- `POST /api/v2/family/verification/resend` with email + account password
  issues a replacement code to an **unverified** mailbox and returns a generic
  202 for missing/incorrect accounts and throttled requests. A previously
  issued code then stops working.
- New registration and resends have per-destination (3 per hour) and per-network
  (20 per hour) quotas. Registration mail failure removes that pending account;
  SMTP is never silently skipped. Password recovery alone cannot activate an
  unverified account.
- Existing account databases are preserved with a new verification metadata
  table. Prior users **must verify once**; any old bearer tokens are rejected
  until then and revoked on successful verification. Operators must ensure
  working SMTP before migrating an active service. This V2 service is currently
  **undeployed**, so no real accounts are being migrated.

CI runs `v2/server/ci_family_server.py` only inside GitHub Actions and stores
synthetic email codes in a runner-private `0600` outbox file to complete a
two-account real-API Playwright journey. No debug verification endpoint exists
in the production API. This is not a mail provider integration test.

**Next security/privacy gates:** tested mailbox delivery and bounce handling,
anti-abuse controls beyond local SQLite/IP, verified parent/guardian authority
and child account creation/privacy, incident monitoring, TLS/persistent hosting,
encryption/retention of offsite backups and erasure reconciliation, physical
Safari/VoiceOver. Email verification alone is **not** guardian consent.


## Opt-in Azure Polish pronunciation feedback (development only)

The private family API can now serve one real `pl-PL` **scripted**
Pronunciation Assessment per explicit learner action. This is
**disabled by default**; the family service itself remains undeployed
and not security-certified for production accounts. Do not enable
publicly until hosted identity, TLS, safe durable storage, parental
privacy, backups, and production API quotas have passed review.

The frontend NEVER receives an Azure key or sends audio directly to
Azure. Only an authenticated and verified V2 family account may
`POST /api/v2/family/speech/assess` using multipart:
`item_id` (must be in the server's built-in canonical lesson
catalog), `audio` (mono PCM16 16kHz WAV, 0.6–10 seconds, max
360KB, local quality checked again on server), and
`approve_azure_audio_upload=yes`. The server constructs the
reference from the trusted catalog, not from browser-submitted Polish
text. Personal lessons intentionally unavailable until explicitly
approved server-side content exists. No client-supplied grade can
be credited.

A durable per-user free-tier guard permits at most **12 requests per
UTC day per account** and **30 total requests per UTC day** across the
service. Requests are counted BEFORE contacting Azure, so failed or
canceled provider calls still count. Only these request counts are
stored; no raw voice, provider transcript, phoneme, result or grading
history is written to DB. A short-lived owner-private temporary WAV
on the API server is deleted after each SDK call (including failure).
The user explicitly consents to transfer that take to Microsoft
Azure; its own processing policies apply.

Server activation is deliberately strict: set
`PTP_SPEECH_ENABLED=1`, `PTP_SPEECH_F0_CONFIRMED=1`,
`PTP_SPEECH_NO_PAID_BILLING=1`, with existing private
`AZURE_SPEECH_KEY` and
`AZURE_SPEECH_REGION=germanywestcentral`.
Install `azure-cognitiveservices-speech` in the server's isolated
Python environment (never commit or ship key in frontend).
Activation fails closed if any required flag/key/region is missing.
Server's existing origin restrictions, session authentication, email
verification and no-cache response headers apply. Add
`VITE_SPEECH_ASSESSMENT_ENABLED=true` to a **local opt-in Vite
build** only when the family API is actively configured; leave
disabled by default. `VITE_FAMILY_API_URL` must also be a
trusted HTTPS origin (localhost allowed for development).

The server returns `status=ok` with Azure's original
`AccuracyScore`, `FluencyScore`, and
`CompletenessScore` mapped to named 0..100 scalar metrics
and `calibration=uncalibrated`. Inconclusive results carry a
sanitized reason and **no grades**. No manual certainty bands,
phoneme-naming claims, XP improvement bonus, automatic uploads,
background provider requests or database retention of voices.
This is an integration slice, not human-calibrated Polish grading.
On any error, Speak's existing local replay/effort XP path works.

Server tests inject a fake assessor and run entirely offline. Browser
unit tests validate result shape and that the feature remains
disabled by default. **Do not confuse mocked CI tests with a real
end-to-end account/mobile/browser Azure assessment.**

