# Journey 1 continuity audit — 2026-11-10

**Scope:** Source-verified progression and native support only. No independent native Polish editorial review, voice calibration or acoustic certification is claimed. V2 is the content authority.

## Verified inventory

| Path | Evidence |
| --- | --- |
| Guided Foundations | 16 ordered groups; 68 original full-recording references; seven introductory grammar groups |
| Guided opening | Yes/no, politeness, greetings; then street/place words, transit, everyday replies |
| Sentence bridge | Requests, location and permission questions, prices, yes/no questions, negation, one/two forms |
| Guided practice | Source-backed food, shopping and location questions after introductory patterns |
| Core Journey 1 | 19 independently placed V2 lessons (8 beginning, 8 middle, 3 end) |
| Core Journey 2 | Two independently placed lessons; none in Journey 3 |

The original source dependency manifest checks named concepts, NOT a complete first-use lexical or inflection inventory. Grammar examples introduce whole recorded Polish phrases and complete meanings before testing, but full lexical and phonetic closure remains unverified.

## Implemented V3-08C

Native guided exercises now offer a collapsed, optional **Earlier learning to revisit** section. Each linked lesson is the exact earlier source group that introduced an explicitly required concept and still contains original recorded items without a saved Learn attempt. A Skip, audio play or translation reveal is not mastery. A missing attempt prompts review but does not lock advancement or impose an 80-percent threshold. Tests verify cross-step dependencies and partial-practice behaviour.

## Reproducible first-use vocabulary inventory

The [full 68-row source-derived first-use inventory](JOURNEY1_FIRST_USE.md)
now records the exact original Polish phrase, full English meaning, source
reference, existing MP3, optional author-marked grammar focus, and all written
word forms first encountered by a learner at that point. The inventory contains
**74 distinct case-folded written forms across 55 unique original audio
recording IDs** (68 appearances including intentional reuse).

This is a surface-spelling audit, **not** morphological lemmatization, comprehension
evidence, sound coverage, or linguistic certification: every row remains
**Pending independent human review**. Native CI checks a byte-for-byte
source-derived report so later changes to the approved V2 material cannot
silently invalidate the inventory. The separate core Journey 1 lessons and
Sound Lab are beyond this guided-only first-use audit.

## Editorial and continuity gaps

1. **Lexical first-use review:** check every Polish word, inflected form and complete English gloss at first exposure in all 16 steps, especially nouns/actions in request, shopping and location recordings. The current dependency graph covers only named constructions.
2. **Sound-before-word review:** independently verify that the alphabet and 13 letter-combination sounds support first-use spoken vocabulary. The five sound lessons do not establish complete coverage.
3. **Single coherent path — navigation resolved, editorial proof outstanding:** UX-03A now presents exactly 16 guided groups and 19 original Journey 1 source lessons as eight sequential chapters with one Home/Practice continuation. The original five source sound contrast lessons have moved earlier, after recorded first words. The source IDs, recordings and user progress still use the V2 identities. The *navigation* is unified; a complete human-reviewed full-core first-use/phonetic/grammar prerequisite audit has not been completed and is required before calling it a fully gapless course.
4. **Grammar comprehension:** independently check seven grammar explanation texts, forms/translations, answer options and vocabulary transitions; source integrity alone is not pedagogical certification.
5. **Physical readiness:** offline first-run, small-screen UX, MP3 play rates, speech and recording quality, restart, privacy of any optional connection, CloudKit signed devices and family/guardian policy remain separately unverified.

**Next safe editorial tranche:** prepare a first-use lexical inventory with exact original utterance ID, Polish sentence, full English meaning, lesson position and human-review status. Do not silently fill missing material with invented recordings or outside-study requirements.

## UX-03A source-coherent native path (2026-11-11)

