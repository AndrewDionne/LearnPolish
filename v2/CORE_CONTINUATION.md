# A-02 — Independent Home course continuation and recent practice

**Status:** implementation, separate from A-01/B-01 silent 3×3 source map. This document records the exact owner-requested safety distinction: **custom/optional practice must not move the core course cursor**.

## Behaviour and truth

- Home’s primary **Continue course** action follows the selected **built-in, mapped** lesson within the 20-source initial `core-journey-v1` pilot, never the most recently opened personal/imported lesson or optional geography/diagnostic.
- Core **course cursor** has its own browser-local key, `ptp-v2-core-continue`. Only opening a vetted, mapped built-in (via Library, Next or Home) updates it. Opening personal sets, diagnostic, standalone sound subpractice, optional topic sets or due-review sessions within personal sets does **not** update it.
- Home optionally shows a second, visually quiet **Recent practice** card when its last visited lesson differs from the core course location. The existing `ptp-v2-last-lesson` key and restore/delete semantics continue to track most recent activity independently.
- Brand-new learner: Home still offers `Explore lessons` and an initial mapped course card, starting with real Greetings. No degree of skill, proficiency, course completion, score threshold or teacher decision is inferred from being on a card.
- `nextLessonResume` still handles the first unvisited Learn expression, the single Numbers 1–20 source lesson with approved 1–10/11–20 batch split, and reading page cursor. Home continuation always passes the existing resume flag; explicitly clicking Library lesson cards remains a deliberate fresh session.
- An older installation without a core cursor migrates at render: use valid last visited mapped built-in first, else most recently **actually encountered** mapped source item from old Learn/Listen/Read timestamps, else first existing course lesson. Personal and optional items are excluded from this inference, as are XP and experimental Speak pronunciation scores. No eager overwrite of old data or imported file is required.

## Local backup and recovery

- The existing local JSON **version 1** backup format retains its identity, with an **optional** `lastCoreLessonId` field. Existing backups without it parse unchanged. Exporting a genuinely unstarted course records `null`, not a fabricated course achievement.
- `parseBackup` rejects malformed, personal or diagnostic core IDs. If a source ID disappears from a future catalogue, the run-time resolver simply ignores it and follows genuine available core history/first lesson; source IDs are not invented or silently remapped.
- `persistRestoredBackup` atomically writes the optional core key as its last storage operation and rolls back **all** touched keys on failure. Restoring older backups explicitly removes any stale core cursor from the current browser, then derives a safe continuation only from the imported records.
- Existing personal lessons, review schedule, reading positions, XP ledger, consent and provider keys are untouched.

## Tests and explicit boundaries

- `src/core-continuation.test.ts`: mapped-only cursor, custom and optional isolation, migration from older timestamps, missing catalogue, malformed storage IDs.
- `src/backup.test.ts` and `src/restore-storage.test.ts`: optional v1 backup field, legacy exports, invalid values, atomic cursor write and final-key rollback.
- `e2e/core-continuation.spec.ts`: creation of a real personal lesson after practising core, Home dual cards, persisted reload, independent recent practice, optional country vocabulary, 320px accessibility, and old-progress migration.
- Existing `e2e/learning-resume.spec.ts` retains exact audio, first new item and Numbers section assumptions while using the new primary `Continue course` label.
- CI gate: typecheck, Vitest/build/offline, desktop/mobile/axe, connected family/private mock Speak, secure backend, benchmark **all pass at final head** before merge.
- This **does not** build the entire tourist/extended/resident conversational curriculum or claim true skill mastery. No changes to core 3×3 decorative marks/tier visibility, original lesson order/IDs, 455 MP3s, 14 protected Speak cases, provider calls, native audio review, physical Safari tests or deployment.

## Follow-on development

**A-03/B-02:** author coherent T01–T03 real-life course unit references and activity handoffs, with independently verified Polish transcript and source audio gates before new dialogue creation. Keep personal content a separate optional lane, not a prerequisite or course milestone.
