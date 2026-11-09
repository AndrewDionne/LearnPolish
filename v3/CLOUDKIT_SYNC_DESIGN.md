# V3 optional private iCloud sync — architecture and acceptance gate
Reviewed 2026-11-09. Not enabled in draft PR #169.

## First-run rule

**No sign-in, iCloud prompt, cloud connection or network contact to learn.**
The entire bundled course, recorded reference audio, local Speak/replay, XP,
review and optional local JSON export must work offline without Apple ID or
family login. iCloud would be a separate *user-initiated* feature from Progress.

Current V3 Export creates a user-controlled, versioned JSON copy of on-device
progress without provider audio, family credentials or sessions. Local erase
must be separately confirmed, replace the learner atomically and never touch
server-held family contributions or a prior export. Neither action uses iCloud.

## Apple platform contract

- Use the user's CloudKit *private database*, never a public roster; account
  access is required. See:
  https://developer.apple.com/documentation/cloudkit/ckcontainer/privateclouddatabase
- Test CKContainer.accountStatus before opt-in access and after account changes:
  https://developer.apple.com/documentation/cloudkit/ckcontainer/accountstatus(completionhandler:)
- CKSyncEngine handles private-record change transport; it needs CloudKit and
  remote-notification entitlements plus durable state. Automatic scheduling
  may be delayed; app-specific conflicts are still our responsibility:
  https://developer.apple.com/documentation/cloudkit/cksyncengine-5sie5
- Handle CKError.serverRecordChanged using client, server, and ancestor copies:
  https://developer.apple.com/documentation/cloudkit/ckerror/serverrecordchanged

Do not initialize sync or add iCloud entitlements to the current unsigned CI
build. Apple developer provisioning and real two-device tests are separate
requirements before enabling it.

## Why syncing the existing local-learner.json file is unsafe

Current LocalLearner contains aggregate PracticeRecord counters and due dates,
not an immutable event for every card attempt. It also keeps personal XP
events keyed by mode + item + device-local calendar day; different time zones
could double-count the same practice. Last writer wins would overwrite valid
review work on a second device; summing counters double-counts attempts;
taking the maximum loses legitimate history. Local navigator position,
tourist cursor and selected region are device preferences, not shared truth.
A local reset must also remain distinct from cloud deletion.

**No whole-file overwrite or silent aggregate merge is authorized.**

## Proposed versioned sync event format

1. Add a bounded append-only PracticeEvent with immutable random UUID,
   original lesson:item ID, practice mode, UTC instant, per-device actor ID,
   and outcome. Never put raw microphone audio, provider transcripts,
   external assessment results, family roster, group receipt or account token
   into a CloudKit record.
2. Keep legacy LocalLearner records fully compatible. Migrate historical
   aggregates without inventing historical attempts. Future events are
   idempotent by UUID. Derive review level and next due date using a
   deterministic, source-validated reducer in chronological UTC order,
   tie-broken by UUID. Certify a single cross-device XP day policy.
3. Keep local navigation position and device preferences local, not
   authoritative cloud history. Family XP remains server-computed separately.
4. Use an explicitly opted-in, private-database record zone. Handle
   serverRecordChanged, account-switch, conflict and change-token recovery
   without wiping a local or remote candidate.
5. Offline learners must not receive a CloudKit account prompt. Optional
   iCloud link needs an explicit decision to keep local or link/merge, and
   must never implicitly occur after a private family login.
6. Local-only erase, opt-out and remote iCloud deletion require separate
   actions and clear disclosures. Remote deletion must be tombstone-safe
   so a stale second phone cannot restore data that was intentionally erased.

## Acceptance tests required before enabling

- No iCloud account and airplane mode: first-run course and local export,
  reset and review work with zero CloudKit requests.
- Two devices: concurrent unique practice converges with no lost attempts,
  double XP or changed review deadlines.
- Repeat practice across UTC midnight, time zones and DST remains
  deterministic and compatible with the certified V2 policy.
- Old schema, malformed source, duplicate UUID and conflict ancestor:
  preserve both versions and fail closed instead of overwriting.
- iCloud quota exhausted, unreachable server, app killed during sync and
  remote-account switch: continued local learning and visible sync status.
- Local erase versus optional cloud erase versus uninstall versus export
  have independently tested and clearly stated outcomes.
- No externally identifying tokens, private family identifiers, voice
  recordings or audio response data appear in CloudKit records.
- Minor/guardian cloud consent must pass an independent server and legal
  privacy release gate before enabling for under-18 users.

## Implementation sequence

A. Certify native local export and atomic local reset.
B. **Implemented and native-tested 2026-11-09:** a bounded immutable
   per-attempt journal, preserving legacy aggregates without inventing old
   events. Individual attempt, review and XP updates commit atomically.
C. **Offline candidate merge implemented and tested, not applied:** source-
   verified UUID deduplication, stable order, explicit shared-epoch requirement
   and hard conflict rejection. Projecting complete journals reproduces
   single-device spaced review; cross-device XP and restoration need further
   validation before merged data can change a real profile.
D. Add opt-in CKSyncEngine only after Apple entitlement, signed-device and
   conflict-resolution acceptance; never claim GitHub unsigned CI proves
   iCloud functionality.

Keep PR #169 draft and all original V2 services/accounts intact.
