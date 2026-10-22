# Path to Polish V2 — development while physical testing is deferred

## Delivery checkpoint — 2026-10-22

- **DPT-01 merged:** [PR #97](https://github.com/AndrewDionne/LearnPolish/pull/97), four CI lanes green; authenticated private-group lifecycle and late-response isolation.
- **DPT-02 restore and download protection merged:** [PR #98](https://github.com/AndrewDionne/LearnPolish/pull/98), squash `fb5a34f433c94f289353500df12614b3e84d8dc3`, [four final-head CI lanes green after a targeted stalled-runner retry](https://github.com/AndrewDionne/LearnPolish/actions/runs/39819216754). Backup storage is committed before showing success and rolls back prior keys on quota failure; offline MP3 download promotion rolls back incomplete cache writes.
- **DPT-02 removal and UI retry follow-up MERGED:** [PR #99](https://github.com/AndrewDionne/LearnPolish/pull/99) squash `8551cf6ff2c81a240f34eb7496fb253ffe99f70e`, [CI #39823136038 all four PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39823136038). Multi-MP3 offline REMOVE rollback, retry the intended operation and stale-lesson response isolation.
- **DPT-02 reconnection and duplicate-completion final gate MERGED:** [PR #100](https://github.com/AndrewDionne/LearnPolish/pull/100), squash `c0542f714b2471d799d3f839217592d880ac18fc`, [CI #39831474180 attempt 2: all four PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39831474180). Per-rendered-answer synchronous double-activation guard, genuine offline→reconnect no-replay and corrupted/duplicate-XP backup refusal. **DPT-02 complete.**
- **DPT-03 synthetic accessibility and audio lifecycle audit MERGED:** [PR #101](https://github.com/AndrewDionne/LearnPolish/pull/101), squash `a1f07339ea234e8c14db8087ba10a3951b293c18`, [CI #39847987332 all four PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39847987332). Read, scheduled reviews, Expedition, 320px layout, audio lifecycle; corrected Practice/review-complete/Expedition contrast and interactive map semantics. CI uses GitHub-hosted Google Chrome on pinned Ubuntu 24.04 with isolated fixed-version FFmpeg; local Playwright Chromium remains unchanged. No physical device, mic or artistic sign-off.
- **DPT-03 temporary catalog recovery MERGED:** [PR #102](https://github.com/AndrewDionne/LearnPolish/pull/102), squash `a81cc30b9f2a74b302a1c2064acb2e30336ef652`, [CI #39849979684 all four PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39849979684). Retry temporary catalog fetch without losing local progress; service-worker excluded only from controlled HTTP-failure fixture.
- **DPT-03 empty/error-state and keyboard focus audit MERGED:** [PR #103](https://github.com/AndrewDionne/LearnPolish/pull/103), squash `3d86b2d0b44f019b62f3e9ca42c4052c5d7a52f7`, [CI #39851619008 four of four PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39851619008). Stable keyboard Enter navigation, mode focus, unchanged XP during navigation, no-due Practice and empty Library, catalog error/accessibility; repaired shared empty/error copy contrast.
- **DPT-03 navigation performance/rapid-interaction synthetic audit IN DEVELOPMENT:** three rounds of destination/focus/XP integrity across five primary routes on desktop/mobile, log actual median/p95/max completion times and enforce only a generous five-second hang guard; same-task rapid mode and route switches must settle at latest destination without new XP/review events. Four final-head CI checks required before merge.

**Decision locked 2026-10-22.** This is the approved execution order until real-device/manual audio work resumes. GitHub code, issues, CI, and this document are the durable authorities; a chat response is not a delivery record. This roadmap is complementary to [V2_REBUILD_PLAN.md](../V2_REBUILD_PLAN.md) and [issue #2](https://github.com/AndrewDionne/LearnPolish/issues/2).

## Principles

- Proceed with *testable behavior* and synthetic browser + isolated service tests; do not wait for physical equipment to fix deterministically reproducible defects.
- Preserve one React V2 and one authenticated private family service. Never create a second account system, scoreboard store, ranking formula, activity ledger, or automatically cloud-sync browser progress.
- Keep owner-approved three learning stages, 26 built-in lessons/482 original items, the single Numbers 1–20 lesson with optional 1–10 and 11–20 sessions, and open 16-region Poland map. No automatic splitting of any other lesson.
- Preserve consent for shared practice; group changes **must reset** opt-in. Server, not UI, authorizes membership and awarded group XP. Most improved remains unavailable without verified comparable human/phonetic evidence.
- Retain original source MP3s and the 14 excluded Speak references until independently reviewed. Approved speeds: 0.75×, 0.85×, 1× only.
- No live provider calls, paid usage, public deployment, fabricated pronunciation feedback, new avatar artwork, native-speaker claims or physical-test sign-off through this roadmap.

## Queue, acceptance gates and merge order

### DPT-01: Authenticated learning-group lifecycle and request isolation — first

1. Signed-out, expired or revoked session cannot display retained private group membership, rankings or invitation codes. Clear pending requests, group selection and contribution consent when an identity becomes invalid.
2. Switching from Group A to B during a late response cannot show Group A's scoreboard or invitation in Group B. Switching groups, leaving/removal and sign-out invalidate outstanding private UI responses.
3. A delayed invite response, refresh failure or activity-triggered refresh must not reopen a discarded group. Transient network errors remain distinguishable from revoked membership; never silently opt in after recovery.
4. Reuse existing service endpoints and server-side group scoping; cover backend negative authorization and Playwright delayed-response races with mobile/desktop fixtures and the connected private browser lane.

**Gate:** Four CI lanes PASS; no regression in multi-group, membership removal, one-use/revoked invites, onboarding, access recovery, single-group recognition or manual privacy choices. Track any physical-login unknowns explicitly.

### DPT-02: Offline and local-data integrity

1. Test interrupted/partial audio cache writes, retry and accurate offline availability, storage quota denial and page reload with network disconnected.
2. Reject malformed/corrupt backups without overwriting good local learning state, verify round-trip under mixed personal/built-in lesson data, and verify recovery after storage write failures.
3. On reconnect avoid duplicated local XP/reviews or fabricated cross-device syncing. Family practice contributions remain *separate* from offline local progress and require explicit group opt-in.

**Gate:** Deterministic offline/browser fault-injection, zero misleading completed-download states, no lost or duplicated personal progress, four green CI lanes.

### DPT-03: Exhaustive synthetic UX, performance and accessibility audit

1. Walk Home → Library → Learn/Listen/Speak/Read → Review → Profile → Groups/Expedition in desktop and small-phone viewports; cover navigation, in-flight audio cancellation, empty/loading/offline/error states, focus/keyboard behavior.
2. Extend screenshots, WCAG A/AA serious/critical checks, 320px overflow/clipped-control geometry, and regressions for screen switching. Fix bugs before aesthetic redesign.
3. Treat synthetic scores and screenshots as *supporting evidence*, never a real iPhone mic/Safari, human visual acceptance or linguistic/acoustic evaluation.

**Gate:** End-to-end stable runs, representative screenshot artifacts, four green CI lanes.

### DPT-04: Pronunciation infrastructure and low-cost provenance (parallel where independent)

- Provider-neutral and identical-byte audio fixture contracts, clipping/silence/network-failure `inconclusive`, no unexpected provider requests, usage/cost caps, deterministic replay and truthful Whisper/Azure metadata.
- Scoring accuracy, phoneme meaning and provider preference **not approved** without labelled natural Polish recordings and human listening. Keep 14 practice-only references excluded from Listen/scored Speak.

### DPT-05: Curriculum and content integrity (parallel, no expansion)

- Strict mapping and reference-link checks for original 26 lessons, Polish source text, translation, stage/course metadata, stable IDs, audio references, and the 14 guarded Speak targets.
- Native idiom/sound/recording quality claims and new dialogue/audio production deferred to native review. Do not invent extra lessons or segment on arbitrary counts.

### DPT-06: Optional profile/recognition refinement (after correctness gates)

- Consider avatars, visually engaging family scoreboard summaries, and weekly recognition history only if justified by evidence. Never award unverified improvement, tie cosmetic work to authorization, or introduce an XP economy change as an incidental UI task.

## Process

Each coherent DPT change is a focused PR against `main`, with its own tests and the four established CI jobs: frontend build/migration/unit/desktop+mobile/axe, private family backend, connected family browser and benchmark harness. Merge **only** after all lanes pass at the final head. Record SHA/CI/known limitations in GitHub issue #2 and the workflow continuity record. Return to physical tests for reference audio quality, actual mic/Safari playback, voice assessments and human visual review without treating them as prerequisites for DPT-01–03.
