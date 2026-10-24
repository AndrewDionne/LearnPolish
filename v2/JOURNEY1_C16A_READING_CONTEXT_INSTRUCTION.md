# C-16A — Source-anchored contextual grammar instruction for 45 remaining recorded Read turns

## Authority

Journey 1 must be teachable using only this program. Lesson N can assume only earlier teaching, or material **explained inside lesson N before comprehension**. There is no fixed 80/20 allocation. A whole-original-utterance MP3 is not isolated syllable sound training and is not automatically native-certified.

## Scope delivered

The C-14 original Read introduction already exposes every full original line, meaning and MP3 before Read checks, and C-15 adds six focused draft grammar cues for `Basic_01R`. C-16A extends that source-backed teaching to **all 45 remaining lines in five original scenes**, without changing the original six:

| Source-scene context | Full original lines with new cues |
| --- | ---: |
| Grocery store | 9 |
| Clothing shop / T-shirt | 10 |
| Passenger on tram | 9 |
| Asking tram driver | 8 |
| Museum | 9 |
| **Total** | **45** |

[The 45 source-matched cue entries](content/journey1-c16-reading-context-cues-v1.json) teach first encounters with quantities (`kilogram jabłek`, `dziesięć złotych`), colours and inflected object forms, customer and formal `pan/pani` address, personal/request verb forms (`noszę`, `nosi`, `mogę`), tram stop ordinal forms (`na trzecim przystanku`), directions, ticket types, and opening hours (`do osiemnastej`). These are concise **English teaching prompts embedded alongside each original full Polish recorded sentence and exact source English**, not new test answers, invented Polish texts or fragmented audio.

[The reading introduction adapter](frontend/src/reading-introduction.ts) accepts each supplemental draft cue only on exact `lesson:id` + Polish + English equality, preserving source identities, text, MP3, XP and parent learning mode. If anything drifts, the cue is withheld for that turn; the original Read lesson stays reachable. Existing independent Library scene access, optional introduction skip, tourist-source Read, progression, profiles, rewards, offline, Speak scoring and family/private pathways are unchanged.

[Native source validation](frontend/scripts/reading-context-cues.mjs) checks all 45 cue entries against the five existing `docs/sets` passage files, indexed individual `docs/static/<lesson>/reading/<index>.mp3` recordings, exact IDs, count and draft-status boundary. Run `cd v2/frontend && npm run audit:reading-context`, or rely on `npm run test:migration` / normal `npm run check`. The exact-source/tamper tests reject Polish or English drift, missing lines, missing recordings, duplicate IDs, false approvals and unexpectedly short/long instruction. Vitest tests confirm 51/51 contextual cues in app, correct lesson matching and no cross-scene leaking. Desktop/mobile 320px E2E exercises grocery, clothing and museum teaching then unchanged graded Read comprehension. These checks certify **source identity, not linguistic correctness or real learner pronunciation**.

## Remaining C-16 blockers: NOT CERTIFIED COMPLETE

- [Issue #156](https://github.com/AndrewDionne/LearnPolish/issues/156) remains open. The **172 basic phrase items** still need true *chronological* first-teaching mapping across the guided curriculum and any whole-source Library exercise, with source-recorded in-lesson introduction before first assessment, not just 172 source catalog rows.
- The 51/51 Read contextual explanations are **editorial draft pending native Polish language review** (word forms, register, examples). Native QA and acoustic/recording provenance cannot be signed off by a machine test; the original 455 imported MP3 identities are retained but their acoustic quality is not established.
- T01–T08 tourist scenes still need explicit prerequisite tracing to the actual earlier lessons, with new replies only when original licensed/native-reviewed recordings can be obtained. These are not treated as mastered.
- 26 active original sets, 482 original rows, 455 source MP3s, 14 protected Speak references, normal complete-word Speak workflow, XP, family/privacy, offline and user learning records must remain untouched.

## Merge/release acceptance

Only merge after **four successful final-head GitHub CI lanes** (frontend migration/TS/unit/build/full desktop+mobile browser and audio/offline/a11y, family-connected browser, backend, benchmark). Never promote draft cues to native certified or request provider inference for this offline curriculum work. Physical learner microphone and language teacher signoffs are independently open.
