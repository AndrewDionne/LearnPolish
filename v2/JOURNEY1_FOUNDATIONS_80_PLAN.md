# C-01 — Journey 1 becomes foundations-first (80/20 teaching allocation)

**Owner priority, 24 October 2026.** Fundamentals and basic vocabulary should be the majority of Journey 1: **target ~80% of guided teaching and practice**, leaving ~20% for applying that knowledge in tourist situations. This is an **instructional design allocation**—not the fraction of Library rows called "Fundamentals", not a proficiency percentage, not an XP weighting, and not grounds to block spontaneous use of a tourist scenario.

## Change implemented in this source-only tranche

New [versioned guided source path](content/journey1-foundation-guide-v1.json) has **20 explicit practice slots: 16 foundation/basic source lessons + 4 applied checkpoints = 80/20 by guide slots**. The source lessons are opened *whole*, using their existing Learn, Listen, Speak and Read modes and inherited audio, not sliced into arbitrary 1–8 numeric fragments. A compact, initially four-item [Library guide](frontend/src/Journey1Guide.tsx) appears **before** the optional tourist scenario cards; learners can expand all 20 and start anywhere. It adds no full-screen onboarding, gamification, tier legend, mastery badge or duplicated lesson data.

The [core journey source placements](content/core-journey-v1.json) now follow the same first 16 source lessons across the ordinary Home Continue/Library course traversal. Initial greetings come first so the student can say something useful immediately; sound pairs and number families follow; everyday phrases expand into useful questions. A small sample of three existing recorded tram/museum conversations follows, and Journey 2's clothing and grocery readings stay independent. To support practical beginner places, `Road_Terminology` moves from optional Explore into Journey 1; no content ID or original recording is changed. `contrast_krzy_przy` moves from Journey 2 to later Journey 1 sound practice. All other source options stay open via Explore.

| Guide slots | Primary purpose | Verified existing learning source |
| --- | --- | --- |
| F01 | Common greetings and polite expressions | `Conversation_1` |
| F02–F06 | L/Ł, C/CZ/Ć, S/SZ/Ś, Z/Ż/Ź and KRZY/PRZY whole-word hearing contrasts | All five original derived sound-contrast sets |
| F07 | Complete numbers 1–20 | Single `numbers_1-20` (20 items; optional 10+10 within practice) |
| F08 | Small greetings-reading exchange | `Basic_01R` |
| F09 | Larger numbers | `Numbers_20-100` |
| F10 | Useful street terms | `Road_Terminology` |
| F11–F13 | Shopping, restaurant and eating-out expressions | `Conversation_-_shopping`, `Conversation_-_restaurant`, `Food_and_Dinning` |
| F14–F16 | Location, transport and emergency requests | `Getting_Around_1`, `Transit_1`, `Emergencies_and_Health` |
| A01–A04 | **Short applied checkpoints** | existing T01 greeting, T03 number/price, T05 grocery, T08 museum unit Listen activities |

The other four recorded tourist scenario units T02/T04/T06/T07 remain fully accessible in the independent **Conversation practice** grid. All T01–T08 retain their source-only / native-review-needed status, and T09–T12 remain unproduced. The checkpoints do not assert completeness or grade spoken dialogues. No synthetic voice or new reading content is introduced.

**Ratio qualification:** 16 out of 20 explicitly authored guided slots is 80%; **this does not establish 80% of real lesson minutes**, because a numbers practice and 26-phrase recording set differ in duration. Treat 80/20 as the target to audit and rebalance after meaningful content and pacing estimates exist. The UI intentionally does **not** show a misleading "80% complete" meter.

## What still needs to be filled: not solved by reordering

