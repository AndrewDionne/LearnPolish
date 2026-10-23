# A-05 — Honest source-unit activity and Resume

**Status:** implementation candidate, final-head four-lane GitHub CI still required.

## Problem and boundaries

T01–T05 tourist modules connect existing recorded source items in Listen, Speak and Read modes, but before A-05 a learner leaving a unit had no **unit-specific** resume point. Source-level progress alone cannot determine *which* unit activity was attempted, because one original ID can appear in multiple units/modes and the ordinary Library. **No new proficiency or pronunciation score** may be fabricated from that source history.

## Learner flow

- Under each source-backed topic in Library → Your path, the original **Listen / Speak / Read** buttons always start that activity from the beginning. After opening a topic, a short **N / M tried** caption shows source items with an explicit user answer/take, by unit and mode. The caption is deliberately factual—not completion, skill mastery, readiness or a grade.
- The optional **Resume →** button returns to the saved mode and exact source item. This cursor persists across page changes/reloads and never overwrites the independent Home **Continue course** selection. All units remain open; progress is never a prerequisite.
- Only submitting Listen/Read answers (including **Needs practice**) or producing a real, locally usable Speak recording via the existing capture flow counts as an attempted unit item. The UI may still grant existing ordinary XP for existing eligible outcomes, but this record does not award additional XP and does not send anything to family services or pronunciation vendors.
- Opening a unit, hearing audio, revealing meaning without submission, skipping to the next item, or pressing Speak **Next** without a usable take do **not** count. Navigation updates only the resume cursor.
- A mode with repeated source IDs from another mode has independent attempted evidence. The resume helper prioritizes the next untried item in the current mode, then wraps through the remaining modes. Once all source items across present modes have a genuine attempt, Resume disappears. Starting a new activity remains available; **tried** is not equivalent to correctness.
- No nine-tier label, hover description, tooltip or standalone legend is introduced.

## Durable data

- A small local-only, versioned `ptp-v2-tourist-activity` record tracks only original item IDs per unit/mode and an optional `{mode,itemId}` cursor. No speech recording, accuracy, translation text, URL, graded score or time-based claims are stored.
- `tourist-activity.ts` validates the records against the checked-in T01–T05 source manifest, including allowed unit names, modes, original IDs, and duplicate/tampered/prototype fields; malformed local records fail closed.
- Full-backup **version 1 remains compatible**: newly exported backups include optional, strictly validated unit activity. Restoring older backups resets any stale current-device unit cursor rather than leaking past user activity; `restore-storage.ts` performs atomic writes and rollback together with personal lessons, progress, review dates, XP and core course cursor.
- **Clear practice and reviews** also clears tourist attempt/resume data while keeping personal lesson definitions. No changes to migration source files, 26 active lessons, 482 items, 455 source MP3 assets, 14 restricted Speak references, one Numbers 1–20 original lesson with optional 10+10 practice, current XP/family privacy/consent, speech capture or offline caching.
- Existing Listen/Read/Speak practice, review, Core and Recent course resume still use their established keys; unit-specific evidence is **never inferred retroactively** from progress history.

## Certification

- Vitest exercises true-response recording vs navigation, skipped source lines, repeated item IDs across modes, duplicates, source drift, malformed local records, all-units-tried termination, and backup strict acceptance/rejection and rollback.
- Playwright desktop/mobile checks skip→answer→leave→reload→Resume at the first untried source line; unrecorded Speak Next shows **0 / N tried** while advancing the cursor; old source progress never becomes unit evidence; Resume remains keyboard/touch usable at 320px.
- Frontend/desktop/mobile/accessibility/offline + connected-family browser + private-family backend + benchmark harness must all pass at the **final PR head** before merge.
- Real mobile Safari/microphone and native speaker/acoustic Polish pronunciation remain deferred; human content issues [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) and [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) stay open.

**Next useful sequence after certification:** native QA and genuinely complete two-way T02/T03/T04/T05 audio + source-backed T06 directions; no fabricated future 3×3 milestones, professional track, XP multipliers or false assessment grades.
