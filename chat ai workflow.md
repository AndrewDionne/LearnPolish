# Path to Polish — Chat AI Workflow / Durable Continuity

**Updated:** 2026-10-16 — first V2 implementation merged

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
- **Next capability:** execute **actual labelled-corpus Whisper large-v3 vs clean Azure assessment**, build proper speech capture and human-grade scoring comparison (issue #1); develop vetted Polish sound-comparison lessons, responsive synthetic screenshot review and secure backend/API foundation before user sync. See issue #2 for checkpoint notes.
- Do not claim physical Safari certification or full design screenshot review; V2 is not deployed as the old site's replacement.
