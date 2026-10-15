# Path to Polish V2 — Rebuild Scope and Delivery Plan

**Status:** V2 development active (2026-10-16). Initial foundation/Library→Learn capability merged in [PR #3](https://github.com/AndrewDionne/LearnPolish/pull/3), commit `c89010c4fd6c603f885c996d51231f8148037fea`. T0/T1 gates remain partial; see [umbrella issue #2](https://github.com/AndrewDionne/LearnPolish/issues/2) for checkpoints and CI evidence.
**Repository:** `AndrewDionne/LearnPolish` (retain; do not create a second repository).
**Owner's product decision:** The current application is unused and may be replaced without preserving its existing runtime behaviour or uptime. Preserve useful learning content and historical source, **not** legacy design or architecture.
**Related pronunciation decision:** [Issue #1](https://github.com/AndrewDionne/LearnPolish/issues/1).

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

## 7. Immediate next development action (after merged PR #3)

The V2 frontend, migrated library, basic Learn UI and offline-only benchmark harness now exist in `main`; CI, including desktop/mobile Playwright smoke tests, passed. The old app is unmodified.

1. Add **editable personal lesson sets** and portable JSON import/export, with stable IDs, local persistence, schema validation and browser tests; no Git commits for user-created sets.
2. Add a modular backend foundation and security/auth boundary only as product needs require, without inheriting unsafe legacy endpoints.
3. Obtain a small human-labelled Polish audio corpus and run **actual** local Whisper large-v3 inference against a clean live Azure baseline, with explicit free-tier guardrails. The harness alone is not an empirical benchmark.
4. Expand real Read/Listen capabilities and design/synthetic/physical audits, then offline support and progress sync by roadmap gates.

**Change management:** Update this plan when a material product/architecture choice is made. Record benchmark evidence and acceptance results in linked issues/PRs. Keep GitHub the authoritative continuity source.
