# C-13 — Curriculum continuity and in-program prerequisite coverage

## Authoritative owner requirement

**Forget the 80/20 quota.** This is not an allocation exercise. Learners should not need to go elsewhere to acquire knowledge assumed by later lessons. **Lesson N must only rely on ideas explicitly introduced and practised earlier in this same recommended path (lessons 1 to N−1).** Any genuinely new words, constructions, sounds or grammatical forms may be introduced **inside Lesson N** with clear meaning, matched recorded audio when available and practice; they cannot be silently presumed known. A learner should be able to start at the beginning and progress without researching outside the app.

**Source-first trust:** never stitch original audio fragments into new words or falsely claim independent native accuracy; C-08 Speak remains full-word/sentence source audio → learner's complete-word recording → one overall score + coloured word text → Try again / Next. The learning path is flexible to revisit prior material; it should not impose artificial proficiency locks, rewards, percentages or hidden tier labels.

## Findings from the first-pass audit

1. **First words → basic vocabulary → sentences** was reorganized in C-12, but the original full shopping and location question practice **came before** the C-11 grammar patterns that would explain the questions. This was a real dependency gap, not fixed by heading changes.
2. Even C-11's five grammar introductions did not explicitly introduce **Gdzie mogę ...?**, **Ile ...?**, or **Czy to ...?**, while the later recorded application lessons contain those forms.
3. The old supplementary 20-entry original source index enforced a hard 16-foundation/4-application split with a numeric 80% field and tests. This was bookkeeping, **not a measure of prerequisite continuity**, and is no longer a curriculum requirement.
4. The original 26 long legacy lessons and historical Home course cursor still include raw material not individually audited at the vocabulary/grammar concept level. **They remain available for exploration and may not be certified as a gap-free alternative beginner route solely by this tranche.**

## Implemented C-13 correction

In the guided Journey 1 path: **Alphabet/sound practice → First words → Basic vocabulary → FIRST explicitly taught sentence constructions with recorded examples → practising full requests and questions**.

The existing C-11 grammar module is moved *ahead of* the three C-06 application groups. After the final basic vocabulary source group, **Next** opens the recorded grammar introduction. After studying the final grammar pattern, **Continue to sentence practice** launches the first complete recorded request group. All source lessons remain independently selectable for voluntary review and exploration; this is not progress-gated schooling.

Added original recorded teaching introductions for:
- **Gdzie mogę kupić bilet?** (“Where can I buy a ticket?”): extends the Gdzie (“where”) lesson to the form used later in location questions.
- **Ile to kosztuje? / Ile to razem? / Ile kosztuje bilet?**: introduces Ile, “how much,” before shopping and transport price questions.
- **Czy to pociąg do Warszawy? / Czy to daleko stąd? / Czy to jest na promocji? / Czy to jest daleko?**: introduces simple Czy to yes/no constructions before application.

C-11 now has **seven** original-audio teaching pattern groups with **28 distinct inherited full recorded utterance item IDs** (original 20 + 8 new curated references), with fixed original Polish, inherited exact English and real individual MP3 files. No invented voices, added duplicate lesson records, spoken syllable files or provider charges. The original C-05/C-06 **40 distinct source practice item IDs**, all 26 lessons, 482 source rows, 455 original MP3s, 14 Speak reference blockers, Numbers 1–20, tourist T01–T08, family/privacy/offline/XP and original progress remain unchanged.

[The prerequisite graph](content/journey1-prerequisites-v1.json) records the exact recommended **16 instructional activities** (three first-word groups; three vocabulary groups; seven grammar teaching patterns; three recorded full-sentence application groups) with what each introduces and requires. [The runtime prerequisite guard](frontend/src/journey1-prerequisites.ts) checks that each explicitly declared prerequisite concept was introduced **earlier** and refuses forward references, duplicate/untracked concepts and missing foundational sources. If any original recording fails its separate source validator and that lesson vanishes, dependent later application groups are **withheld** rather than presented as prerequisite-complete. Unit and E2E tests check those cases, source ID preservation, original audio integrity, exact ordering, and desktop/mobile grammar-to-practice handoff.

**Important scope of this guarantee:** the machine check covers **explicitly inventoried constructions**, not every individual Polish word, all inflection/case phenomena, or acoustic/translation accuracy. Glossed original whole utterances introduce new vocabulary at point of use. An independent Polish curriculum/linguistic audit is still needed before claiming the entire Journey 1—including original full source lessons and conversations—contains **zero** unintroduced language, vocabulary, pronunciation or listening assumptions.

## Next audit and development standard

For every future lesson, before publishing:
1. List **required knowledge** and map every dependency to an earlier lesson/explicit review, or reclassify it as new instruction **taught inside the current lesson**.
2. Introduce every new lexical/phonetic/grammar concept using a clear gloss/explanation and a properly matched **complete-word/utterance source recording**, then provide recognition and recall before relying on it.
3. Test source text/English/audio and order, including missing-source failure, review transitions, accessibility/mobile and continuity of progress.
4. Trace the **entire** Journey 1, not just this focused first path: alphabet/sound examples, 26 historical full lessons, tourist scenes, dialogue comprehension, numbers and grammar forms. Document remaining missing bridges and fill them **before** treating the affected lesson as a recommended next step. Avoid pretending a structural graph replaces native Polish editorial review.

Issue [#140](https://github.com/AndrewDionne/LearnPolish/issues/140) remains OPEN for genuine Polish native pedagogy/acoustic validation and correctly recorded **new** vocabulary/audio as required by remaining gaps. There is **no numeric 80/20 coverage target** and no standalone syllable audio requirement.

**Certification:** all four exact-final-head CI jobs must PASS before merge (frontend migration/TS/Vitest/build+desktop/mobile/offline/a11y browser, connected-family browser, backend, benchmark). Passing software tests is not linguistic signoff.
