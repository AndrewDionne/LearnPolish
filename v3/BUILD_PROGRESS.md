# V3 execution ledger — GitHub is durable continuity

## V3-08G — white-square branded iPhone app icon (2026-11-10)

**Implementation:** Locked the owner-approved Path to Polish geometric navy
P, horizontal path and mint endpoint on a **full white square**, no pre-rounded
corners or transparency. The source vector is versioned at
`v3/ios/Brand/AppIcon.svg`; a dependency-free macOS Swift/AppKit renderer
creates an **opaque 1024×1024 RGB PNG** during the existing source/media
preparation. The single-size iOS asset catalog is named `AppIcon` and
XcodeGen now explicitly registers it. The generated PNG is ignored in Git
to avoid a second mutable copy of the branding. CI asserts PNG IHDR,
asset catalog, source vector and Xcode setting before compiling the Simulator.

**First owner device gate:** The phone icon is now part of the
[isolated iPhone functional-beta checklist](IOS_DEVICE_SMOKE.md). The real
iPhone still must show actual native rounding and correct brand visibility;
a CI compile is not a physical phone witness. No legacy/V2 original audio,
course source ID, account, service, cloud entitlement or production setting
is changed. Previous V3-08F [CI #42822803571](https://github.com/AndrewDionne/LearnPolish/actions/runs/42822803571)
**SUCCESS** including iPhone Simulator and XCTest; V3-08G exact-head
verification pending at commit creation. PR #169 remains draft.

---


## V3-08F — one Home Continue path and iPhone device acceptance handoff (2026-11-10)

**Implementation:** Native Home now has a **single** prominent Continue entry
using existing guided vocabulary/grammar progress, then the original core
course when every existing guided reference has at least one actual saved
Learn attempt. Browsing Library and optional sound/scenario activities remains
unrestricted. Original source item IDs and shared Learn/XP/review records are
not duplicated. Core "resume next unseen" ignores stale item position after
a voluntary Library visit, without replacing V2 course IDs or inventing any
unapproved dependency. Two native XCTest cases cover anonymous first-run,
all-skipped progression, 55 source-backed original-record attempts and restart
without a login.

**Device gate:** [first Xcode/iPhone acceptance checklist](IOS_DEVICE_SMOKE.md)
provides an isolated Git worktree launch and exact offline/voice/review/restart
observations. An initial physical functional-beta test is now recommended
after exact-head Simulator CI, **before** full curricular editorial/cloud
release completion. No credentials, Apple cloud entitlements or backend
changes. Prior V3-08E [CI #42820424132](https://github.com/AndrewDionne/LearnPolish/actions/runs/42820424132)
**SUCCESS** — original audio/source checks, Simulator build, XCTest. The
new V3-08F exact-head CI is pending at commit creation; PR #169 stays draft.

---


## V3-08E — guided lesson cursor integrity and unpractised completion feedback (2026-11-10)

**Implementation:** Revisiting earlier prerequisites or exploring future foundation groups no longer overwrites the active guided Continue cursor. A guided item/step cursor is now persisted atomically **before** in-memory mutation; failed writes leave the original cursor intact and surface the existing storage error. Completing a group is navigation-only: it does not mark skipped phrases as learned or issue XP. The final screen reports the actual **N of M phrases practised** rather than claiming saved practice when all items were skipped, and offers **Revisit unpractised** to jump to the first original source phrase without manufacturing completion state. Voluntary free exploration and source-item identity are preserved.

**Regression:** Four new XCTest cases for backward/forward excursions and persisted resume across restart; skipping the full 16-group sequence without learning leaves all 68 items unpractised and returns to the first step rather than declaring proficiency; blocked-write storage preserves previous bytes and cursors; partial source practice finds the next unattempted phrase. Existing graded practice and XP remain the sole completion evidence.

**Verification:** Prior V3-08D [Actions #42815951980](https://github.com/AndrewDionne/LearnPolish/actions/runs/42815951980) **SUCCESS** (lexical audit, Simulator build and native XCTest). V3-08E exact-head GitHub CI pending at commit creation; no physical device or linguistic certification is inferred. Draft PR #169 remains open. V2 source/audio, Neon/Render, family testers, optional CloudKit and speech scoring unchanged.

---


## V3-08D — reproducible Journey 1 word-form first-use inventory (2026-11-10)

**Implementation:** `v3/ios/scripts/audit-guided-lexicon.mjs` inventories all
68 existing Guided Foundations reference occurrences, 55 unique original
recording identities, and **74 distinct case-folded NFC written surface forms**
across 16 ordered groups. [Full review-ready 68-row inventory](JOURNEY1_FIRST_USE.md)
lists source ID, exact original Polish/English utterance, grammar focus, audio
reference and newly seen written forms. **All rows remain Pending independent
native/linguistic review; this is not lemmatization, grammar or sound certification.**
No source phrases, translations, recordings or progress state were changed.

**CI source-drift gate:** Following V2 asset preparation, the native macOS
workflow now checks report equality against the canonical generated catalog
and runs five Node tests, including Polish diacritic/inflection handling,
duplicate original recordings, invalid original text/meaning/audio/status
and an exact checked-in report comparison. V2/Neon/Render/family and all
production settings remain untouched. Prior V3-08C
[Actions #42811630855](https://github.com/AndrewDionne/LearnPolish/actions/runs/42811630855)
**SUCCESS** (Simulator build and native XCTest); V3-08D exact-head CI is
pending at this commit's creation.

**Next:** independent first-use forms and inflection explanations, followed
by a source-ID-preserving coherent Journey 1 path; the guided and main-course
tracks are still separate. PR #169 stays draft; no owner Xcode test requested.

---


## V3-08C — source-derived prerequisite links and Journey 1 continuity (2026-11-10)

Native Guided Practice offers an optional, collapsed **Earlier learning to revisit** section when a declared prerequisite was introduced in an earlier recorded source group with source examples not yet saved as Learn attempts. Source IDs/order are unchanged; no lesson lock, fabricated mastery, new text/audio, gamification or account requirement. Two new XCTest cases check real concept predecessors and partially practised dependencies.

Curriculum audit: [Journey 1 continuity audit](JOURNEY1_AUDIT.md). The 16 guided steps, 68 original audio references and seven grammar introductions are not a complete lexical/phonetic certification. Core Journey 1's 19 lessons remain a separate native progress path awaiting independent editorial integration.

**Verification:** Previous V3-08B [Actions #42809006255](https://github.com/AndrewDionne/LearnPolish/actions/runs/42809006255) has a passed iPhone Simulator build; its XCTest step was in progress at this observation. V3-08C exact-head CI pending. PR #169 remains draft; physical device and real speech/cloud/guardian acceptance are still open. Production V2, Neon, Render and four tester identities unchanged.

---


## V3-08B — single offline daily review across lessons (2026-11-10)

**Implementation:** Adds a compact **Daily review** entry on Home (only when items are due) and a primary **Review up to 20 due** action in Practice. `NativeDailyReviewQueue.snapshot` selects a bounded batch of actual V2 Learn cards across different lessons, oldest due first with deterministic source-order ties. The queue freezes on entry: an incorrect answer remains due in the normal 1/3/7/14/30/60/90-day schedule but never loops inside the same short session. Review displays original Polish, approved audio at 0.75×/1× where present, then meaning and Got it/Needs practice; Skip is non-awarding. Every graded answer uses the V3-08A atomic persist-before-advance boundary. Existing by-lesson review remains available.

**Regression:** Four `NativeDailyReviewQueueTests` validate oldest-first cross-lesson selection, stable 20-card cap, exclusion of unseen/future/reading-only entries and frozen snapshots after progress updates, plus real persisted wrong-answer due and next-day successful recall. No fabricated words, XP, automatic account, new backend or speech scoring.

**Verification:** V3-08A [Actions #42804252300](https://github.com/AndrewDionne/LearnPolish/actions/runs/42804252300) **SUCCESS**: original-source/media checks, iPhone Simulator build and XCTest. V3-08B exact-head CI **pending** at creation; no claim of full validation until run completes. Keep V3 PR #169 draft; the owner explicitly deferred physical Xcode testing until full app surface.

---


## V3-08A — answer submission and lesson navigation durability (2026-11-10)

**Implementation:** Across Learn, Listen, Read, Speak and Guided Foundations, a submitted answer now advances or locks in a selected choice **only after** `LocalLearningStore.recordAttempt` returns success. `NativePracticeSubmission.commit` is the single persist-before-UI boundary. Failed storage writes leave the same card and choices available for retry and show the existing storage error; deliberate Next/Skip remains non-awarding navigation. Both native multiple-choice modes defer their selected-answer state until after a successful write. No scoring, content, account, audio, Neon or Render changes.

**Regression coverage:** `NativePracticeSubmissionTests` exercises all four native practice modes with blocked storage (no callback, no journal/XP/review, original bytes preserved), plus accepted answers verified from reloaded disk **inside** the navigation callback. Guided Foundations shares the exact same submission method.

**Verification:** Prior V3-07E [Actions #42802763331](https://github.com/AndrewDionne/LearnPolish/actions/runs/42802763331) completed **SUCCESS**, iPhone Simulator compiled and XCTest phase passed. New V3-08A source awaits its own exact-head GitHub iPhone Simulator CI result. V3 remains a draft PR; owner phone testing is intentionally deferred. Live CloudKit, guardian-safe family features, real speech calibration and bilingual curriculum review are still separate unverified release gates.

---


**2026-11-08. Owner direction: continue developing the full native application; defer owner Xcode install/physical testing until substantially feature-complete.** Automated macOS Xcode builds and iPhone Simulator tests remain required on every tranche. The native PR stays draft until release gates are satisfied.

## V3-07D — manual private-CloudKit recovery, conflict preflight and no-network consent guard (2026-11-10)

**Exact verified code head:** `a8fe33b816f4ab760697e8ced3a9f03364506d2f`. [Actions #42798542713](https://github.com/AndrewDionne/LearnPolish/actions/runs/42798542713) **SUCCESS** — full iPhone Simulator **BUILD SUCCEEDED**, **171 native XCTest passed, 0 failed**, original V2 lesson/media and JS source-integrity suites passed. Prior [CI #42797370802](https://github.com/AndrewDionne/LearnPolish/actions/runs/42797370802) verified 168 native tests at the preceding implementation head.

- `NativeCloudSyncPlanner.swift` introduces a **read-only original-source-verified preflight** for explicitly invoked remote journal writes: initial creation only when no previous server revision, no-op for identical history, upload only when every remote event is already in local journal, and **refuse/review** if another device contains unseen events. Duplicate UUIDs with conflicting payloads, stale/missing formerly seen server records, foreign learner identities, a retained tombstone, incomplete historical journals and unrecorded regions fail closed; no XP or profile mutation.
- `NativeCloudKitPrivateTransport.readManually` now enforces the separately persisted, explicit private-cloud opt-in gate and bound learner identity before reading records; an observed remote tombstone is **persisted locally** as a terminal deletion before any attempted future upload. Manual upload reuses the planner and does not needlessly rewrite an identical record. The private pending-delete recovery path can still inspect an existing server tombstone to complete interrupted deletion acknowledgement. CloudKit server change-tag CAS remains the final network race boundary.
- `NativePrivateCloudGate.requireActiveLocalLearner` is a **zero-network preflight** before even calling `CKContainer.accountStatus` / `userRecordID`. Opt-out, paused-account, pending-delete, remotely-deleted, wrong-learner and missing-epoch conditions are refused synchronously. A later account and generation check is still mandatory at the network boundary.
- `NativeCloudSyncPlannerTests.swift`: 12 tests for two divergent simulated-device histories, original-source validation, duplicate upload no-op, remote-ahead review, stale/missing server, tombstone, identity, legacy, unknown source and conflicting UUIDs. Three new `NativePrivateCloudGateTests.swift` verify local refusal before any Apple account lookup.
- **Strict limit:** These are source-bound unit tests plus Swift/SDK compilation, **not live CloudKit service acceptance**. The running native app still has **no iCloud entitlement, automatic startup path, CloudKit Settings UI, enabled background synchronization or Apple account prompt**. Real signed two-device races, conditional revision and persisted deletion on Apple's service, quota/offline/kill/retry, large-journal chunking, guardian-authorized cloud usage and physical app acceptance remain unverified. Keep PR #169 draft and production V2/Neon/Render/four tester identities unchanged.

---

## V3-07C — real CloudKit private-record transport, manually invoked and not yet activated (2026-11-09)

**Exact verified implementation code head:** `791e3ae7af044b8e503baaa1efff89b9a13154b8`. [Actions #42691929108](https://github.com/AndrewDionne/LearnPolish/actions/runs/42691929108) **SUCCESS** — native iPhone Simulator **BUILD SUCCEEDED**, **156 XCTest passed, 0 failures**, original V2 media/source integrity and Node tests passed.

- Previous code at `9d56b2a014b46e145e5bb4538f3ab616339af1e1` [CI #42683775128](https://github.com/AndrewDionne/LearnPolish/actions/runs/42683775128) was fully green: 144 native XCTest passed, establishing safe offline account-pause/remote-delete-policy persistence across restarts.
- `NativePrivateCloudGate.observeVerifiedServerRevision` tracks server-verified, monotonic revisions and refuses unrelated scopes or unverified generations.
- New `NativeCloudKitPrivateTransport.swift` compiles against Apple's real CloudKit SDK. It uses the **private** database, verifies the active iCloud account only on explicitly invoked operations, stores a bounded original-source-valid `NativePracticeJournal` in a stable record, and uses CloudKit's `ifServerRecordUnchanged` **server change-tag compare-and-swap**. On a race it refuses to overwrite the newer record rather than silently retrying. Existing remote attempts not present on the device must be manually merged first.
- Remote erase retains an authenticated generation-bound **tombstone in the same record** rather than deleting the record/zone, and the pending deletion remains locked by `NativePrivateCloudGateStore` until CloudKit returns a verified server acknowledgement. Source-constrained payload contains **no family account, microphone audio, speech-provider transcript, or client-computed XP**; v1 payload max 450 KB and rejects oversized journals rather than truncating.
- New `NativeCloudKitPrivateTransportTests.swift` adds **12** native tests: source-bound encoded round-trip, epoch and original region integrity, refusal of legacy/unsupported/forged history, retained tombstone semantics, future schema rejection, size limit, generation check, privacy fields, and stale remote candidate constraints.
- **Important release boundary:** This transport is **not referenced from first launch or the SwiftUI Progress screen** and **no CloudKit entitlement or container provisioning was added**. GitHub simulator compilation is NOT a real CloudKit account, network, concurrent private record, signed device, or deletion witness. Do not claim production iCloud sync is enabled. CKSyncEngine/push/background sync, conflict user experience, large journal chunking, quota handling and multi-device live service verification remain open. Existing opt-in private-family pilot, anonymous offline app, V2/Neon/Render and 4 family tester identities are untouched.
- **Next:** signed account/entitlement provisioning and isolated CloudKit functional tests, two-device stale CAS/tombstone recovery, user-visible sync review/enable controls ONLY after the signed tests pass, independent guardian-authorized child features and real speech/editorial/hardware acceptance. Keep PR #169 draft.

---

## V3-06B — immutable practice journal and offline merge candidate (2026-11-09)

**Exact implementation code head:** `78173bacf33821ca629ae0dea4d9704e14265536`. **Native CI [#42608744715](https://github.com/AndrewDionne/LearnPolish/actions/runs/42608744715) PASS:** original source/audio checks and Node guard tests, iPhone Simulator **BUILD SUCCEEDED**, **78 XCTest passed, 0 failed**.

- `v3/ios/Sources/NativePracticeJournal.swift` adds a bounded, source-verified, immutable UUID-per-attempt journal containing only actor-local anonymous UUID, original lesson:item ID, mode, timestamp and an understood/needs-practice/recorded outcome. It carries no audio, transcript, remote score, identity token or family XP. Source mode, restricted Listen items, invalid outcomes, duplicate UUIDs, journal version and event cap are checked before considering remote application.
- `LocalLearner.practiceJournal` is an optional Codable field so older saved profiles load unchanged. A journal started **after** old progress marks `hasLegacyHistory=true`; no invented events or unearned XP are synthesized for old aggregates, including old XP-only records. Legacy histories are **ineligible** for automatic candidate merge.
- The central `recordAttempt` now commits one real event, the existing PracticeRecord review update and the original device-local daily-deduplicated XP **together in one atomic file replacement before publishing the profile**. Failed writes publish no attempt, review or XP. Tourist practice cannot advance its completion counter if the underlying attempt fails to persist.
- A **pure offline candidate merge**, not invoked by UI/cloud, is deterministic/idempotent by event UUID; identical repeated events deduplicate, same-ID payload conflicts hard-fail, different anonymous epochs or incomplete legacy histories reject, and original V2 source IDs/modes must validate. The projected review reducer matches current 1/3/7/14/30/60/90-day spacing on complete journals only. **It does not apply merged history or award merged XP.**
- `NativePracticeJournalTests.swift`: 10 additional native tests cover live event journal/XP parity, restart/export, legacy aggregates, two-device commutative/idempotent merger, foreign epoch rejection, conflicting UUID, bad source/outcome, local reset/ID rotation, bad storage atomicity, and legacy XP-only case.
- **CloudKit still OFF**: no entitlements or account prompt, no sync writes or network calls. Formal merge-to-profile and cross-timezone XP reducers, explicit owner linking/restore UX, cloud tombstones and Apple signed two-device tests remain open. V2/family account services unchanged.

**Next:** build an authenticated or user-confirmed safe archive import/restore with rigorous source/identity validation and an automatic pre-restore backup; then a tested pure XP reconciliation policy before opt-in CloudKit. No owner Xcode install until full application acceptance; PR #169 remains draft.

---

## V3-06A — local privacy export/reset and CloudKit-safe groundwork (2026-11-09)

**Exact native code head:** `5aa02c5162f765935c0604982140e3db1fbd6155`. **CI [#42598104496](https://github.com/AndrewDionne/LearnPolish/actions/runs/42598104496) PASS:** original source-locked curriculum/media validation, iPhone Simulator **BUILD SUCCEEDED**, **68 native XCTest passed, 0 failures**. The earlier V3-05B mislabelled UTC-day fixture was corrected; family-source XP now rejects out-of-scale values.

- `LocalProgressArchive.swift` introduces an explicit user-exported, versioned, bounded JSON document for the **local learning profile only** (course positions, review, anonymous local ID, tourist history and personal XP). It includes no family session, account credentials, provider scores/transcripts, cloud identifier or microphone recording. User chooses the export destination with the native document exporter; exported JSON is not encrypted, and UI warns to keep it private.
- `LocalLearningStore.swift` has a separately confirmed **local-only erase**, which writes a new profile with a fresh anonymous local ID atomically **before** publishing it. On an unreadable saved profile or storage failure, reset refuses and leaves the original file untouched. The lesson/audio bundle is not deleted, and the operation does not touch family-server contributions or any previously exported copy.
- The Progress screen exposes the export and erase actions; new native `LocalProgressArchiveTests.swift` cover source-bound archive decode, sensitive-field exclusion, unchanged source file after export, restart after reset, corrupted-file preservation, atomic-write failure and forward schema rejection.
- `v3/CLOUDKIT_SYNC_DESIGN.md` locks the **user-opt-in private iCloud** design and exact conflict/identity/migration acceptance. CloudKit is **not enabled**: current LocalLearner aggregates cannot be safely merged across devices, and automatic whole-file upload could lose reviews/double-award daily XP. No Apple/iCloud account prompt on app launch, no entitlements, and no CloudKit network calls. Future event-journal migration and two-device tests precede signed-device iCloud activation.

**Outstanding:** import/restore of owner-exported JSON, bounded per-attempt journal for safe cross-device conflict resolution, production CloudKit account/entitlement and multi-device testing, guardian-authorized connected use for minors, provider speech calibration, complete curriculum/editorial certification and integrated physical iPhone acceptance. Maintain draft PR #169; do not modify main or V2/Neon/Render.

---

## V3-05B adult pilot privacy boundary — implemented, simulator regression verification in progress (2026-11-09)

- The prior native V3-05A integrated run [#42491145355](https://github.com/AndrewDionne/LearnPolish/actions/runs/42491145355) compiled, with **60/61 native XCTest passing**. Its sole failure came from a test timestamp labelled prior UTC day that was actually midnight on the same UTC day. The UTC-day fixture is corrected.
- Source-backed V3 now contains 32 recorded alphabet examples, 13 combinations, 5 sound lessons / 25 ear questions, six Read dialogues / 51 lines, seven source-first Listen sets, and eight original tourist scenarios / 22 mode stages. These are native functional screens, not separate toy apps.
- Optional verified V2 family login, 16-region server-only group expedition and weekly leaderboard, same-UTC-day opt-in source-item activity sharing, and original Azure+Whisper source-bound assessment transport are on the draft branch. Private V2 provider deployment remains **disabled** and live calibration/physical tests are not claimed.
- **V3-05B gate:** all connected features are an **explicitly acknowledged, in-memory adult-only pilot** (18+ using their own account). Without acknowledgement there is no optional family authentication request or speech connection. Offline language study is available to everyone. This is **only self-attestation**, not verified guardian authority, and does not authorize children to use connected features.
- The server's existing pilot signup and identity endpoints do not expose a verified guardian relationship or per-purpose child consent. Child family participation and remote voice uploads remain **blocked** until server-authoritative guardian grants, revoke/delete controls and acceptance tests are approved. See [v3/FAMILY_PRIVACY_GATE.md](FAMILY_PRIVACY_GATE.md).
- **Exact-head CI:** [#42589284869](https://github.com/AndrewDionne/LearnPolish/actions/runs/42589284869) iPhone Simulator **BUILD SUCCEEDED**; new expanded XCTest checks are not yet certified at this note's creation.

**Owner instructions remain:** keep PR #169 draft, V2/Neon/Render and the four tester records unchanged, defer owner Xcode phone build until the complete functional surface.

---

## V3-03a guided Foundations / first grammar — implemented and simulator-certified (2026-11-08)

**Commit head:** `b51f243cb0fb864d4395c275e3c61b35b8709792`  
**CI:** [V3 native iPhone run #42472992095](https://github.com/AndrewDionne/LearnPolish/actions/runs/42472992095) — generated source/audio assets, project, iOS Simulator **BUILD SUCCEEDED** and **TEST SUCCEEDED**. **5 Node source-compiler tests + 17 native XCTest tests passed, zero failures.**

- `v3/ios/scripts/prepare-guided.mjs` projects four existing V2 C-13 source files into `guided-foundations.json`. **16 prerequisite-ordered activities, 68 original full-recording references, 7 source-authored grammar introductions**. Original lesson:item IDs, phrases, translations, audio and existing source status are preserved. Reused items are deliberate, not duplicate progress identities.
- Build gate rejects altered original Polish/English/audio, restricted source recordings, invalid focus spans, missing/extra groups, wrong editorial status, missing prerequisites and out-of-sequence concept introductions. No newly synthesized Polish or manufactured recordings.
- Native `GuidedFoundationsScreen` shows First words → Basic vocabulary → First sentences / basic grammar with source-validated groups. `GuidedPracticeScreen` plays existing audio at 1×/0.75×, introduces original meaning and source-author explanations before recall, and optionally emphasizes the existing authored text focus. Skip/reveal/play never earn XP; only a real self-rated attempt writes the original Learn progress, spaced review and daily-deduplicated personal XP.
- Separate guided activity cursor persists across restart, without changing original Core Continue or Library exploration; last-item advancement moves to the next actual source step. No sign-in or network access.
- **Certification boundary:** structural prerequisite closure does not prove the full language program is complete; the original V2 human review and recordings remain source-only, not independently native-speaker certified. This migration does not cover separate reading/listening first-exposure, alphabet teaching, sound lessons or applied tourist roleplay. Remote Speak remains offline-only record/replay in V3.

**Owner decision unchanged:** no user Xcode install/physical testing until complete feature integration. Keep PR draft, preserve Neon and family identities.

---

## Implemented on draft PR #169

- Native SwiftUI iPhone app, first-run account-free home/library/practice/progress; optional accounts and iCloud do not block offline study.
- Generated genuine 26-lesson / 482-item V2 library with 455 original MP3s and 481 total source-backed audio references. Preserve source IDs, reference blockers and draft grouping qualifications.
- Exact source-authored V2 core journey order: **21 core placements**, plus 5 exploratory entries. No fabricated Journey 3 or native approval of editorial drafts.
- Library browsing no longer replaces selected core course Continue. Home explicitly resumes first unvisited source item; optional two original Numbers 1–10/11–20 sections use strict source and audio checks.
- V2 Learn, Read, Listen and local Speak practice foundation. Listen excludes source-blocked speech recordings, uses original authored comprehension checks where supplied and V2 choice ordering otherwise; Read does not invent assessments for lines without authored questions.
- Original V2 1/3/7/14/30/60/90-day 24h spaced review; frozen due-item session, optional repeat and no forced pass threshold. Local records remain anonymous and written atomically.
- Native AVFoundation 0.75x/1x reference audio and quality-gated local microphone capture/replay. Optional authenticated Azure+Whisper adapter is source-bound and double-consented, but the hosted scoring feature stays **OFF** pending acoustic/provider acceptance; no invented syllable accuracy.
- Local original V2 effort XP ledger, same once-per-mode/item/local-calendar-day deduplication and personal map taper; original 16 V2 region outlines drive distinct native personal and family maps. Family XP stays server-authoritative and does not backfill or overwrite local records.
- Native source and asset XcodeGen project, GitHub macOS iOS Simulator CI, regression tests for journey/source geometry/selection/XP/persistence.

## Still substantially incomplete (do not call full app)

1. **Guided teaching inside Journey 1:** native guided 16-step foundations, recorded alphabet, sound lab, source-first Read/Listen and eight tourist scenarios are implemented. **Still missing**: complete independent linguistic/prerequisite audit, content authoring for unsupported gaps and real bilingual editorial sign-off. Content remains editor-review gated.
2. **Speak production:** optional private API contract, WAV conversion, double per-take consent and in-place segmented-colour overall estimate are coded. **Still missing**: real authorized provider deployment, acoustic validation, calibrated/blind rating study, reliable latency and independent guardian policy; never claim syllable-level acoustic certification.
3. **Family:** optional verified connection, adult-pilot acknowledgement, original server leaderboard/map and explicit source-only family XP submission implemented. **Still missing**: authoritative guardian relationship/consent and minor-safe backend; existing 4 tester accounts preserved. No mandatory sign-in.
4. **iCloud:** independent feasibility spike for private progress sync, optional sharing, Apple entitlements, collision/merge semantics and offline return. Do not automatically switch backend.
5. **Complete content and editorial QA:** missing fundamentals, conversational practice, reading/listening instruction, rights-cleared audio/native acoustic validation. Migration itself does not certify missing content.
6. **App completeness:** settings, offline assets management, account/privacy/export/delete, complete course and content authoring, robust navigation and review session flows, polish/performance/accessibility and application icon/release packaging.
7. **Physical acceptance and release:** not yet requested from owner; no physical Xcode install/phone testing until full functional surface and automated parity are ready.

## Next recommended implementation tranches

- V3-03b: native recorded alphabet and Sound Lab, source-first Read/Listen preteaching and tourist application checkpoints, all source-locked and independently tested.
- V3-04: pronunciation transport/response contract, consent and offline fallback; server-once/no secret in app; calibrate against verified real recordings separately.
- V3-05: family connection and XP reconciler; native map family view, privacy, profile controls.
- V3-06: iCloud optional sync/sharing spike; remaining UI/authoring/gap closure and full end-to-end acceptance.

## Security, merge and device policy

Never repurpose original family provisioning, rotate secrets, reset Neon, or modify Render production during a native UI tranche. No app signing credentials in GitHub. A passing simulator compile is not evidence of hardware microphone/voice quality or production readiness. Keep PR #169 **draft** and V2 release issue #2 open. The owner explicitly elected to **defer their own Xcode build** until V3 is complete; do not make every partial native tranche a new physical test request.
