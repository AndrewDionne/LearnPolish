# V3 family privacy and guardian release gate
_Last reviewed: 2026-11-09. Draft native PR #169. No hosted production change._

## Current safe release boundary

Path to Polish V3 **must not require sign-in** to learn or access offline original
reference audio, local review/XP, local Speak record/replay, sound lab, reading,
and tourist lessons. The device-local learner ID is not an external account.

Current optional family connectivity uses the pre-existing V2 verified session,
and the private family service is authoritative for membership and group XP.
V3 does not send login credentials to any other service, store a login/session
token on disk or upload old lesson activity during login. Every share requires a
fresh explicit Share action; only original item_id, mode, region are sent.
Azure/Groq voice assessment requires a separate per-take approval for **each**
provider; no mic/audio uploads on first launch or sign-in.

The V2 server currently has an **adult-only private pilot signup allowlist**,
but neither the login nor the me API returns authoritative verified
age/guardian role or participation grants. Its existing adult checkbox
is *self-attestation*, **not proof of adulthood or guardian authority**.
Therefore, native V3's temporary connected surface is **adult-only** and
requires a separate session-only acknowledgement of being age 18+ and using
one's own existing account before any family login request can start. No DOB
is collected. Without this acknowledgement there must be **zero family network
requests**, and no account-bound pronunciation endpoint is enabled.

This age acknowledgement is **not a child-safety solution** and cannot be used
to authorize a minor. Under-18 learners can study offline without sign-in,
personal account collection, family leaderboard or remote speech assessment
until the following additional approvals exist.

## Release blockers before connected features for minors

1. **Server-enforced guardian relationship:** a verified guardian independently
   authorizes a specific minor learner, with explicit group and family-role
   permissions. Child self-assertion or knowledge of a family password is never
   authority. Server must validate every family scoreboard/activity endpoint and
   voice assessment permission from the verified guardian policy; UI-only checks
   cannot substitute.
2. **Parental consent scope:** separate opt-ins for joining a family group,
   submitting activity statistics and sending a single microphone recording to
   two named speech providers, with clear retention, data-recipient and
   withdrawal language. No default consent from a family invitation.
3. **Privacy data minimization:** review children's personally identifying
   fields in group leaderboard results and restrict cross-family/member reads;
   no public directory. Voice content, transcript, raw acoustic response,
   bearer token and private guardian details must never enter local XP/export,
   analytics, crash logs or a CloudKit public database.
4. **Consent revocation and deletion:** verified guardian can disable family
   submission and connected speech independently; server rejects future
   requests immediately. Specify account deletion, voice retention and group
   history policy; preserve offline learning if a connected account is removed.
5. **Device and backend tests:** verify guardian allow/deny/revoke for every
   private endpoint, cross-family IDOR and role escalation, sign-out mid-request,
   offline/reconnect, password reset, historical activity rejection, and age
   handling. Secure production deployment requires owner approval and separate
   hosted/physical acceptance.

## Testable invariant matrix

| Surface | First launch, no login | Adult pilot after opt-in | Under 18, no guardian proof |
|---|---|---|---|
| Offline course, saved local XP, replay | Allowed | Allowed | Allowed |
| Private family sign-in | Not attempted | Allowed after own-account adult acknowledgement | Disabled |
| Family board/map | No request | Server-authenticated, read only | Disabled |
| Share activity | No request | Explicit per-event action; source fields only | Disabled |
| Azure/Groq speech upload | No request | Only verified session + dual per-take consent | Disabled |
| Historical local XP backfill | Never | Never | Never |
| CloudKit/private iCloud sync | Off | Off pending entitlement/merge acceptance | Off |

## Rollout and durable continuity

The V3 gate is **client-side interim defense**. It does not change the V2
server, existing provisioned tester identities or Neon/Render configuration.
Do not state that guardian permissions have been implemented or that an adult
checkbox verifies identity. Do not enable family or speech use for minors
without the server changes and documented acceptance above.

No Xcode physical installation until the user-approved full SwiftUI functional
scope has been integrated. Keep PR #169 draft and make GitHub the durable source.
