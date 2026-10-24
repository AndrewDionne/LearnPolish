# C-06 — Actual recorded beginner vocabulary and short-phrase sequence

**Release category: new guided practice of ORIGINAL source material, not new recordings or independent Polish/audio signoff.** This is the next learner-facing fundamentals implementation after [C-05](JOURNEY1_C05_REAL_BEGINNER_PRACTICE.md), not another unpublished curriculum shell.

## What actually changes for learners

From **Library → Your path → Start with the essentials**, expand **Keep building your everyday vocabulary**. Six optional short, ordered, genuinely usable sessions follow the first eight C-05 greetings:

| Practice | Original source set | Real recorded original items |
|---|---|---:|
| More everyday replies (e.g. *Może*, *Nie rozumiem*) | `Conversation_1` | 5 |
| Street and place words (*ulica*, *plac*, *most*, *rondo*) | `Road_Terminology` | 6 |
| Getting around: first words (*bilet*, *metro*, *autobus*, *tramwaj*) | `Transit_1` | 6 |
| Simple food requests (*Poproszę wodę*, *Poproszę kawę*, *Deser*) | `Conversation_-_restaurant` | 5 |
| Questions in a shop (*Ile to kosztuje?*, *Gdzie jest kasa?*) | `Conversation_-_shopping` | 5 |
| Asking where things are (*Gdzie jest metro?*, *Ile kosztuje bilet?*) | `Getting_Around_1` | 5 |
| **New practice inventory in C-06** | **6 original sets** | **32** |

Together C-05 and C-06 expose **40 distinct exact original recorded lesson item IDs** as a graduated beginner practice sequence. C-06 alone includes **16 original single-word targets**, with short recorded phrases and questions to move from isolated lexical items to useful language. This is **not** the same as C-02's provisional 42-item F1 editorial draft, and should not be counted as 40 newly approved words. No false claims of full 32-letter alphabet or reviewed letter-name IPA.

Every focused exercise is a subset of **one** existing original vocabulary lesson. Practice uses the original `LessonItem` instances and original `generated/audio/<source>/<index>.mp3` path. Users can Learn, Listen and Speak without cloned progress IDs or invented scores, progress through completed groups using **Next: ...**, or return to the original full lesson. Existing cards, global review, family XP/consent and offline audio use their original source identifiers.

The full guide remains available, and the new optional exercises **do not alter its 16:4 planned-slot ratio**, which remains only a curricular allocation proxy, not a measurement of actual instruction time. Nor do new groups add nine-tier labels, tooltip legends or inaccessible/invisible descriptions of internal learner categories. They do not advance the Home course cursor when manually chosen.

## Source and integrity contract

- [C-06 exact-source plan](content/foundation-next-words-v1.json) maps **6 original lessons / 32 fixed Polish + English source utterances**.
- [Validated runtime focus](frontend/src/foundation-next-words.ts) independently pins those 32 source texts/English meanings. Only the six original legacy vocabulary lessons with an exact item ID, exact original Polish+English, matching **own original MP3 path** and no Speak-blocker status produce clickable groups.
- Any missing, substituted or mismatched audio/Polish/translation/protected source makes its **entire affected group unavailable**; other correctly sourced groups remain accessible.
- Neither the C-02 unpublished letter/sound editorial material nor C-04 empty blocked release intake is imported or mapped into learner data; the C-05 eight original greeting groups remain unchanged.
- No new audio, phoneme/isolated pronunciation grading, fabricated alternative reference or user progress migration.

Unit tests compare all 32 C-06 rows to the authentic six `docs/sets/*.json` sources and check group counts, duplicate prevention, source mismatches, protected audio, mode identity and tamper cases. Desktop/mobile Playwright covers the six-group disclosure, Learn/Listen/Speak, 5-item completion and next-session navigation, 320px layout, stable full 26-lesson Library count and absence of internal journey-tier labels. All existing baseline tests remain required.

## What is genuinely missing for Journey 1

The 32 canonical Polish **letter names**, independently approved letter/word sound recordings, 20 context-sensitive orthographic topics, and the unrecorded high-frequency first vocabulary + basic F2 grammar still need real native Polish/English editorial acceptance and licensed **decodable** aligned recordings before new authored F0/F1 learner lessons. Tracked in [open issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140). Inherited source text+audio **are not** independent human acoustic certification. The C-04 compiler and native-review packets remain useful for genuine future new content, but publishing more empty shells will not advance learner proficiency.

**Merge gate:** all four exact-final-head GitHub Actions lanes must pass (frontend migration, TS/unit/build, all desktop/mobile/offline/audio/accessibility browser journeys; connected-family browser; backend; benchmark). No paid inference, physical phone/mic testing or production launch is claimed.
