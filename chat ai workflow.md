# Path to Polish — Chat AI Workflow / Durable Continuity

**Updated:** 2026-10-16 — sound lab, Speak, review, offline and core V2 journeys merged

## Read first in every new development session
1. [V2_REBUILD_PLAN.md](V2_REBUILD_PLAN.md) — authoritative product scope, architecture direction, priorities, delivery tranches, acceptance criteria.
2. [Issue #2 — V2 rebuild umbrella](https://github.com/AndrewDionne/LearnPolish/issues/2) — execution checklist and checkpoint statuses.
3. [Issue #1 — Polish pronunciation benchmark](https://github.com/AndrewDionne/LearnPolish/issues/1) — tests and free-first provider policies.
4. Latest V2 PRs, commits and CI evidence before choosing a next task.

## Owner's approved decisions
- **Keep the `AndrewDionne/LearnPolish` repository.** Rebuild clean V2 inside it, then replace the unused legacy app. Do not create a new repository unless later evidence justifies it.
- Prioritize an actually functioning **Learn, Speak, Read, Listen** application, not incremental patches to old generated pages.
- **Pronunciation is a core feature**, not just word recognition. **Test Whisper large-v3 first** against a clean Azure `pl-PL` pronunciation baseline, on identical recorded audio. Grade pronunciation only from sound-level evidence; do not infer it from transcription alone.
- Prefer **recurring free AI API allowances / local open-source execution** during research. Verify quotas in the real account. Never incur paid API usage or auto-top-ups without explicit approval.
- User lessons are user data; **never generate entire HTML pages and Git commit/push** to create a learning set.
- Use coherent, larger-but-reviewable, end-to-end capability tranches; proportionate automated tests, synthetic browser/screenshot UX review before physical testing, and merge eligible verified work into `main`.
- GitHub is the durable source of continuity across chats. Update this file, the plan, and issues/PRs when a material decision changes.

## Continuation procedure
1. Fetch current GitHub status; do not infer implementation completion from old chat.
2. Check umbrella issue and code. Choose the next unfinished acceptance checkpoint, identifying dependencies and relevant tests.
3. Develop in a branch; execute available checks, report what is tested vs unverified.
4. Merge only when acceptance evidence and repository policy permit; keep issues/checklist and this workflow current.
5. In the user summary, state actual files/PRs/commit changes and next step, without claiming unrun tests or unbuilt features.

## Current state — verified 2026-10-16
- **PR #3 merged to main:** `c89010c4fd6c603f885c996d51231f8148037fea`. New `v2/frontend` React/TypeScript/Vite foundation provides Home, Library, basic Learn/Read/Sounds, locally saved recall, unified audio and full 23-set content migration.
- New `v2/benchmarks` offline-only Python harness supports dry checks, pre-downloaded Whisper large-v3 and raw Azure score parsing. **No actual Whisper/Azure comparative inference run yet.**
- **CI PASS** on exact PR head `b46b8f1b20ca161fc50d0f557f504b783ba503bc`, including Playwright desktop/mobile smoke journeys: https://github.com/AndrewDionne/LearnPolish/actions/runs/38819091257
- **PR #4 merged into main:** `5bd2649013aa565f86c2c93bcbc036d73c5381a9`. V2 supports create/edit/delete personal lessons plus portable JSON import/export; browser-local only, audio URLs stripped from imports.
- **PR #4 checks PASS:** https://github.com/AndrewDionne/LearnPolish/actions/runs/38819800786 (schema/ID tests, Playwright desktop/mobile authoring workflows).
- **Roadmap status:** T0 foundational frontend **partial**; T1 usable Library→Learn + personal authoring **partial**; T2 benchmark harness only; all larger tranche release gates remain open.
- Original source baseline before V2 plan: `42f3f4e8f4669d52fd7f25a26fa0ad5579219d0d`.
- **PR #5 merged:** `bc8b08fe3d189427eb7b8c532bc8746850be8ede`. Read and audio-first Listen are functional with reading-position persistence, transcript reveal, deterministic comprehension choices, mode-qualified progress and controlled variable-rate audio. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38868650767).
- **PR #6 merged:** `d5ccb1e29e7888d29965e25a9c6aa019e8f23519`. Production V2 PWA has a single versioned service worker, verified explicit offline audio downloads, cache status/removal/retry, and app-shell offline reload. Actual desktop/mobile browser offline test [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38869863571).
- **Roadmap status now:** T0 frontend foundation **partial** (backend/auth still absent); T1 library/learn/personal sets substantially implemented but content QA remains; T2 pronunciation harness only (no actual Whisper/Azure comparison); T3 Read/Listen core **implemented** but graded content/word alignment pending; T4 verified local PWA offline **implemented** but no cloud sync; T5 release readiness pending.
- **PR #7 merged:** `62c034678acb3bb5821ed0be9a8919a70dbac7c6`. Browser microphone permission/capture, ephemeral take replay, WAV PCM16 16 kHz conversion, silence/clipping/short-take checks, provider-agnostic input contract; **no AI grading, no recording upload**. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38871639776) incl. synthetic mic/permission desktop/mobile.
- **PR #8 merged:** `1358aae54c3b75151589372b4505bba245cbedf0`. Self-rated Learn recall creates transparent spaced schedules; Practice lists due cards per lesson and launches focused due-only reviews; saves schedule locally. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38872458280) incl. reload/e2e.
- **Current checkpoint:** all four mode shells exist (Learn, Speak *ungraded*, Read, Listen). User lesson editor/import/export, local progress and spaced review, and opt-in offline packs operate in the standalone V2 preview. No accounts/cloud sync or scored pronunciation yet. **Physical iPhone Safari, real mic hardware/audio, content/audio native review and full visual screenshot audits are NOT certified.**
- **PR #9 merged:** `83c882a8dad16a8b79b269e0cd3ef8a32e3fb8ba`. Sound Lab compares C/CZ/Ć, S/SZ/Ś, Z/Ż-RZ/Ź-ZI and L/Ł in four curated V2 lessons using **22 individually playable reference recordings**, linked to exact existing source text/card/audio. The three original letter-recognition grouped-audio sets are retired from V2's catalog but preserved as legacy files in Git. Sound metadata/IPA and selected audio are **not native-speaker reviewed yet**. The content build fails on source index/text/audio mismatch. [CI PASS](https://github.com/AndrewDionne/LearnPolish/actions/runs/38924538537) including desktop/mobile Sound Lab browser tests; strict validation caught and blocked an incorrect "Legnica" source index before merge.
- **Current content counts:** 24 V2 lessons (14 legacy vocabulary + 6 reading + 4 curated sounds), 477 total learning items; 455 copied legacy source MP3s and 22 references to these sources in curated sound lessons. Sound contrasts are NOT certified minimal pairs, and genuine isolated phoneme audio is a later content production task.
- **Next rebuild before user's physical testing:** UX and accessibility audit of all V2 modes at mobile sizes, content/copy quality and Read/Listen exercise quality; reliable user data backup/export and backend/auth architecture if needed. Test real consented recordings with Whisper large-v3 vs corrected Azure under free-tier controls before any automatic pronunciation grades.
- **Speech models:** Whisper large-v3 remains first recognition candidate, repaired native Azure baseline for comparison; free-first and no unapproved paid usage. No actual comparative benchmark has been executed.

- Do not claim physical Safari certification or full design screenshot review; V2 is not deployed as the old site's replacement.
