# C-14 — Whole Journey 1 source inventory and source-recorded dialogue teaching

## Curriculum rule

A lesson may **assume** only previously taught/reviewed material, or introduce any new language **inside the current lesson** with its full meaning and authentic matching recording before assessing comprehension. **There is no 80/20 target.** Retain the optional source Library and allow free exploration, but do not equate a source directory or mechanical next-button with an independently complete language course.

## Audited inventory — all original source groups, not a false full language signoff

[Full machine-verifiable source-level gap inventory](content/journey1-full-source-gap-audit-v1.json) tracks **26 active lessons totaling 482 V2 items and all 8 actual tourist units T01–T08**, with a specific known educational risk and actionable gap fill for EVERY source. Nothing is presented as Polish-native or acoustically certified. The inventory breaks down as follows:

| Original material | Lessons | V2 items | First-pass disposition |
| --- | ---: | ---: | --- |
| Source-derived sound-contrast groups | 5 | 26 | Recorded whole-word examples; phonetic/letter-context review still open |
| Fundamental word, number, geography and name sets | 7 | 232 | Numbers and relevant core words usable; full large inventories optional, not beginner prerequisites |
| Complete legacy basic phrase / question sets | 7 | 172 | Only mapped original excerpts have curated prerequisite introductions; full 172 items still need word/grammar checks |
| Complete original reading conversations | 6 | 51 | **C-14 adds complete source-audio+English teaching pass** before ordinary Read checks; grammatical structures still require native review |
| Standalone unverified pronunciation lab | 1 | 1 | Not treated as normal course audio or beginner proficiency |
| **Total active original learning material** | **26** | **482** | **All 26 accounted for; no source-level false review approvals** |

Every one of **T01–T08** is accounted for in the same inventory. They reuse original source recordings; gaps remain in first-person name answers, complete prices/payment exchanges, waiter replies, grocery-price follow-up, walking directions, platform/timetable/transfer information, and time/museum exhibition language. Some are deliberately editorial/rights blockers, **not** permission to invent dialogue, unreviewed audio or current ticket-service policies.

### Highest-priority verified gaps

1. **Read lessons assumed comprehension before instruction.** Six original reading modules contain **51 real whole recorded Polish utterances**, including grammar not previously taught in the 16-unit guided beginner graph (e.g. *Jakie jabłka pan lubi? Czerwone czy zielone?*, *Na którym przystanku powinienem wysiąść?*, and museum hours/price forms). Their source English meanings exist but were revealed during/after Read testing. **C-14 fixes the missing preparatory exposure** for all 51 original lines, without inventing translations or audio.
2. **Original full 172 basic phrase items are not the same as the first 40 focused references.** The guided 16-unit graph teaches explicit Poproszę, Gdzie mogę, Ile, Czy to, negation and one/two concepts, but it does **not** certify every original full-set item. Continue tracing remaining source lines individually and construct reviewed in-app bridges with original matched MP3s.
3. **Numbers above 20 and full noun/name/place inventories are not logically required to pass early lessons.** A 36-item numbers lesson reaches beyond 100; 68 country names and 32 people names are useful optional assets, not prerequisite foundations. Their full source lists remain untouched and selectable.
4. **Tourist source scenarios are not globally prerequisite-certified.** Their eight source-unit metadata files already acknowledge missing dialogue and natural replies. Merely offering Listen/Speak/Read in a card does not establish that the preceding curriculum taught every utterance.
5. **Acoustic and semantic quality requires human review.** Original audio-file presence, exact text, and software tests cannot certify a native voice, correct phonetic teaching, Polish declension, realistic conversation or authorized new recordings.

## Actual new learner-facing instruction

For all six original recorded reading lessons—Everyday Conversations: Greetings; At the Grocery Store; Buying Clothes: A T-Shirt; On the Tram: A Conversation; Asking a Tram Driver; At the Museum—opening their ordinary **Read** lesson at the first turn now offers **Learn this conversation first**. It initially opens to the first **entire original Polish utterance, its unchanged English meaning, and an original recorded full-utterance playback control**. Learners may advance through **every** source dialogue turn, repeat/step back, or choose **Read conversation now**. After the final line, **Start reading** closes the introduction and leaves the existing reading comprehension workflow unchanged.

There are **6 + 9 + 10 + 9 + 8 + 9 = 51** separately traced **original audio recordings**, not isolated phonemes or manufactured phrase concatenations. Source item IDs and recorded English text are unchanged; no new lesson, duplicate XP, review/progress key or provider audio upload is created. The extra introduction is fail-closed if the entire source dialogue's item IDs, full original Polish/English, original individual MP3 or protected reference drift. The original Read/Listen lesson stays available even if optional preparation is unavailable. Tourist Read steps retain their separate focused source-reuse behaviour and are NOT silently rewritten into the standalone new introduction.

**Important:** this teaches/introduces each original *complete line's meaning and sound* before reading assessment, and addresses the initial outside-learning assumption for comprehension. It does **not** constitute comprehensive explicit instruction in every noun declension, conjugation, pronunciation pattern or higher-level grammar used inside that full line. Those separate pedagogical review gaps remain listed OPEN in the exact source-level inventory.

## Quality and next work

[The strict preparation helper](frontend/src/reading-introduction.ts) accepts only the six original unchanged legacy recorded reading lessons. [The learner UI](frontend/src/RecordedReadingIntroduction.tsx) and stylesheet add a compact mobile-safe whole-turn listening/meaning experience. Mandatory content migration tests compare all **51 original source passages** to the generated 26-lesson catalog and verify the **51 exact MP3 files actually exist**, while separately checking every source-audit item count, 26 IDs/482 rows and all eight tourist IDs. Unit tests cover missing text/audio/ref blockers, source IDs and original English. Desktop/mobile E2E covers teaching/playing, advancing, backing up, beginning original Read comprehension, optional skip, 320px layout and unaffected tourist Read paths.

**Next priority after C-14:** perform the item-by-item Polish lexical/grammar prerequisite review of the 172 full basic items and the 51 reading turns (not merely source-level totals), then teach missing forms in meaningful micro-units. Also connect the T01–T08 source scenes to the explicit foundational grammar introductions *before* they are recommended as mastered scenarios. No outside learning should be required, no fictitious perfect-completion threshold, and [issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140) stays OPEN until genuine native and recording reviews exist.

**Certification:** final-head four CI lanes must PASS (frontend migration/TS/unit/build and desktop+mobile browser/audio/offline/a11y, family-connected browser, private backend, benchmark). Physical phone microphone and paid speech assessments are not tested by those suites.
