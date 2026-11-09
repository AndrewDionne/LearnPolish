# V3 execution ledger — GitHub is durable continuity

**2026-11-08. Owner direction: continue developing the full native application; defer owner Xcode install/physical testing until substantially feature-complete.** Automated macOS Xcode builds and iPhone Simulator tests remain required on every tranche. The native PR stays draft until release gates are satisfied.

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
