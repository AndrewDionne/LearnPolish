# C-11 — First short Polish sentences and grammar through real recorded utterances

**Release type:** Actual learner-facing Journey 1 instruction, using unchanged, existing Polish whole-utterance MP3s and exact English meanings. This is **not** a new synthetic voice, a compositional audio generator, a proficiency claim, a separate lesson/XP system or an independently native-certified grammar course.

## What beginners can now learn

In **Library → Your path → Start with the essentials → Build your first sentences**, expand one of five small pattern groups. Learn from four short real recorded examples with a short explanation and the relevant **Polish expression highlighted within the complete sentence**. Listen to any full original recording, see its original English gloss, and advance one at a time. After four examples, select **Check understanding**: hear an original complete Polish utterance with its Polish writing **hidden**, choose between two authentic English meanings, then see the correct English, original full Polish phrase and focus, with a chance to try the next sentence. Repeat or switch to another pattern. This is comprehension practice with no additional pronunciation or sound scores.

| Foundational pattern | Exact recorded examples (4 each) | What it teaches |
|---|---|---|
| **Poproszę** — polite requests | Poproszę wodę; Poproszę kawę; Poproszę herbatę; Poproszę menu | The repeated polite opening and different things requested |
| **Gdzie jest ...?** — where | Gdzie jest przystanek?; Gdzie jest metro?; Gdzie jest kasa?; Gdzie jest apteka? | The repeated question phrase and the place named after it |
| **Czy mogę ...?** — permission | Czy mogę zapłacić kartą?; Czy mogę zapłacić gotówką?; Czy mogę to przymierzyć?; Czy mogę kupić bilet u kierowcy? | A simple permission-question opening and changing verb phrases |
| **Nie ...** — simple negation | Nie rozumiem; Nie mam drobnych; Nie jem mięsa; Nie piję alkoholu | Negating common first-person statements |
| **One / two** — quantity and forms | Jeden bilet, proszę; Dwa bilety, proszę; Poproszę stolik dla jednej osoby; Poproszę stolik dla dwóch osób | Observe that number and noun forms change in real recorded contexts |

These explanations are limited to the **original examples**. They do not claim universal conjugation, case, or gender rules; the examples have not received an independent native-speaker editorial audit. Do **not** produce new unrecorded inflected Polish phrases by combining source fragments. English meanings are **inherited verbatim** from the original source, including alternate styles and punctuation.

## Source fidelity and progression

[The fixed C-11 source manifest](content/foundation-sentence-patterns-v1.json) references **20 unique original legacy vocabulary lesson items across six existing source sets** with exact ID, full Polish/English, source path, and the specific repeated or contrasted word to highlight. The [runtime guard](frontend/src/foundation-sentence-patterns.ts) rejects invalid manifests, duplicated item IDs and forged approval claims; each pattern is offered only when **all four** of its original lesson items, whole Polish text, English, unchanged MP3 path, original source type and unblocked reference match. If an item drifts or is missing, the group does not appear; others remain available. Mandatory migration tests confirm each source MP3 file actually exists. No extra ID, duplicate completion, XP, provider call, data upload or persisted correctness score is created.

The UI is an optional, collapsible teaching addition **between beginner vocabulary and the original 20 guided steps**, naturally extending C-05/06 words into phrases, C-09 sound recognition and C-10 the full written alphabet. It is designed to work on desktop and 320px mobile without hidden tier names, stage tooltips or verbose overlays. Standard **C-08 Speak** remains authoritative and entirely unchanged: hear original whole word/utterance → learner records complete utterance → if explicitly assessed, show **one overall score plus visually colour-coded word parts** → Try again or Next. There is no separate syllable audio.

**Preserved:** all 26 source lessons, 482 source items, 455 inherited MP3s, 14 protected Speak references, full original Numbers 1–20 and optional 1–10/11–20 practice, original T01–T08 tourist units, 40 C-05/C-06 beginner audio-backed examples, all C-09/C-10 activities, family/XP/consent/privacy, progress/backup/offline and the original 3×3 internal tier markers without exposed labels.

## Outstanding content work

Issue [#140](https://github.com/AndrewDionne/LearnPolish/issues/140) remains OPEN for native Polish editorial signoff, exact new licensed full-word recordings where missing, vocabulary expansion, stronger sentence/grammar sequencing, and calibration of the whole-word Azure + Whisper approximate colour feedback. No claim is made that the 80%-of-Journey-1 **actual study minutes** fundamentals target has been measured; 16:4 guided-step distribution remains only a planning proxy.

**Certification:** full final-head 4/4 GitHub CI gate (frontend content migration, TypeScript, unit, build, desktop/mobile audio/offline/a11y E2E; family-connected browser; backend; benchmark). Passing these synthetic tests does not equate to independent linguistic or acoustic approval or real-microphone testing.
