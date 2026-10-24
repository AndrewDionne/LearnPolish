# C-08 — Authoritative pronunciation interaction contract

**Owner decision (2026-10-24):** No syllable-level audio for ordinary word practice. Supersedes C-07's speculative plan to independently align 40 source recordings into individual playable syllable clips. Do not restart that work. Keep source audio whole-word/whole-utterance.

## Standard word pronunciation

**Recorded full word → Learner records full word → [explicitly requested pronunciation assessment] → One overall score with colour-coded syllable/text groups → Try again or Next.**

The learner hears a **single exact original whole-word recording** at the existing 0.75×/0.85×/1× controls. The microphone recording is held locally and the learner chooses whether to send a particular take for scoring; there is no automatic provider upload or audio retention. In the enabled **Azure + Whisper blend**, show **only the averaged overall score** and the **Whisper-transcript-proxy colour guidance embedded in the Polish word** with small spaces between its text groups. Do not show a numeric grade for every syllable, separate colour boxes, unnecessary descriptions, extra score breakdowns, raw Whisper transcript, or an 84/50 component breakdown. The whole-score blend remains an experimental uncalibrated estimate, and the colours are a **transcription-derived visual hint**, not independently verified acoustic syllable measurements. If a response lacks exact original word and group alignment, show no misleading colours; if scoring is unavailable or inconclusive, do **not** fabricate a 0 or a grade. Azure-only assessment does not supply the Whisper colour hints; show its overall estimate only until both providers are legitimately available/consented.

A successfully scored take presents **Try again** and **Next**. Try again resets that take's feedback and invokes the existing microphone flow; Next completes/moves on. Repeated user clicks must not consume duplicate provider allowances. Learners may still practise without scoring, and source-specific `practice_only` items never silently become scored references. The existing English pronunciation cue/guide is **optional** (off at start); no new per-syllable playback is linked from it.

## Explicit sound introduction only

For a sound lesson, the teaching presentation should read **“<sound>, like in <word>”** with that grapheme highlighted *inside the existing real recorded example word*. Play that **whole** source example word, not synthetic isolated phoneme/syllable TTS. The Sound Lab now says **“Hear sounds in real words”** instead of misleadingly promising to hear every sound separately. IPA and authored grapheme contrasts can remain. An independently reviewed sound-only demonstration can be considered **only if** a real sound lesson needs it, not as a prerequisite for words or Journey 1.

## Scope and deliberate C-07 removal

- Remove `ReviewedSyllableAudio` and the `syllableAudio` lesson data/schema; imported data explicitly rejects this obsolete field.
- Remove WebAudio `playExcerpt`, `onPlayExcerpt`, timing/rights/ffprobe extra processing, and the blocked audio release manifest/validator/tests. No extra audio assets were published by C-07; no recordings are deleted.
- Preserve the **visual-only** optional editorial spelling groups in normal Learn and Speak. Automatically guessed splits remain excluded from the teaching guide; the transcript proxy may still colour groups after an exactly aligned blended assessment.
- Preserve all 26 original lesson sets, 482 source items, 455 original MP3 imports, 14 protected Speak reference blockers, C-05/06's **40 exact source-backed beginner focus items**, full Numbers 1–20 and optional 10+10 practice, 8 tourist units, family/XP/consent, backup/offline, and internal journey tiers without labels.

**Open content dependencies:** native Polish/editorial review of **new** alphabet/sound contrast examples and F0/F1 vocabulary, authentic full-word recordings where missing, and empirical calibration of the two-provider whole-score/colour experience. Tracked under [issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140). A syllable-only recording project is **not** an outstanding deliverable.

## Test authority

Production migration/TypeScript/Vitest/desktop + mobile Playwright/connected-family/backend/benchmark must pass at the exact PR head before merge. No physical microphone, paid provider inference or human acoustic calibration is asserted from synthetic browser tests. The user can review behaviour with their device after the merged sync.
