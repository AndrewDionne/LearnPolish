# C-10 — Polish alphabet and letter combinations in original recorded whole words

This tranche adds **real learner-facing alphabet fundamentals** to **Library → Your path → Start with the essentials**, before greetings and everyday expressions.

## What learners can actually do

Open **Explore the Polish alphabet**, select a Polish letter in the complete **32-letter alphabet**, hear its **original full Polish example recording**, inspect the original English meaning, and see the chosen letter highlighted **inside the spelling**. Use existing 0.75×, 0.85× or 1× playback and advance to the next letter. Switch to **Letter combinations** to explore **13 recorded spelling clusters** by the same workflow.

The complete 32-letter ordered alphabet is **A Ą B C Ć D E Ę F G H I J K L Ł M N Ń O Ó P R S Ś T U W Y Z Ź Ż**. The 13 additional focuses are **CZ, SZ, RZ, CH, SI, ZI, DZI, NI, SZCZ, TRZ, PRZ, KRZ, DZ**. Neither V, X nor Q is inventively promoted to a native Polish alphabet letter. This is a quiet, responsive 32-letter navigation grid with a full original-voice example per tile, not 32 added lesson tiles or independent new MP3s.

Examples selected from the actual original audio source include *A* in **Autobus**, *Ą* in **Jakub Dąbrowski**, *C* in **ulica**, *Ć* and *Ę* in **Pięć**, *Ł* in **Łódź**, *Ń* in **Poznań**, *Ź* in **Mateusz Woźniak**, and the cluster *CZ* in **Cztery**. Some complete examples are proper names, places, or phrases rather than simple dictionary words; labels/English meanings always match the original source material exactly.

This is instruction about **recognising Polish graphemes and encountering their pronunciation inside naturally recorded complete words**. It is **not** an authentic separately recorded spoken letter name course, isolated phoneme files, a context-independent phonetic equivalence, or a reviewed comprehensive Polish orthography / phonetics guide. A letter may be pronounced differently depending on surrounding letters; we are demonstrating an example in one actual context. Native review of full letter-name teaching, orthographic context and IPA explanations remains outstanding.

## Why source safety is essential

[v2/content/alphabet-recorded-examples-v1.json](content/alphabet-recorded-examples-v1.json) maps **45 exact source recordings** to one highlighted spelling focus and original English meaning. [recorded-alphabet.ts](frontend/src/recorded-alphabet.ts) validates **all 32 canonical letters in exact Polish order** and the **13 explicit combinations**, checks that the focus occurs exactly once, and resolves each only against the original built-in **legacy vocabulary** lesson/source ID, matching entire Polish utterance, original English, original matching per-item MP3 URL, and no `practice_only` speech reference blocker. Each inconsistent row is unavailable, rather than silently substituted with fabricated text or wrong audio. No new rights agreements or licensed recordings are claimed.

The entry is a **navigation and repetition aid**, not a new scored lesson, XP route, standalone letter-name clip, syllable-only playback, or a new personal data record. All original 26 lessons / 482 source items / 455 MP3 assets, 14 Speak reference blockers, C-05/C-06's 40 existing beginner focus items, C-09's 25 source word recognition examples, original Numbers 1–20 and optional 10+10, tourist T01–T08, family/consent/privacy/offline/backup remain untouched. Unreviewed C-02 native letter-name/IPA candidates stay unpublished. No visible/internal 3×3 journey labels, explanations or accessibility tier descriptions are added.

C-08 standard Speak is **complete word audio → learner whole word recording → one overall score and coloured syllable-like text hints, if valid/consented providers are available → Try again or Next**. C-10 never introduces syllable/isolated-sound playback or grading.

## Quality gates and remaining F0/F1 work

Automated migration and source tests verify every one of 45 entries matches its own **unchanged original Polish + English text and existing original full-recording MP3 file**. Unit tests cover 32 exact alphabet entries, 13 patterns, original source objects and fail-closed tampering. Desktop/mobile tests cover alphabet disclosure, browsing + advancing letters, accented characters, source word/meaning and focus, 13 combinations, playback rates and 320px accessibility.

**Remaining for a complete fundamentals curriculum:** human Polish editorial approval of phoneme explanations, 32 **spoken letter names** where pedagogically necessary, licensed full-word audio for currently missing combinations (e.g. dż vs dź and contextual consonant spellings), expanded first vocabulary, basic sentence/grammar explanation, and measured progress toward **80% of actual Journey 1 instructional time**. The existing 16:4 source guide split is a planned slot ratio, not real study minutes. See [issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140). Do not create unreviewed vowel or phoneme pronunciations from invented TTS or claim independent acoustic certification.

**Certification:** all four exact-final-head GitHub Actions lanes must pass before squash merge: frontend migration, types, unit, build + desktop/mobile/offline/audio/a11y browser; family-connected browser; backend and benchmark. No physical microphone/phone testing, external native human review or paid speech calibration is claimed.