This source package **is not** a completed alphabet, grammar or everyday-vocabulary programme. The actual material audit revealed the following gaps. [GitHub #140](https://github.com/AndrewDionne/LearnPolish/issues/140) is the canonical work queue; it is not closed merely by this source-backed implementation.

| Curriculum segment | Existing source evidence | Missing teaching material |
| --- | --- | --- |
| Complete alphabet and letter-name distinction | Five sound-contrast sets with 26 source-derived *whole-word* examples | Systematic alphabet 32-letter coverage, correct letter names vs sounds, common multi-letter consonant groups, nasal vowel and stress examples; specific legal recording rights and human phonetic verification |
| Pronunciation for English speakers | Recorded L/Ł, C/CZ/Ć, S/SZ/Ś, Z/Ż/Ź, KRZY/PRZY contrast examples | Reviewed `ą/ę`, ó/u, y/i, ń/ni, ć/ci, dź/dż/dz, rz/ż, ch/h, ś/si, ź/zi; variable spelling sounds by context and minimal *real* examples |
| High-frequency first vocabulary | Greetings, the original whole Numbers 1–20, selected everyday sentence vocab | A deliberately limited list of high-use nouns, pronouns, verbs, question words, basic adjectives and essential actions; **not** a memorization dump of 68 countries or 32 surnames |
| Combining words | Original Shopping, Restaurant, Food, Transit phrases | Native-reviewed forms of I am/I have/I want/I need, common questions, negation, agreement, simple location/price phrases and short polite variants |
| Sentence building and listening | A few original reading dialogues and fixed source phrases | Progressive paired questions/answers, variation without fabricated reference voice, simple time, concrete two-way interactive comprehension and practical Read prompts |
| Review and sequencing | Indexed original source and local attempt/review machinery | Meaningful practice frequency, first-word reappearance in later phrases, grounded benchmarks for recall without equating an opened clip with language mastery |

The three retired `letter_recognition_1/2/3` bundled-word banks contain recordings that are **not** one-to-one validated alphabet/phoneme clips; no original 33 bundled rows are silently relabeled as 33 source-backed beginner sound lessons. No newly drafted text in #140 becomes learner-facing Polish until human-native / English / rights / exact recording / listening signoff, and its *own* four-lane source CI.

## Software and learner-safety proof

- The guide validator requires *exact* 16 source-lesson links and 4 existing unit checkpoints, no fabricated ninth unit, duplicate/personal source, invented lab or altered session allocation. It cannot change source items or audio and cannot claim a source-list slice is a new original lesson.
- Existing source-safety and 14 `practice_only` reference exclusions stay active for normal Speak; guide clicks open original lessons with existing mode guards.
- Existing Numbers 1–20 original 20 items, optional 1–10/11–20 selector, unmodified source/progress, historic backup and explicit Home Continue source IDs remain compatible. Newly core-placed `Road_Terminology` is now part of the canonical sequence, but older saved source IDs continue to resolve.
- Core review queue follows revised actual course order while Explore/personal lists stay independent. All 26 lessons, 482 original items and 455 inherited MP3s remain as before.
- The Library still shows all eight tourist scenarios and all 26 lesson cards, with no three-journey tier names, tooltips or accessible position labels. A compact expandable guide keeps mobile layout narrow; full desktop/mobile/320px regression verifies real launches, absence of invented grading and hidden-tier metadata.

## Recommended execution order

1. **F0 sounds/letters**: independently reviewed alphabet and source recordings; complete sound clusters and vowel distinctions, not just consonant contrast examples.
2. **F1 foundational vocabulary**: short, high-frequency, practical modules with the first useful words, everyday verbs and questions; no large city/country inventory as core.
3. **F2 basic grammar and phrase building**: pronouns, first-person patterns, question forms, negation, frequent collocations, polite natural alternatives, basic agreement/number.
4. **F3 listening/speaking/reading progression**: use reviewed whole-word audio first, then fixed multiword/sentence recordings and true source-grounded responses, not automatic transcripts as verified pronunciation.
5. **F4 integration and calibration**: ensure the 80% goal is reflected in *actual guided practice emphasis*, revisit vocabulary across new contexts, then advance the remaining T09–T12 scenarios with approved audio.

This is an **ongoing content production tranche**, not simply a one-off restructure. Physical iPhone/Safari, human acoustic review, paid Azure/Whisper and production rollout remain explicitly separate.

**Merge certification:** final PR head must pass all four GitHub Actions lanes: frontend source validation/TypeScript/unit/build/full desktop-mobile browser/audio/offline/accessibility, connected-family browser, private backend and benchmark. Synthetic success does not approve Polish pronunciation or the 80% *time* target.
