# C-16B — Actual guided source chronology and first-listen introduction

## Instructional authority

Source of continuity: top-level `chat ai workflow.md`, no reliance on chat history. User's goal is a **linear, self-contained Polish course**: lessons only assume concepts taught earlier, otherwise the lesson must teach them before its first assessment. No fixed first-journey 80/20 split. Do not replace the original recorded whole Polish phrase with stitched or generated word/phoneme audio. Keep original source IDs and personal learning records stable.

## Verified mechanical evidence (not a native-language certification)

The [C-16B chronological reference map](content/journey1-c16b-chronological-source-uses-v1.json) follows the ACTUAL rendered guided path, not the arbitrary order of legacy lesson filenames:

| Actual guided stage | Units | Original complete-recording uses |
|---|---:|---:|
| First words: Yes/no, Polite essentials, Greetings | 3 | 8 |
| Basic vocabulary: Street words, Transport words, Everyday replies | 3 | 17 |
| First sentence grammar: 7 ordered source-recorded pattern groups | 7 | 28 |
| First-sentence application: Food, Shopping, Locations | 3 | 15 |
| **Guided sequence** | **16** | **68** |

The 68 references reuse **55 distinct source recordings**. **48 of the original 172 basic phrase items** are present in those guided encounters; **124 of 172** are original **optional Library** rows with *no guided-first-teaching claim*. The other seven distinct guided items originate from `Road_Terminology` and are not part of the C-15 172-row seven-basic-set inventory. All first uses, repeated uses, per-unit positions and 74 distinct first-observed **written forms** are traced. Written forms are **not lemmas, morphology review or evidence of concepts learned**. Every one of the original 172 stays in its source lesson unchanged.

[The source checker](frontend/scripts/journey1-guided-chronology.mjs) verifies the 16 true unit IDs and their actual source manifests; all exact Polish/English original rows, original complete audio files, 172/172 basic ID-to-first-use status and chronological written-form first occurrences, all 15 sentence-cue text anchors, and no fake native approval. Mutation tests cover missing cues, changed text/audio refs, unit order, first-use identity and false signoff. Run `cd v2/frontend && npm run audit:guided-chronology` or the complete `npm run test:migration` pipeline.

## Learner-facing improvement before grading

A new [exact-source 40-item guided phrase introduction](frontend/src/guided-phrase-introduction.ts) reuses the established C-14/C-16A small, single-card player ahead of **Listen** assessment in each of the nine guided first-word, basic-vocabulary or sentence-practice groups. Each card shows the **exact original whole Polish item and English**, and plays its **existing full MP3**, with Next/Previous/Start listening or optional skip. For all **15** sentence-practice items (five each in Food/Shopping/Locations), [source-matched draft explanations](content/journey1-c16b-first-sentence-cues-v1.json) explicitly unpack unfamiliar constructions (`Poproszę + object form`, `Ile to ...?`, `Czy mogę ...?`, `Gdzie mogę ...?`, noun/object and price terms) before the source Listen multiple-choice grade. First words and single-word vocabulary use the full audio+English introduction without redundant paragraph explanations.

The seven recorded grammar pattern groups continue to display the original full utterance/meaning and pattern comparison before their own checks; these are represented as 28 separate guided source uses in the chronology but do not become new cards/progress keys. `RecordedReadingIntroduction` is reused with scoped wording for the guided Listen context and retains its original Read wording, behavior and 51 contextual reading cues elsewhere.

The pre-Listen introduction is source-only and available only if **all original item IDs, original Polish, English, exact full-audio refs and group order match**. It is voluntary for people reviewing a familiar set, not a proficiency gate; no new XP, modified assessment engine, guesswork about sound fragments or permanent unlocked-state assumptions. The uncurated original Library remains an independently browsable/explorable archive, **not a certified sequential course**. Existing offline, family, personal data, XP, 14 protected Speak refs and original 26/482/455 source inventories remain untouched.

## Unfinished gaps (C-16C / issue #156)

1. The **124 original basic Library-only rows** need source-anchored *in-lesson* instruction before first unfamiliar Listen/Speak assessment if treated as a beginner path, and individual lexical/morphological native review. Independently exploring a Library lesson out of order is not proof of prior instruction.
2. The 48 guided basic rows and seven Road terminology refs currently have original-recording/English and an instructional position, but a native Polish teacher still must review inflections, register, meanings and where finer introductory grammar is required. The 15 grammar cues are **draft**, not native certified; 74 written forms are only orthographic tokens.
3. The source-only eight tourist units T01–T08 require the same actual-step prerequisite tracking, including full replies and recording rights. No invented natural responses.
4. The course cannot claim end-to-end complete Journey 1, native content signoff or physical calibrated Speak audio. [Issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140) remains open for native/acoustic and provider-inference verification.

## Integration rule

Only merge after all FOUR exact final-head CI lanes pass: frontend source/TS/unit/build plus desktop/mobile/320px/browser/audio/offline/accessibility, connected-family browser, private backend and benchmark. Record exact SHA/CI/merge in `chat ai workflow.md`, keep C-16 open.
