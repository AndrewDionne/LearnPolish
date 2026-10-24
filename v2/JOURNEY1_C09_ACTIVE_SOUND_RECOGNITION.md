# C-09 — Active Polish sound recognition with recorded complete words

**Status:** Learner-facing source-audio instructional improvement. This tranche teaches learners to recognise sounds **inside recorded complete Polish words and phrases**, not isolated syllables, standalone generated phonemes, or new word recordings.

## Progression

All five existing Journey 1 sound-contrast lessons retain the familiar **“<sound>, like in <recorded word>”** comparison cards. The new unobtrusive **Compare words / Test my ear** choice lets a learner do actual listening retrieval practice:

1. Tap **Test my ear**. The comparison words are hidden during the question.
2. Hear **one complete existing Polish word/phrase recording** (repeat freely, with established audio rate).
3. Choose one of the lesson's **two or three contrasting sound families**.
4. See the correct sound family and **the full Polish word with its source-authored grapheme highlighted**. A wrong answer gives corrective feedback, not a zero score or punishment.
5. Tap **Next word**, then **Practise again** or **Compare sounds**. Nothing is submitted to a speech provider.

This is ungraded recognition practice. It does **not** create a new audio item, standalone speech-sound recording, individual-syllable playback, new XP stream, stored quiz score, microphone upload, or a proficiency/phonetic certification claim. Standard whole-word Speak still follows **full-word audio → learner recording → single overall score + syllable-coloured word text → Try again/Next**, exactly as locked in [C-08](JOURNEY1_C08_PRONUNCIATION_WORKFLOW.md).

## Actual sound-question inventory

[Source-only curation file](content/sound-listening-v1.json) contains **25 exact original recorded items**, drawn directly from the five existing source-verified sound-contrast lessons:

| Existing lesson | Recognition examples |
| --- | ---: |
| C / CZ / Ć | 6 |
| S / SZ / Ś | 5 |
| Z / Ż–RZ / Ź–ZI | 6 |
| L / Ł | 4 |
| KRZY / PRZY | 4 |
| **Total** | **25** |

The prompts alternate sound families within each lesson, rather than repeating six answers from one class. `Sześć` remains a recorded source example in the original comparison lesson but is intentionally **not used as a blind SZ-family listening question** because it includes a separate soft fricative that could make that particular multiple-choice check misleading.

**Independent Polish-native/acoustic certification remains pending.** The quiz is a source-grounded training activity, not a proven calibrated sound discrimination assessment. IPA and exact source sound contrasts retain their prior editorial review status.

[Runtime source guard](frontend/src/sound-listening.ts) checks stable sound-item ID, Polish source wording, focus substring, exact sound group, existing original trusted full-word MP3, and protected reference status for **every question in a lesson**. If any target drifts, that lesson's optional ear exercise is withheld instead of substituting another recording or returning an incorrect answer; original comparison remains available.

The quiz is self-contained within each existing sound lesson ([React UI](frontend/src/SoundEarQuiz.tsx)); [unit tests](frontend/src/sound-listening.test.ts) validate all five sound groups and 25 exact source rows, mutation failures, no duplicate IDs, and the ambiguity omission. Migration tests confirm each MP3 **exists** in the current original recorded corpus. Desktop/mobile end-to-end browser journeys cover hidden-answer playback, deliberately wrong and correct choices, highlighting, completion, retry, return to comparison, library preservation, and 320px layout.

## What remains for Journey 1

Only five sound-contrast lessons are presently taught using recorded source words; the **full Polish alphabet and remaining letter combinations are not yet adequately covered**. C-09 deepens actual instruction for the available sounds and fits the 80%-fundamentals goal, but does NOT establish that 80% of actual learner instructional time has been achieved. We must next expand source-authentic alphabet/sounds and first vocabulary using **independently reviewed Polish and complete recorded example words**, integrate short meaningful sentences, and assess real minute allocations.

Preserve existing 26 lessons / 482 original source items / 455 original MP3 copies, 14 protected Speak reference items, 40 C-05/C-06 source-backed beginner focuses, complete Numbers 1–20 with optional 10+10, original tourist T01–T08, and family/consent/XP/offline/backup. No visible 3×3 journey-tier labels. C-07's unnecessary individual-syllable audio plan remains superseded by C-08.

**Certification:** Require all **four exact-final-head GitHub CI lanes** PASS: migration/source integrity/type/unit/build and desktop/mobile/offline/audio/accessibility browser; family-connected browser; private backend; benchmark. Browser tests use original MP3 asset availability, not independent native-listener or microphone assessments.
