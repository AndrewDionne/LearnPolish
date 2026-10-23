# C-05 — First *usable* Journey 1 beginner practice with inherited source recordings

This tranche deliberately **moves beyond author packets**. It publishes actual beginner access to **eight existing, recorded, unmodified whole expressions** inside the current Learn / Listen / Speak lesson engine. It does **not** publish C-02/C-03/C-04 unreviewed letter-name, phoneme, isolated syllable or new-vocabulary candidates. All 8 recordings are inherited originals, not new independent native acoustic verification.

## What a beginner can do now

Open **Library → Your path → Start with the essentials → Practice eight everyday expressions**. Choose any small group:

| Group | Full Polish source phrases | Original source IDs |
| --- | --- | --- |
| Hello and goodbye (3) | Dzień dobry · Cześć · Do widzenia | `Conversation_1:0`, `:2`, `:4` |
| Polite essentials (3) | Proszę · Dziękuję · Przepraszam | `Conversation_1:10`, `:8`, `:12` |
| Yes and no (2) | Tak · Nie | `Conversation_1:14`, `:15` |

The three buttons open genuine mini-sessions, not extra library courses. Learners can reveal meanings, listen to the **original full utterances** at the established 0.75/0.85/1.0 playback speeds, complete standard comprehension/recall interactions and access the existing Speak workflow. A Speak exercise is **not** a claim that this reference has been separately native/acoustically certified; existing feedback-provider policy and 14 protected unrelated source prompts remain in force.

The **full original greetings lesson** remains one tap away through the F01 guide step or its original Library tile. No new item IDs, MP3s, speech measurements, duplicate completion credits, double counting or changed course position; existing XP, review scheduling, backup, family consent/share and offline caching remain source keyed.

## Source integrity / regression gates

`v2/content/foundation-first-expressions-v1.json` specifies only original lesson ID, exact item IDs and full Polish text, with an explicit status distinguishing inherited recordings from independent native certification. `v2/frontend/src/foundation-first-expressions.ts` validates the exact canonical eight strings, three group boundaries, original source kind and original per-item MP3 URL before any starter action is shown. If a recording, text, source type or protected reference changes, **that group disappears**, not substituted with another prompt. Validation references neither C-02 editorial candidates nor C-04 blocked release intake at runtime.

`v2/frontend/src/foundation-first-expressions.test.ts` covers all 8 original word/audio links in 3 learn/listen/speak routes, source mutation, missing audio, moved IDs, blocked Speak refs, fictitious editor approval and empty/different lessons. `v2/frontend/e2e/foundation-first-expressions.spec.ts` verifies actual guided-session launch, mode switching, 3/3/2 counts, mobile/desktop navigation, original full lesson restoration and all 26 original tiles. Existing 20-step C-01 guide remains 16 foundation + 4 application **entry slots**, not 80% measured instructional time; guide lessons themselves remain full originals.

**No new alphabet names, phoneme recordings or 42 new candidate words** are published by this tranche. The 8 expressions existed already; the improvement is usable beginner grouping/reuse of *actual source audio*, not eight newly authored/acoustically approved words. Full native/audio certification and genuine new F0/F1 material stay on [open issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140).

## Next learner-content tranche

Once independent Polish/English review and licensed decodable recordings exist, integrate a **small actual new** F0 pronunciation and first-word batch through the C-04 source/compiler pipeline. Do **not** claim C-05 is a full alphabet course or 80% of teaching time; do not do more empty scaffolding. Re-audit 80% instructional minutes once realistic F0/F1/F2 lessons and repeat practice exist. Preserve genuine Numbers 1–20 as one full lesson with optional 1–10 / 11–20.

**Merge gate:** four final-head GitHub Actions lanes must pass (including frontend browser desktop/mobile/offline/a11y, family connected browser, backend and benchmark). CI does not provide human Polish/voice approval.
