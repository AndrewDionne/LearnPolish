# Path to Polish V2 — Rebuild Scope and Delivery Plan

**Status:** V2 development active (2026-10-16). Initial foundation/Library→Learn capability merged in [PR #3](https://github.com/AndrewDionne/LearnPolish/pull/3), commit `c89010c4fd6c603f885c996d51231f8148037fea`; personal lesson editor/import/export merged in [PR #4](https://github.com/AndrewDionne/LearnPolish/pull/4), commit `5bd2649013aa565f86c2c93bcbc036d73c5381a9`. T0/T1 gates remain partial; Read/Listen and verified offline PWA capability have now been merged in PRs #5 and #6, but release gates remain open; see [umbrella issue #2](https://github.com/AndrewDionne/LearnPolish/issues/2) for checkpoints and CI evidence.
**Repository:** `AndrewDionne/LearnPolish` (retain; do not create a second repository).
**Owner's product decision:** The current application is unused and may be replaced without preserving its existing runtime behaviour or uptime. Preserve useful learning content and historical source, **not** legacy design or architecture.
**Related pronunciation decision:** [Issue #1](https://github.com/AndrewDionne/LearnPolish/issues/1).

## Reward-system direction — owner decision 2026-10-16 (design only)

- **Retire the Pierogi characters from the intended V2 reward UX.** They remain in historical code/assets for now; do not spend time ripping them out before replacing the view. Shift from Gold-as-currency toward **XP for real effort, additional XP for demonstrable improvement, and team achievements**. Reuse existing earned-event data where safe rather than discarding it.
- **Private family learning groups**, with encouraging, optional and friendly weekly leaderboards. Recognize distinct strengths: effort, most improvement relative to baseline, highest unlocked learning difficulty, consistency, and contribution to the group. Shared progress is permanent even when weekly leaderboards reset. No individual speech recordings exposed publicly.
- **Open interactive map of Poland:** any Polish region can be selected at any time, irrespective of adjacency or prior unlocks. Family members can coordinate organically, but the application **does not require votes or orchestrate a route**. Individuals can independently focus/contribute XP toward a different region ("go rogue"); their progress still benefits the family's map. Unlocked regions remain permanently open. Region costs grow with progression according to a moderate configurable power curve, not a mandated fixed route.
- **Learning difficulty and reward growth must rise together.** Later/harder lessons earn more qualifying XP, while more costly regions and anti-repetition eligibility make exploring all Poland via beginner-content farming impractical. Keep effort recognition meaningful to beginners; avoid punishing children or low-volume participants.
- **Design for functioning pronunciation scoring at launch**, rather than creating temporary scoring/reward code to remove later. Make the reward model accept *verified learning outcomes* from Learn/Read/Listen and a future vetted Speak phonetic assessor through the same small stable interface. Speaking improvement bonuses depend on measured change from a learner baseline. An absent/inconclusive result is not zero or a fake grade, and Speak still earns base effort XP for a usable attempt. Do not tie XP to Whisper transcription accuracy alone.
- **Avoid make-work / premature implementation.** This is a product design decision, NOT a request for an XP rewrite now. Keep existing PR #13/#14 behavior operational until one coherent UI + event-ledger + group/map tranche can replace it. Exact XP amounts, difficulty classification, region-cost formula, allocation rules and social access control need refinement during implementation; do not hard-code arbitrary constants at this stage. No content authoring. Continue the real AI evaluation with existing privacy and zero-spend gates.

## Latest completed development — private Speak corpus, 2026-10-16

[PR #15](https://github.com/AndrewDionne/LearnPolish/pull/15), squash commit `b33bbf04ea4763118cf22d957fda8bfd71e7f1f8`, adds timestamped/ID-preserving 16-kHz Speak research WAV export, automatic offline exact-Polish manifest construction, verified SHA-256 file identity, silent/duplicate/unknown-ID and volume-cap rejection, and a browser test for delayed mic permissions after switching screens. [CI passed](https://github.com/AndrewDionne/LearnPolish/actions/runs/38959948628): 38 unit tests / 39 browser tests plus Python dry-run benchmark protections. **Still no actual Whisper/Azure model inference or native Polish ratings**. Real private samples and a confirmed no-spend inference environment are the next gate. **Keep family expedition XP/open-map and no-Pierogi reward direction; do not implement make-work temporary scoring.**

## Family account privacy and departure — merged 2026-10-17

[PR #20](https://github.com/AndrewDionne/LearnPolish/pull/20), `4be22fc642668dd143972a66f71d1ee677ac57cb`, [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39011403128): 50 unit / 41 standard browser + 2 connected desktop/mobile browser / 8 backend security tests and offline safeguards. Private authenticated family account controls now provide export, current-password-verified password rotation invalidating sessions, explicit irreversible account deletion, revoke-unused-invites, transfer family ownership to an existing member, or leave/close a group. Family-linked activity is removed when consent is withdrawn, and a previously unlocked shared territory may lose progress or relock; privacy supersedes the normal permanent-unlock rule. Personal offline data remains intact. UI confirmation/disclosure and permission checks covered by CI. **Family service remains undeployed; no live public accounts or parental privacy certification.** Next: secure hosting/storage/backups, email verification and recovery, parental/guardian policy, and actual device review. AI testing still deferred.

## Family UX follow-ups — merged 2026-10-17

[PR #18](https://github.com/AndrewDionne/LearnPolish/pull/18), `946d77ffca32b6192ba12c218b1e69aed48e3373`, fixes stale team totals when a summary fetch races with server XP credit. Acknowledged contributions trigger a new authoritative summary and older HTTP responses are discarded; late-activity 2-person connected browser test passes. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39007280451).

[PR #19](https://github.com/AndrewDionne/LearnPolish/pull/19), `112c45c5657f3f7cfdbbc4bd8bff6a58a829e3e3`, ships a compact team dashboard with five weekly recognition views: earned XP, days practised, highest curriculum tier attempted, team map XP and evidence-gated Most Improved (pending, **no invented pronunciation/improvement values**). Equal results share places and inactivity produces no false winner. Create/join inputs are collapsed after entering a family. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39007780208): **50 Vitest, 41 general browser + 2 connected desktop/mobile browser**, backend private-membership tests and Python offline benchmark guards.

Synthetic screenshots from connected CI manually inspected. Team and personal map are distinct; compact management improves mobile density. The accessibility skip-link appears in one full-page captured frame (possible screenshot-focus artifact); verify on subsequent visual/physical review. **Actual family backend is still not publicly deployed; AI testing intentionally remains deferred.** Next substantive tranche should focus on deployable secure service, recovery and multi-device validation, not more synthetic/fictional social features.

## Family groups, server-owned XP and synced map — merged 2026-10-17

[**PR #17**](https://github.com/AndrewDionne/LearnPolish/pull/17), squash `468329c6c96fcc55b57f7fb3b67eb4bf897e3e0a`, [CI green](https://github.com/AndrewDionne/LearnPolish/actions/runs/39006527751): 47 unit, 41 general browser, 2 *real connected* two-learner browser journeys, 4 isolated backend authorization/security tests and benchmark guards.

**Code delivered:** standalone V2 Flask family API, isolated from legacy auth/score endpoints; private user sign-up/sign-in/out, invite/redeem with strict one-use and owner permissions, membership controls; built-in catalog validates learning item IDs and server calculates tier XP, de-duplicates per user/mode/item/UTC day, tracks a permanent collaborative open Poland map. Weekly private boards show XP effort, active days and highest independently known tier; most-improvement awaits reliable evidence. React Family panel connects when explicitly configured, opt-in new built-in activity only, individual chosen region and My Map/Family Map toggle. Real two-account desktop and mobile scenarios were run using a locally hosted API and real server persistence.

**Not deployed:** API intentionally not exposed publicly. To make cross-device accounts really work requires operator-managed persistent DB + HTTPS domain + exact production origin, database backup strategy, security review, parent/minor privacy, email verification/recovery and hosted end-to-end tests. Existing personal offline XP remains available without server and is not silently merged into groups. Client-declared completion is not cryptographically or pedagogically proof-of-work; competitions remain private/friendly. Manual inspected CI screens flag long mobile group form/board for UX reduction later. **AI testing deferred by owner.**

## New shipped UX milestone — open Poland expedition, 2026-10-16

**[PR #16](https://github.com/AndrewDionne/LearnPolish/pull/16)** merged `f7f9dfd1b6fc90abcfa28b4b70b2e8dd6900d374`. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38963206900): 45 Vitest / 39 desktop-mobile Playwright, offline Python bench harness. Live UI replaces Gold/Pierogi with XP for completed Learn/Read/Listen/usable Speak activity, higher tier rewards when explicit audited difficulty metadata exists, objectively measured authored-comprehension improvement, provider-independent verified future pronunciation evidence, and a per-mode/item/day deduplicated XP ledger. Repetition remains rewarding personally but yields diminishing map progress. Valid legacy Gold converted once without erasing prior learning history; full backup/restore supports old Gold and new expedition state. Real interactive Poland boundaries for 16 regions (source MIT attribution in code), open selection with no prerequisite/adjacency/voting, increasing/frozen-per-region targets and permanent unlocks. **Only browser-local single learner**, clearly labeled; no secure multi-member family sync or real leaderboards yet. **AI testing deferred**, no provider inference or provisional phonetic grades. Next: secure family groups/shared ledger + friendly leaderboards; mobile physical test still later.

## Priority reset — 2026-10-16

Owner instruction: **pause further lesson-content expansion**. Concentrate exclusively on (1) coherent four-mode end-to-end UX (mode entry, transitions, feedback, completion, mobile/audio lifecycle), (2) actual privacy-respecting Whisper large-v3 vs corrected Azure pronunciation evaluation, (3) revival of **rewards for work** (legacy Gold weekly target/default 500, total Gold, streaks, custom goal, later Pierogi avatar/expressions). Do not introduce arbitrary/perfect pronunciation grades, paid API calls or coin economics. PR #13 introduced the earned-Gold ledger and opt-in WAV download/paired evidence comparator, [CI green](https://github.com/AndrewDionne/LearnPolish/actions/runs/38934043274); **no actual real-model accuracy results**.

PR #14 adds same-lesson **completion → next learning mode** controls, displays session-earned Gold, restores original 4 Pierogi avatar selections + win/neutral expressions with PWA offline media caching, and preserves avatar selection in Gold backups. [CI green](https://github.com/AndrewDionne/LearnPolish/actions/runs/38935124109): 36 frontend unit and 37 Playwright desktop/mobile cases, Python offline AI guards. **No model inference or phonetic scoring has been run.**

Research gate remains blocked by missing consented private recordings/human labels, preloaded local Whisper large-v3 model or approved free-hosted access, and clean Azure `pl-PL` raw assessment result with confirmed zero-spend billing. The user need not physically test V2 for UI/content yet; collecting recordings for an explicit AI research test is a distinct opt-in task.

## 1. Product mission and non-negotiables

**Path to Polish** is an approachable, mobile-first Polish-learning app built around four integrated learning experiences: **Learn, Speak, Read, Listen**. Pronunciation is a first-class pillar. The user should be able to open the app, choose or create a lesson, hear accurate Polish, practise, get constructive feedback, and pick up where they left off.

**Quality principles**
1. One coherent app shell and design system; consistent navigation, typography, controls, and feedback across every learning mode.
2. Reliable, deterministic application state: no overlapping audio, duplicated events, silent offline-download failures, disappearing progress, or opaque binary pronunciation scoring.
3. Fast, comprehensible UX on an iPhone, with responsive tablet/desktop layouts.
4. Correct Polish orthography, natural speech, and nuanced **evidence-backed** pronunciation feedback; no invented LLM grades.
5. Learning content and user data independent of app deploys. No Git commits or code generation to create a set.
6. Free-first testing of third-party AI services; explicit hard usage caps and no automatic paid upgrades.
7. Incremental, end-to-end usable tranches validated with automated tests and synthetic browser review before physical testing.
8. GitHub issues, plan, decisions, source and tests are the durable cross-chat record; no reliance on transient conversation summaries.

## 2. Repository strategy — decision

**Reuse this repository as the permanent V2 home.** Do **not** refactor the existing `app/flashcards.py`, `app/practice.py`, `app/reading.py`, or `app/listening.py` HTML-page generators into V2.

- Start with isolated `v2/frontend/`, `v2/backend/`, `v2/content/`, `v2/tests/` (or equivalent clean separation if implementation reveals a better minimal layout).
- Integrate finished tranches into `main` using normal reviewed PRs. Avoid long-lived divergent V2 branches and avoid tiny administrative micro-PRs; ship coherent capability slices.
- Keep `docs/` as the existing GitHub Pages entry until it is intentionally switched; at handover replace its generated output with the V2 frontend build. Production host specifics may change if another arrangement is simpler.
- The existing main history at the decision point is `42f3f4e8f4669d52fd7f25a26fa0ad5579219d0d` (2025-12-08 code baseline). Git already preserves legacy source; before deleting large legacy areas, create a clearly named legacy tag or release snapshot and verify content backups.
- Do not carry the tracked `venv/`, generated mode HTML, per-set service workers or old scoring APIs into the V2 app.
- Keep existing lessons, accepted educational content and reusable audio after auditing their correctness and provenance.
- Existing auth, DB schema, deploy and storage integrations may inform requirements but must be reassessed rather than copied indiscriminately.

## 3. User experience and V2 functional scope

### A. Home / Library / navigation — must ship
- A simple, predictable main navigation: **Home, Library, Practice, Profile** (or fewer destinations if user testing supports it). Four learning modes remain prominent inside each lesson.
- Home: continue last lesson, recommended next practice, short progress overview, and access to the library. No dashboard clutter.
- Library: search/filter by topic, level and mode; readable display names; clearly distinguish built-in and personal sets; open, create, duplicate, rename, edit and delete personal sets.
- Lesson view: **Learn / Speak / Read / Listen** navigation shown when that content exists; consistent playback and progress controls; clear escape back to the library.
- Mobile-first layout, accessible keyboard/focus and touch behaviour, sensible empty/loading/error states, and a single coherent visual language in shared styles.

### B. Lesson content and authoring — must ship
- Versioned canonical JSON schemas with stable IDs for sets, items, optional mode capabilities, metadata, text, translation, pronunciation reference, audio, and progress mappings.
- Migrate and validate old lessons without cloning their generated websites. Initial source inventory: **17 vocabulary sets (437 cards), 6 reading sets (51 passages)**; reconcile these counts against actual migration output.
- Create/edit personal lesson sets **through the app**, not Git deployment. Preserve both stable set IDs and editable user-facing display names.
- Import/export a portable JSON format; duplicate and adjust downloaded/shared lessons. Basic authoring validation for Polish diacritics, missing texts, unsupported modes and duplicate IDs.
- Alphabet and pronunciation contrasts as **explicit lesson type**, not one comma-separated phrase containing unrelated examples; support Polish `ą/ę/ł/ó/ś/ć/ń/ż/ź`, `sz/ś`, `cz/ć`, `ż/ź`, `c/cz`, digraphs, stress and minimal pairs.
- Content QA: native-Polish verification of sound references, meaning, phonetics and audio; do not treat English respellings as ground truth.

### C. Learn — must ship
- Reusable flashcards with prompt, reveal, native playback, meaningful repeat/next/previous controls and self-assessed recall.
- Separate **recall/recognition** from **pronunciation quality** in data and UI.
- No arbitrary perfect-score counters or required coin mechanics.
- Simple review scheduling, introduced after robust item state and history are in place.

### D. Speak / pronunciation — **core priority**
- Single, platform-correct audio capture path on iOS Safari, Android and desktop, with recording permission handling, silence/clipping checks, format negotiation and graceful retry.
- Phase-one benchmark: **Whisper large-v3** (local and/or Groq free API) against **repaired Azure Polish pronunciation assessment**, processing identical audio bytes. Use old Azure only as a baseline, not its old penalties.
- Keep speech recognition, phonetic assessment, and optional LLM coaching as **separate provider-agnostic components**. A transcript match does not prove correct pronunciation; a misrecognition does not mean a learner spoke poorly.
- Phoneme/word-specific diagnostics and helpful articulatory feedback only if justified by benchmark evidence. Support intelligible-but-improvable speech. Mark low-confidence and bad captures **inconclusive**.
- Store evaluation provenance (provider/model/version), feedback evidence and per-sound practice needs without storing recordings indefinitely by default.
- Confirm actual free quotas and API access before tests, with an explicit no-spend default, usage counters and automatic fallback/stop.

### E. Read — must ship
- Short graded Polish passages with clear English translation, readable typography, playback and controlled navigation.
- Accurate word/sentence highlighting only when timestamps are available; otherwise no misleading faux-synchronization.
- Select a word/phrase for meaning and audio where source data permits; reading position/progress is durable.

### F. Listen — must ship
- Listen-first exercises using natural Polish audio, replay, speed adjustment as needed, reveal transcript/translation and comprehension checks.
- Shared player for Learn/Read/Listen/Speak examples: one active audio stream, stop/cancel on mode switch and card change, await playback completion before auto-advance.
- Consistent audio error recovery and clear progress UI.

### G. Offline PWA — must ship
- Explicit lesson download, actual completion acknowledgement, cancel/retry, progress/error state, and visible availability status.
- A **single** service-worker/caching strategy plus IndexedDB for lesson data/state as appropriate. No per-set workers or optimistic `downloaded` markers.
- Lessons and predownloaded audio work offline. Pronunciation scoring may require the network; mark that honestly and provide listen/repeat without scoring.
- Progress edits made offline sync safely on reconnect without duplicate outcomes.

### H. Account, progress and data — must ship
- Guest/local mode first where feasible, and reliable account sign-in when cross-device sync is ready.
- Persist completed lessons, per-item attempts, recall, pronunciation feedback and next-review dates using a small explainable model.
- Privacy-first recordings and AI provider disclosures; default to minimal storage and user-controlled deletion.
- Server-side auth and authorization; no privilege assignment from a signup email match, no dual-purpose JWTs, no token in URL query strings, protect paid/token issuance endpoints, secure diagnostics, controlled CORS.
- Explicit database migrations, predictable deployments and monitoring. No password/secret/recording leakage in logs.

## 4. Technical architecture — provisional, favour simplicity
- **Frontend:** React + TypeScript + Vite, a shared component/style system, browser audio capture, offline-capable PWA.
- **Backend:** modular Python API (Flask is acceptable to preserve operational familiarity) with typed contracts and predictable error handling; PostgreSQL for account/cloud learning data if needed.
- **Content:** schema-validated versioned JSON and durable app/user storage; no server-side HTML generation per lesson.
- **Audio:** pre-existing reviewed Polish reference recordings, object storage/CDN as appropriate, plus optional TTS generation and a single client audio manager.
- **Speech/AI:** interchangeable adapters; Whisper large-v3 is the initial recognition candidate, clean Azure as comparison. No vendor hard-wiring in lesson format.
- **Tests:** frontend unit tests (Vitest), browser journeys (Playwright, including touch-sized viewports), Python API/schema tests, audio lifecycle mocks, static type/lint/CI.
- **Deployment:** simplify to one frontend build and one backend API environment (or a smaller deployment if feasible). Separate dev, test, prod environment configuration; no user operation triggers a Git push.
- Review tech choices during first foundation tranche; avoid adopting infrastructure whose complexity outweighs a single-person learning app.

## 5. Implementation roadmap and gates

### T0 — Audit, continuity, security and scaffolding
**Deliverable:** baseline inventory/backups; clean V2 app+API skeleton and CI; legacy preservation strategy; security boundary for any still-public old endpoints.
**Gate:** reproducible local build and passing smoke checks, V2 frontend can load without importing old generated page code.

### T1 — Functional learning foundation
**Deliverable:** polished mobile Home, Library, lesson navigation, canonical set schema/import, migrated core vocabulary, built-in and personal lesson management, functional Learn mode, unified audio.
**Gate:** create/rename/open/practise/close/reopen a set; no lost state, cross-mode audio overlap or per-set page generation.

### T2 — Pronunciation evaluation (parallel early work) and Speak
**Deliverable:** benchmark harness/corpus, Whisper large-v3 versus corrected Azure, baseline results, chosen deterministic grading/evidence strategy, working Speak user journey with honest uncertainty states.
**Gate:** native speakers and typical learners get defensible, reproducible outcomes; bad recording != zero; no fabricated phoneme explanation; no unapproved API spend. **See issue #1.**
**Important:** benchmark research can begin during T0/T1; do not postpone pronunciation decisions until the rest of the app is complete.

### T3 — Read, Listen and content breadth
**Deliverable:** graded passages, listening practice, unified audio controls, all validated legacy material migrated, sound-contrast lesson series.
**Gate:** full Learn/Speak/Read/Listen vertical journeys, accessible and with consistent UI.

### T4 — Offline, progress and cross-device foundations
**Deliverable:** verified lesson downloads, offline playback, progress persistence/sync, lightweight review scheduling, account security and reliability.
**Gate:** airplane-mode use/reconnect tests; no misleading offline statuses or lost/duplicated events.

### T5 — Polish, certification and release
**Deliverable:** mobile interaction refinement, performance/accessibility, synthetic screenshot audits, browser and backend regression suite, production deploy/cutover, remove unused legacy code/dependencies.
**Gate:** all primary end-to-end user journeys pass in CI and physical smoke tests; no high-severity security or audio bugs; last known good legacy snapshot exists.

### Later / only if justified by observed use
Optional AI lesson import, nuanced dialogue coach, adaptive curricula, community sharing, friends/collaboration, avatars, group competition, gold/points, elaborate gamification. **Do not allow these to delay a reliable four-mode learning experience.** Sharing portable lesson JSON is within initial scope; hosted social features are not.

## 6. Acceptance and evaluation principles

- **Functional journey** is the unit of delivery, not number of commits. Prefer larger coherent slices with proportionate tests.
- **Pronunciation:** keep intelligibility, correct intended word, segmental sounds, stress, timing and mic-quality states distinct; compare against native human ratings and exact-audio replay, not a generic model's self-reported confidence.
- **Learning:** learner can independently use each core mode, retain progress, and consistently review content.
- **Audio:** one stream at a time; stop on navigation; no idle replay; test real Safari recording and playback.
- **Offline:** downloadable assets confirmed cached; the app does not claim a completed download prematurely.
- **Stability:** account controls, API auth, migrations, and data updates covered by regression tests.
- **Cost:** use recurring free usage and local models for development where possible; quote realistic production costs only after benchmark measurements. No automatic paid consumption.
- **Observability:** report test evidence, exact branch/head, status of checkpoints, open defects and next smallest high-value tranche in GitHub.

## 7. Current delivered capabilities and remaining pre-physical-test work (2026-10-16)

**Additional merged tranches**
- [PR #12](https://github.com/AndrewDionne/LearnPolish/pull/12): 24 exact-source-authored Read/Listen comprehension questions over 6 dialogue lessons (51 turns), six-step editorial pathway, strictly validated source text and existing reference audio, question-before-translation reading, audio-first listening with concrete answers/feedback, and ungraded fallback for non-authored passages. [CI 38930896241](https://github.com/AndrewDionne/LearnPolish/actions/runs/38930896241) passed (31 unit / 29 Playwright tests). Questions and 22 audio examples require native-speaker review; pathway stages are not certified CEFR levels.
- [PR #11](https://github.com/AndrewDionne/LearnPolish/pull/11): automated baseline WCAG A/AA serious/critical checks, keyboard skip navigation, proper page focus and active-nav markers, Polish language spans, improved contrast and input focus, mobile safe-area and 320px no-overflow layout. Desktop/mobile Playwright **29 passed**, [CI 38928297690](https://github.com/AndrewDionne/LearnPolish/actions/runs/38928297690). Screenshot evidence artifact captured for each audited mode; manual visual inspection and native Safari VoiceOver remain open.
- [PR #10](https://github.com/AndrewDionne/LearnPolish/pull/10): full local learning-data backup/export and confirmed validated restore across personal lessons, recall history, review schedules, reading positions and most recent lesson. Browser-local only until account sync ships; no audio recordings, credentials, or media blobs included. [Desktop/mobile CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38925901788).
- [PR #9](https://github.com/AndrewDionne/LearnPolish/pull/9): four **individually playable** Polish Sound Lab curricula with 22 words/short utterances sourced from existing validated-by-index MP3 references. C/CZ/Ć, S/SZ/Ś, Z/Ż-RZ/Ź-ZI, L/Ł. The three old bundled alphabet sets are removed only from V2's catalog and preserved in Git. Full content/audio source mapping plus desktop/mobile browser tests passed [CI 38924538537](https://github.com/AndrewDionne/LearnPolish/actions/runs/38924538537). Human/native Polish audio review is pending; these are not minimal-pair claims.
- [PR #7](https://github.com/AndrewDionne/LearnPolish/pull/7): browser Speak capture, temporary replay, local acoustic validity checks and provider-neutral PCM16 WAV preparation. No pronunciation grade or paid AI integration. Desktop/mobile synthetic microphone CI passed.
- [PR #8](https://github.com/AndrewDionne/LearnPolish/pull/8): local deterministic spaced recall, due-only focused review queue and persistent schedule. Desktop/mobile browser CI passed.
- [PR #5](https://github.com/AndrewDionne/LearnPolish/pull/5): Read/Listen (audio-first comprehension) with saved passage position, separate mode histories, secure media path, repeatable audio playback speed. Desktop/mobile browser CI passed.
- [PR #6](https://github.com/AndrewDionne/LearnPolish/pull/6): Production PWA shell and verified lesson MP3 download/removal with cache confirmation, real browser offline disconnect+reload checks. Desktop/mobile browser CI passed.

**Still before user physical testing (PRs #3–#10 merged, V2 separate from live app)**: native-speaker content QA of the new sound contrasts, dedicated minimal pairs and isolated phoneme recordings; real labelled Polish pronunciation-engine benchmark (Whisper v3 vs clean Azure) and evidence-based scoring; richer authored graded Read/Listen; security-reviewed backend/auth and cloud-sync architecture (no need to activate social features); expert visual screenshot inspection and native accessibility audits (automated axe/320px browser checks completed in PR #11). Test physically only when core journeys are coherent. Offline is now testable in the V2 **production preview**, not dev mode. No empirical Whisper/Azure comparison yet.

## 8. Previous immediate next development action (historical checkpoint after PR #3)

The V2 frontend, migrated library, basic Learn UI and offline-only benchmark harness now exist in `main`; CI, including desktop/mobile Playwright smoke tests, passed. The old app is unmodified.

1. **Done:** Personal lesson authoring and portable JSON import/export now work with stable IDs, local browser persistence, schema and browser tests in merged PR #4; these are not cloud-synced.
2. **Next priority:** Obtain a small human-labelled Polish audio corpus and run **actual** local Whisper large-v3 inference against a clean live Azure baseline, with explicit free-tier guardrails. The harness alone is not an empirical benchmark.
3. Add modular, security-reviewed backend/API foundation; browser Speak capture is now implemented in PR #7, but real audio hardware and scoring remain untested.
4. Expand genuine Read/Listen exercises, audited Polish sound comparisons, responsive screenshot and iOS Safari review, then offline downloads and progress sync by roadmap gates.

**Change management:** Update this plan when a material product/architecture choice is made. Record benchmark evidence and acceptance results in linked issues/PRs. Keep GitHub the authoritative continuity source.


## 9. Family service pre-deployment reliability checkpoint — 2026-10-17

The private family API and learning collaboration are merged through PR #20, but
the service is **not live**. Next incremental gate is secure durable storage and
rehearsed recovery **before** choosing public hosting, accounts or email delivery.

**Backup-readiness tranche merged** ([PR #21](https://github.com/AndrewDionne/LearnPolish/pull/21), commit `78be71629fe848829d4313a3b9939fdc9a3d0759`, [four-lane CI PASS #39014248350](https://github.com/AndrewDionne/LearnPolish/actions/runs/39014248350), 17 family backend tests):
- Owner-private directory/file validation (0700/0600) and explicit path checks before SQLite startup; fail closed rather than silently accepting world-readable account data.
- SQLite online snapshot from the live store, with WAL-safe committed data, integrity/foreign-key checks, SHA-256 size manifest and no-overwrite backup names.
- Offline operator-only recovery rehearsal to an entirely new file, verified before restore.
- Tests for permissions/symlink rejection, tamper detection, WAL data, and non-overwriting restore; instructions in `v2/server/README.md`.

**Acceptance:** backend regression and all usual V2 CI lanes passed
on the exact PR head before merge. This creates a backup rehearsal tool, **not**
a production backup schedule, off-host encrypted storage, key rotation, disaster
recovery RTO/RPO guarantee or approved deployment.

**Next release blockers after this checkpoint:** persistent TLS deployment and
DB operational monitoring; authenticated email verification/recovery; consent
and parent/guardian authority for minors; documented retention/deletion and
post-restore erasure reconciliation (old snapshots could resurrect erased data);
live multi-device reconnection testing; actual iOS Safari/VoiceOver UX. AI
pronunciation evaluation and further lesson writing remain owner-deferred.


## 10. Private family account recovery checkpoint — 2026-10-17

**Capability merged** in [PR #22](https://github.com/AndrewDionne/LearnPolish/pull/22) (commit `9b5d974ebc2c8baa588ce168385a98ce42e91fe3`, [four-lane CI PASS #39017210836](https://github.com/AndrewDionne/LearnPolish/actions/runs/39017210836), 24 backend security tests): a real recovery journey for someone who
can no longer sign in to an existing family account. Secure SMTP-delivered
one-use 15-minute codes (hashed at rest), generic reset requests without
account enumeration, request limits, complete session/token invalidation,
accessible browser recovery form, and synthetic delivery/unit/browser tests.

**Acceptance:** exact-head backend/frontend/connected-browser/benchmark CI passed
before merge. Host configuration must be explicit: no SMTP means no recovery
claim or working reset endpoint; no real email messages or user data in CI.
**Do not confuse this with registration email verification**, which is still a
separate release requirement. Follow-up release gates: verified-email signup,
guardian approvals and minor account lifecycle, email-provider abuse/bounces,
encrypted off-host backup and privacy-preserving restores, persistent TLS
service, native mobile testing, incident/retention review. Pronunciation AI
and content authoring remain owner-deferred.


## 11. Verified mailbox before family membership — 2026-10-17

**Merged in [PR #23](https://github.com/AndrewDionne/LearnPolish/pull/23)** (commit `87cb214a9993e74cff49141f0878c0a023644a45`, [four-lane CI PASS #39018174378](https://github.com/AndrewDionne/LearnPolish/actions/runs/39018174378), 31 backend tests): refuse new family account registration when secure
mail delivery is unconfigured; create accounts as pending until the recipient enters
a single-use emailed code; reject sign-in and **all private family access** until
verification. Include an authenticated credential-based resend for pre-existing
unverified accounts, 30-minute bounded codes, attempts per email/network, code
invalidation and old-session revocation. CI simulates the private mailbox and
requires each of two independent browser learners to verify before joining a
group; backend checks legacy persisted users and reset/password separation.

**Acceptance MET for this code tranche:** four GitHub V2 CI lanes green on the same PR head, with browser
desktop/mobile family collaboration, new security tests and offline benchmark
safeguards. No production SMTP is provisioned, so production registration is
deliberately closed. **Mailbox verification does not establish that a learner is
an adult, or that a parent consents**; verified parent/guardian authority,
child-associated account/data rights, safe invitations, external mail
deliverability monitoring, deletion reconciliation, TLS persistent hosting,
and physical Safari tests remain separate release gates. No AI testing or
new course authoring in this tranche.


## 12. Pronunciation AI research resumed — pilot protocol (2026-10-17)

**Pilot readiness shipped:** [PR #24](https://github.com/AndrewDionne/LearnPolish/pull/24) merged (`183d759a736257dcd0600e64b03f6017f8b94e61`); [all four CI jobs PASS #39020355029](https://github.com/AndrewDionne/LearnPolish/actions/runs/39020355029), 13 offline benchmark tests. No recordings/human/model evidence yet, and no live provider calls authorized.


Priority shifted from future guardian profiles to an **adult-only, consented
pronunciation engine study**. No prior production or model accuracy is
demonstrated. Use the no-spend reproducible 12-stimulus x 2-take pilot in
[`v2/benchmarks/PILOT_PROTOCOL.md`](v2/benchmarks/PILOT_PROTOCOL.md),
existing Speak opt-in WAV export / built-in-reference manifest, and new
independent human-label templates/validation. Control native false negatives
and contrasting sound errors before selecting a pronunciation architecture.

Reconfirmed Azure `pl-PL` assessment capability versus its limited **named
phoneme** / spoken-phoneme / prosody localization (English-specific); and
Whisper large-v3 transcription versus phonetic quality. Account-level free
quotas, real adult recordings, native listener evidence, pretrained local
model or explicitly approved free Groq, and native Azure result remain
prerequisites. No API spend, audio uploads or child-voice collection initiated.
Do not reintroduce fake perfect pronunciation or lesson content changes.


## 13. Groq two-model recognition pilot — explicit free-plan gating

**Implemented and merged:** [PR #25](https://github.com/AndrewDionne/LearnPolish/pull/25), commit `e585dc77b3bbe38ec0f7c46daf6e0a848b5d3243`; [four CI lanes PASS #39021508148](https://github.com/AndrewDionne/LearnPolish/actions/runs/39021508148), 19 offline benchmark tests. Actual free-plan key verification, consented recordings, independent human ratings and first real AI result remain owner-driven next steps; no provider was called.


A local standard-library research client for Groq Whisper `whisper-large-v3`
and `whisper-large-v3-turbo` reads existing SHA-256-locked adult WAV manifests
and produces **model-specific transcripts only**. Default dry-run requires
no key or network; sending requires explicit voice-upload consent, a locally
loaded environment key, owner-confirmed account Free Plan/no paid billing,
and strict per-run API-request and billed-audio caps. Keys and WAVs cannot be
checked into Git; transcripts are saved as private, never-overwritten results
outside the repository. Backend-only mocked tests prohibit surprise uploads;
a completed free-account setup still does NOT constitute AI accuracy evidence.
See `v2/benchmarks/README.md` and issue #1 for exact operator steps and
reproducible human/Azure comparison requirements.


## 14. Licence-grounded native Polish recognition controls

**Merged in [PR #26](https://github.com/AndrewDionne/LearnPolish/pull/26)** (SHA `378926c6075548ecc4ae28c9b87b1f87cc4e5e20`, [four-lane CI PASS #39035992396](https://github.com/AndrewDionne/LearnPolish/actions/runs/39035992396), **24 offline benchmark tests**). Live Commons downloading and actual Groq transcription still await local execution by the owner; source verification was public webpage/license review, not audio inference.


Native Polish baseline now starts with **public, human-spoken, transcript-known
pronunciation words** from Wikimedia Commons, avoiding both unconsented learner
audio and unlicensed YouTube/news clips. The public control importer downloads
reviewed CC-BY recordings, uses local ffmpeg to standardize them to 16k PCM16,
and writes the **same manifest contract** used by the Groq two-model runner
with immutable checksums and preserved source authors/licences. By default
two words test `cz` and `ci`; this means 2 recordings × 2 Whisper engines
= 4 requests and at least 40 billed seconds of provider quota. No new key
for Turbo. The corpus is a native **ASR** control only, not evidence of
phoneme-level grading or learner intelligibility. Later expand to longer
open-licensed sentences (Common Voice/FLEURS) and consented learner recordings
with independent sound-error assessment. Exact no-network preparation,
full sample licences, account gating and API commands live in
`v2/benchmarks/README.md`.


## 15. Wikimedia Commons 429 field repair

**Merged:** [PR #27](https://github.com/AndrewDionne/LearnPolish/pull/27), commit `0729a34a11564e34a36fe319b3e0891af7f32083`, [four-lane CI PASS #39036723705](https://github.com/AndrewDionne/LearnPolish/actions/runs/39036723705), 28 offline benchmark tests. Local importer 429 handling and transactionality synthetically certified; actual Wikimedia source availability after rate-limit and Groq transcription results still unverified.


During Mac physical trial of the licensed native-audio pilot, HTTP 429 from
`upload.wikimedia.org` left an empty output directory which prevented a
subsequent attempt. The downloader now recognizes provider throttle, includes
a descriptive public project URL in User-Agent, surfaces `Retry-After`, does
**not** retry or bypass the limit, and stages files transactionally so failed
downloads/conversions do not leave half-populated research directories.
The `--source-dir` option imports manually downloaded original Commons Ogg
files *without network calls*, preserving existing 16k WAV conversion,
immutable checksums and CC author/licence metadata. Mock tests cover 429,
offline source validation and cleanup. Real-media retrieval and Groq testing
on the user's Mac remain the acceptance gate. See README recovery section.


## 16. AI study workspace — owner-selected repository temp

**Merged:** PR #28 (2026-10-17), commit `b4ee7d8a4719fae1b5e3771a654ae9d063ad31e0`; CI run #39037897459 all four checks passed, including 32 offline benchmark tests. Local WAV import and first Groq results remain pending owner physical execution.


Owner requested storing native Polish source media, normalized WAV controls,
manifests and model output **under the actual LearnPolish repository**, not in
a disconnected Mac home folder. Standardize on the root **`temp/` directory
ignored by Git** (NOT `assets/`, reserved for intentionally published app
resources). Update Commons importer and Groq result placement guards to
allow this specific ignored directory while rejecting tracked repo paths and
symlink escapes. Require private mode 0700 folders and 0600 result files;
`.gitignore` is not encryption and can be overridden with `git add -f`.
CLI in `v2/benchmarks/README.md` migrates the two downloaded Oggs from the
older in-repo `PathToPolish-Private-AI` into `temp/commons-originals/` and
then runs 2-word Commons conversion/Groq v3-Turbo dry-run entirely locally.
No paid API access or real pronunciation grading authorized.


## 17. FINAL owner choice: preserve existing PathToPolish-Private-AI in place

**Implemented, CI-certified and merged:** [PR #29](https://github.com/AndrewDionne/LearnPolish/pull/29), `6ba0f17d38165101ee83e24c87b4686a50c17162`; [CI #39038820449 four-lane PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/39038820449) including **34 benchmark Python tests**. Actual owner Mac import/preview remains unverified and requires no file move.


This supersedes Section 16's `repo/temp/` recommendation. The owner has repeatedly shown that the **two manually downloaded original Commons Ogg files are already in `repo/PathToPolish-Private-AI/`** and explicitly instructed that **neither the files nor the directory will move**. Git ignores the exact root directory `/PathToPolish-Private-AI/`; benchmark path checks permit it and still reject tracked `assets/`, `docs/` and symlink escapes. Converted native WAV, checksum manifest, attribution and Groq transcripts go under the existing folder's importer-created child `commons-native-01/`. Docs, tests and durable workflow must use these exact relative paths from repo root and never suggest moving originals to `temp/`, `$HOME/`, or another folder. Only consented/Free-plan-confirmed explicit Groq requests, after dry preview, may upload audio. The former root `temp/` support remains for compatibility but is NOT this user's designated research location.


## 18. Groq pilot physical 403 — read-only diagnosis and empty-output recovery

Owner's Mac completed Commons Ogg-to-WAV and verified exactly 2 SHA-locked
native controls. Two-model dry-run passed with 4 planned Groq requests
(40 minimum billed seconds) but **no inference**. First approved live run
returned **403 Forbidden**, with no transcriptions. Official Groq docs point to
org/project model permissions as a specific 403 cause; they also classify
generic 403 as permission denied. Before further uploading audio, inspect
organization and active project **Settings → Limits** for both Whisper models
and validate actual Free Plan/key project. New opt-in `--check-access`
performs only a read-only GET model list (zero audio or transcription), with
explicit warning that listing a model doesn't guarantee execution permissions.
Error hints surface only whitelisted safe Groq denial codes, never raw
server-body or API secret. Subsequent refused-first-call cleanup removes
new zero-byte JSONL output, but retains genuine partial results. Owner's
source folder is unchanged, `PathToPolish-Private-AI/`. Actual provider
permission resolution, first successful transcripts and Polish contrast
accuracy remain pending. No API calls made in CI.
