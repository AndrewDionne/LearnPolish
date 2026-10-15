# Path to Polish — Chat AI Workflow / Durable Continuity

**Updated:** 2026-10-16

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

## Current state
- **Scope and benchmark are documented; V2 code has not yet been implemented.**
- Original source baseline before plan changes: `42f3f4e8f4669d52fd7f25a26fa0ad5579219d0d`.
- Next product increment: bootstrap V2 app/test architecture + end-to-end Library-to-Learn; concurrently implement an audio-replay harness for Whisper large-v3 and corrected Azure results.
