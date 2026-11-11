# V3 decision record — native SwiftUI, account-optional and local-first

**Date:** 2026-11-08  
**Status:** approved direction; native implementation in progress  
**Repository:** `AndrewDionne/LearnPolish` (same repository; V2 stays intact)  
**Branch:** `ai/v3/swiftui-local-first`

## Locked product decisions

1. **Real native iPhone application.** SwiftUI is the primary V3 learning interface. Not a WKWebView, website wrapper, empty prototype, or separate repository.
2. **No mandatory sign-in.** First launch goes immediately to a real lesson. No email, password, account creation, iCloud authorization dialog, subscription prompt or profile form to begin learning.
3. **Local-first and offline-capable.** The app persists learner state on the device without network access and bundles actual existing curriculum and licensed/reference audio for offline playback. No fabricated audio or linguistic approvals.
4. **Preserve V2 assets, learning contracts and stable IDs.** The V2 curriculum remains the versioned source while migration is in progress. Do not erase or edit legacy source IDs, core progression, lesson prerequisites, review semantics, XP policies, or privacy/consent requirements.
5. **Account and cloud are optional capabilities.** Investigate optional Apple iCloud private sync first. Actual CloudKit sharing, conflict resolution, Apple entitlements and child/guardian flows must pass an independent spike before replacing any backend or promising cross-device persistence.
6. **Keep existing Neon/Render family backend and four tester identities untouched.** Do not migrate, provision, reset, revoke or auto-sign-in accounts. The family service remains the authoritative source for shared XP/group memberships until a tested replacement exists. Optional connected family login is a later separate flow, not a first-run gate.
7. **Local capture, consented remote speech only.** AVFoundation-based capture/playback and replay are local. Azure/Whisper scoring requires explicit permission, credential-safe server mediation and real acoustic testing. No keys embedded in client, no fake pronunciation or syllable scores, no automatic remote uploads.
8. **Keep minimal UI.** Focus on the learning path, Listen/Read/Speak, clear feedback, 0.75x/1.0x playback, and simple continue/retry controls. Do not introduce onboarding tutorials or unrequested gamification.
9. **SwiftUI becomes the primary learner client.** The React/Vite V2 implementation stays runnable for parity tests/reference and the existing API; no parallel V2 feature expansion solely for UI parity.
10. **GitHub as durable source.** Implement via reviewable draft PR, tests and clear physical-device release gates. Never claim an untested Xcode build is certified.

## Architecture

```
SwiftUI iPhone client
  ├─ Bundled, versioned V2 lesson manifest + mapped MP3 assets
  ├─ Native lesson navigation + local assessment/review engine
  ├─ Application Support / atomic local progress store
  ├─ AVAudioPlayer and AVAudioRecorder for sound practice
  └─ Optional future connectivity:
      ├─ iCloud private sync (only after signed-in entitlement/conflict testing)
      ├─ secure V2 family API / Neon for group participation
      └─ consent-gated private speech assessment API
```

A locally generated anonymous profile ID is an internal record key, not an app account; no network transmission or onboarding consent is implied.

## Explicit non-goals in first native tranche

- No automatic CloudKit sync or silent linking to an Apple account.
- No bypass of backend authentication or public unauthenticated group score submission.
- No replacing V2 backend, deleting hosted data, or modifying live tester credentials.
- No claiming provider-calibrated syllable scoring or certified content beyond V2 evidence.
- No shipping to children, App Store or production before privacy, acoustic and on-device testing.

## Native delivery sequence and completion gates

- **A. Foundation:** compile and validate native projection of existing `lessons.json`, preserve original IDs and audio paths, enforce no duplicate IDs or missing media, add deterministic catalog tests.
- **B. Functional SwiftUI:** Home/Continue, lesson library and filters, Learn, Listen, Read, Speak (local record/replay), local progress and review, native iPhone icon/launch and recovery from restart. Real bundled lessons; no demo fixtures masquerading as release data.
- **C. Progress parity:** compare native outcomes with V2 on representative lessons, test atomic persistence, mode separation, card batching, last position and review scheduling.
- **D. Connected service spike:** iCloud availability and failure modes, CloudKit conflict strategy, sharing model and family/minor privacy; leave Neon family API isolated until demonstrated parity.
- **E. Physical release gate:** Xcode iOS simulator build plus owner iPhone test: first-run without account/network; Listen 0.75/1x; Speak mic permission, recording and replay; full lesson; force quit/relaunch; offline; eventual grouped account permissions and real provider speech assessment.

## Migration protections

Existing `v2/frontend`, `v2/server`, `docs/sets`, `docs/static`, `ptp_v2` Neon schema and production Render configuration are **not** changed by the V3 native tranche. Generation reads the current V2 catalog, does not mutate it. `main` merges only after relevant GitHub and device verification.

## Status of this tranche

Record and implementation are proposed on a draft PR branch. Passing static validations does not prove SwiftUI Xcode compilation; report precisely which checks have and have not run.


## Owner refinement, 2026-11-11: activity-centric learning

The old per-card Learn/Listen/Read/Speak picker is an interim migration design and is superseded by the approved objective to curate a single sequence with distinct Speak (original audio + meaning + speaking feedback), Learn (vocabulary recognition/retrieval, optional flip card) and Listen (real dialogue comprehension). Home is a personal and optional team progress dashboard, not a course list; Library is browse-only and organized into small source-backed journeys plus Extras; Practice owns all started, paused and resumed activities. Only genuine results may appear as scores, and pronunciation grading requires independent acoustic/provider acceptance. See [UX_LEARNING_ARCHITECTURE.md](UX_LEARNING_ARCHITECTURE.md) for the current implementation phases and release gates.