See [UX_LEARNING_ARCHITECTURE.md](UX_LEARNING_ARCHITECTURE.md). The 8 chapters contain activity counts **3 / 5 / 5 / 7 / 4 / 4 / 4 / 3 = 35**, comprising 16 original guided groups and all 19 of the existing Journey 1 source lessons. There is no new lesson source or new grade identity; repeated original MP3 references share original source IDs. Home's recommended next activity comes from the first genuinely unpractised step in this single sequence rather than a parallel resume cursor. A skipped step remains unpractised. Sound contrast lessons were repositioned earlier as an explicit instructional ordering proposal, not a new pronunciation claim. Two Journey 2 lessons remain outside the core first journey.

**Remaining risk:** explicit dependency closure is only at named-concept level; full core first-use vocabulary/inflection and human phonetics audit remain open. Journey 1 is not yet independently accredited as no-outside-knowledge or acoustically calibrated.

## UX-03B: full original-source written-form first-use inventory (2026-11-11)

See the [381-row unified source report](JOURNEY1_UNIFIED_FIRST_USE.md), derived from original V2 Polish/English/MP3 references in all **35 native Journey 1 activities**. The reproducible script `v3/ios/scripts/audit-unified-first-use.mjs` validates 8 chapters, 16 guided groups, 19 core V2 lessons, 381 source occurrences, 313 distinct original item IDs, 344 distinct first encountered NFC/case-folded written word forms, and 328 first non-sound meaning-exposure word forms. The existing 68-row guided-only report remains available as a historical component-level provenance witness, not a second authoritative Journey 1 path. Sound contrast examples are not automatically marked as full lexical teaching.

The first automated quiz audit identified **68 candidate prior rule violations** (a correct Polish match with a distractor sourced from a later card, potentially disclosing its English meaning). UX-03B changes the native source lesson introductory match so two distractors must come from earlier original cards, or the new card remains Speak. The revised source audit demands **zero future-card options**. This resolves the static future-option leakage and **does not** certify inflection/case coverage, word comprehension, independent human review, acoustically valid syllables, or that a learner did not Skip past prior words.

**Human editorial queue stays open:** Verify 381 full Polish/English pairs, 344 orthographic first encounters and appropriate pronunciation/sense/case teaching before each tested sentence; align source-backed repetition across the 8 chapters and determine which core dialogue lines require an earlier source-backed introduction. No invented translations, MP3s, graded outcomes or new outside-study requirement has been added.

## UX-03C1: source-backed runtime exposure gate (2026-11-11)

UX-03B's full 381-row report identifies the static order of original texts, not whether each individual learner actually practised the preceding words. UX-03C1 adds a live record-backed teaching guard: an ordinary first-contact phrase is displayed in **Speak** with its source English meaning and MP3, not as an unintroduced matching question. A genuine source-recorded Speak attempt can immediately trigger a three-choice **Learn** recap on the *same* phrase only after two other distinct earlier source English meanings have saved practice evidence. Skipping, browsing or listening without a real saved attempt does not qualify distractors. Historical Learn self-ratings count as earlier exposure but never as new objective grades. Scheduled Learn reviews use only previously practised original meanings or fall back to a labelled self-rating; unreviewed future words are never introduced through answer choices.

**Human limits remain:** A past attempted item is not proof its meaning was understood, nor a guarantee of correct case/inflection, pronunciation, contextual grammar, or true listening comprehension. Source-backed additional spaced retrieval and rigorous bilingual/acoustic sign-off are separate UX-03C2 release gates.

## UX-03C2A: repetition with evidence, dialogue preview without fake listening (2026-11-11)

The automatic first-use report remains Pending for independent Polish review. The iPhone Practice tab now offers a small opt-in reinforcement session from previous, genuinely practised Journey 1 chapters, reusing original MP3s and exact source item IDs and scoring only objectively answered Polish-English matches. It neither manufactures additional source items nor assumes that merely seeing a previous card taught it. The ordinary Daily Review remains scheduled separately; a successful or missed reinforcement answer enters that existing scheduling mechanism.

Dialogue lines not previously attempted can be inspected in an optional *ungraded* original-source preparation view before answering the authored dialogue question. This supports first-contact comprehension without claiming that a visible line was heard or understood. Correct morphology/phonetics, genuine dialogue-level prerequisite closure, and headset routing remain separate acceptance criteria.
