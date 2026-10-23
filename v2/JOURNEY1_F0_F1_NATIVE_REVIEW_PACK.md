# C-02 — Journey 1 F0/F1 foundation production packet (native review REQUIRED)

**Source authority:** GitHub issue [#140](https://github.com/AndrewDionne/LearnPolish/issues/140) and the completed [C-01 source-only path](JOURNEY1_FOUNDATIONS_80_PLAN.md).

**State: EDITORIAL CANDIDATES ONLY.** This tranche does **not** deliver any new learner-facing content, voice, phoneme labels, Speak feedback, scoring, or claim that the 80% actual learning-time objective is achieved. The original 26 source sets / 482 items / 455 inherited MP3, all 14 original Speak reference restrictions and eight T01–T08 tourist units are unchanged. C-01's 16/4 guide allocation remains a **planning proxy** only.

## What is produced here

The versioned [author corpus](content/journey1-f0-f1-editorial-v1.json) has four separately reviewable sections:

| Section | Candidate quantity | Review intent | Release state |
| --- | ---: | --- | --- |
| F0 letter inventory | **32** Polish alphabet letters in canonical order, each paired with one meaningful word + provisional English gloss | Native reviewer supplies exact letter **name**, primary sound(s), graphemic context, phonetic accuracy, stress and beginner-safe explanations | All name/IPA fields `null`, all approval/audio false |
| F0 spelling/pronunciation | **20** focused review rows | Vowels and nasal context, Polish vs English vowel expectations, Ł/L, c/cz/ć, s/sz/ś, z/ż/rz/ź, dz/dź/dż, ń/ni, ch/h, stress and assimilations | Candidate written words only; no sound-level clip claims |
| F1 functional vocabulary | **42** selectively sequenced everyday items in four groups | Politeness and social entry (8), pronouns/people (8), useful objects (10), questions/verbs/time/place (16) | Eight exact inherited **full-utterance** anchors; remaining 34 require new recording and review |
| F2 orientation | **10** unapproved fixed sentence candidates | First-person verb forms, accusative, genitive, question order, formal address, polite repair phrases | Preview for next tranche only; no source MP3 |

This is a *limited* word inventory intentionally optimized for early practical use: no 68-country or sprawling proper-name memorization, no arbitrary partial numbers lesson, no tourism-first detour. Words that are **inflected forms** (`mam`, `chcę`, `mogę`, `potrzebuję`, `jest`, `dobry`) are explicitly differentiated from dictionary lemmas. A native editor must verify lexical register, grammatical case, translations and eventual fixed speech prompts.

### Critical original-audio distinction

The **eight legacy anchors** (`Conversation_1:14`, `:15`, `:10`, `:8`, `:12`, `:2`, `:0`, `:4`) are references to existing source **utterances**, not newly extracted isolated sounds. The five existing `contrast_*` modules likewise contain genuine source-derived **whole-word** examples, **not** evidence of native-reviewed phonemes or letter-name clips. The old bundled `letter_recognition_1/2/3` MP3s must **not** be reused as aligned one-phoneme/one-word voices. Neither written candidate words nor English phonetic hints constitute verified audio.

## Print the actionable reviewer pack

```bash
cd v2/frontend
npm run test:migration
node scripts/foundation-editorial-gate.mjs --review-sheet
```

The review sheet prints each letter, spelling distinction, first word, English gloss, first-word original source (where known), and the ten provisional sentence bridges. This command is offline/read-only and does not invoke Azure, Whisper or an audio generator.

### F0 — independent native review checklist

1. Verify the **full 32-letter alphabet order** and each sample word; fill the letter-name and primary IPA fields only in a **separately reviewed successor** packet. Letters and sounds are different pedagogical objects. Verify spelling in context, not one English respelling per letter.
2. Review word-level realization of `ą/ę`, including place/context sensitivity and frequently oral word-final `ę`; `ó/u`, `y/i`, `ł/l`, `ć/ci`, `ś/si`, `ź/zi`, `ń/ni`, `ż/rz`, `ch/h`, `dz/dź/dż`, assimilation, stress and exceptions. Never present a spelling contrast as if it were automatically a phonemic minimal pair.
3. Assign per-item **recording text**, exact stable future ID, natural native speaker, rights/licence and SHA-256. Letter name, isolated phoneme, **whole-word example**, and **full utterance** each need a different production type and aligned file when taught separately.
4. Require a **second listener** to check Polish phonetic accuracy, clipping, word endings, natural stress and correspondence to the approved text. Do not promote old syllable color coding or inferred English transcription into a phoneme grade without independently validated phonetics.

### F1 — first vocabulary / composition checklist

1. Confirm utility, Polish meaning, English gloss, formal vs informal register, gender/case/number and inflected form. Avoid `pan/pani` slash targets as a single recorded Speak utterance.
2. For every first word, record one full, unambiguous Polish token **if the task is isolated word practice**; a legacy phrase MP3 cannot automatically be cropped without review or treated as that word's licensed original recording.
3. Approve the F2 fixed bridge sentences only after grammar correction and add their *own* independently recorded voices. Questions and answers need genuinely aligned responses; do not convert invented written text into a source-backed Listen/Speak or graded Read item.
4. Maintain graduated practice: F0 letter recognition and sound discrimination → F1 first 8 polite expressions → people/pronouns → concrete objects → questions/verbs → reviewed multiword patterns → short dialogue/reading. Revisit the same words in later contexts rather than just listing new nouns.

## Release and safety contract

`scripts/foundation-editorial-gate.mjs` plus a negative test suite run in mandatory `npm run test:migration`. The gate checks exact alphabet order, mandatory 20 sound patterns, 42 curated F1 rows, 10 F2 previews, eight exact original phrase anchors and all five source-derived contrasts. It rejects approvals, invented MP3s, fake letter-name/IPA authority, removed rows, changed original utterances, fabricated source refs or runtime imports. A separate PR with actual human approvals, new original audio and full provenance is **required** for learner publication. No editor checkmarks will be changed in this author-candidate packet.

### Recommended production sequence

- **C-02 (this branch):** a complete reviewable *syllabus and candidate text* for F0/F1; no new live lessons, no voices.
- **C-03:** obtain native reviewer edits and accept/reject each F0 candidate and every F1 form. Produce rights-cleared matching letter names and isolated/whole-word audio (no unapproved synthetic voice).
- **C-04:** integrate individually certified F0/F1 lessons with source/MP3 manifest, recording checksums, true beginner practice and mobile/offline testing. Keep 1–20 as one 20-item lesson with optional 10+10.
- **C-05:** native-reviewed first-person and short-sentence F2/F3 recordings, paired question/answer Listen/Read, actual re-use of early words, calibrated instructional time allocation.

**Integration gate:** ALL FOUR final-head GitHub Actions lanes PASS (frontend migration/type/unit/build/browser/offline/audio/accessibility; connected family; private backend; benchmark). CI validates packet integrity and unpublished status, **not** Polish linguistic correctness or acoustic quality. Native/audio approval, physical iPhone/Safari, paid provider testing and launch remain separate.
