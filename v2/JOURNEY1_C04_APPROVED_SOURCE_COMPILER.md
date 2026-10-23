# C-04 — Quarantined F0/F1 source compiler, not a content launch

**Status:** Software/compiler tranche only. Native Polish review, written English translation, letter-name IPA, voice rights, MP3 recording and independent acoustic certification are **not available** in this repository. [Issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140) remains open. **No new lessons or audio were published**.

This stage changes the *technical cost of integrating genuinely approved future assets*, not the language-learning claim. It deliberately neither copies C-02 draft Polish into `public/generated` nor enables a development flag to present fake certified content.

## What C-04 delivers

[Release compiler](frontend/scripts/foundation-release-compiler.mjs) derives prospective lessons exclusively from the 136 source-fingerprinted C-03 work items:

| Quarantined prospective module | Reviewable recording jobs | Source content |
| --- | ---: | --- |
| Polish letter **names** | 32 | Null pending original letter-name words, independent of alphabet symbols |
| Alphabet **example words** | 32 | One full candidate word per Polish letter; not isolated phoneme recordings |
| First polite expressions | 8 | Original eight exact `Conversation_1` **full utterance** references |
| People and pronouns | 8 | New individually recorded words needed |
| Everyday objects and places | 10 | New individual word audio needed |
| Questions and first verbs | 16 | Review inflected forms, then record exact prompts |
| First complete sentences | 10 | Review case, register, inflection and question forms before recording |
| **Total** | **116** | No ready-to-publish audio assets at present |

The other 20 F0 sound/spelling explanations require native-editorial review but **are not** standalone utterance recording jobs. A future phonetic lesson may use reviewed full words to illustrate them, without pretending a letter name or spelling label is an isolated sound.

### Source-locked contract

The compiler accepts a manually supplied **proposed** candidate with these critical proofs:

- Original C-03 `jobId`, job SHA-256 fingerprint and full source-inventory fingerprint. Unknown, duplicate, reordered/stale or cross-group source references fail.
- One normalized and unambiguous full spoken Polish target per recording; English meaning is separate and may provide multiple glosses. Changes to the C-02 candidate need a documented correction reason.
- References to human Polish review, English review and an independently recorded acceptance decision. They are *required claims*, **not authentication or linguistic/acoustic verification**.
- Media under `foundation-review-audio/<group>/<stable-job-id>.mp3` in a **private** review workspace, with declared original text, binary SHA-256, byte length, rights/speaker-release references, acoustic report and second-listener reference. Binary checks reject mismatches, obvious non-MP3 envelopes, traversal and remote URLs. **MP3 envelope and SHA-256 do not establish that the audio is decodable, accurate or permitted for release.**
- Deterministic future lesson IDs and audio slots tied to `F0-N-01` etc., not array position, to avoid migration of historic learner progress when source words are added. The return value is `quarantine_not_learner_approved`, never a live lesson manifest.

The committed [release intake](content/foundation-c04-release-intake-v1.json) is **intentionally empty** with `status: blocked_no_native_audio`, `published:false` and zero approved assets. The mandatory migration CI gate rejects promoting this committed document or referencing the new compiler/release-intake/audio workspace from learner runtime. C-04 does **not** introduce a source alias for `personal` content, a ninth tourist unit, a bypass in the 26-lesson legacy catalog or a new scoring signal.

### Tests

```bash
cd v2/frontend
npm run test:migration
node scripts/foundation-release-compiler.mjs
```

C-04 Node unit tests demonstrate **only compiler control-flow** with a synthetic, explicitly **non-decodable** in-memory byte fixture (not shipped, not included in the release intake, not a recording). The positive rehearsal remains *quarantined*. Negative tests check forged signoff fields, false publication, unreviewed sound concepts, source drift, alternative Polish targets, invalid voice paths, altered audio SHA/byte counts, missing recording rights/listening references and drift of permanent IDs.

Tests cannot replace external independent Polish pronunciation and accent review, authenticity of the reviewer/rights documents, decode QA, native listening QA, human authority to release or physical mobile/offline deployment testing. The compiler is an editor tool, not a course loader. It never writes assets, updates `lessons.json`, modifies XP/progress or publishes a proposed lesson.

## Next effective steps, not more empty curriculum shells

1. **Human native editorial work**: return real C-03 review feedback on the 32 names, 32 word examples, 20 sound/spelling concepts, 42 first vocabulary words and 10 elementary sentence targets; correct contextual Polish and English and approve every exact fixed utterance.
2. **Sound production**: record/verify 116 possible fixed targets as needed with proper licence and separate independent acoustic listening; do not force every prospective job to be recorded if native review eliminates or consolidates a weak choice. Choose real, stable recorded items first.
3. **Actual learner release PR**: only once native/editorial and audio evidence exists, assemble a small approved F0/F1 lesson batch, verify *decodable* audio and final exact spoken correspondence, integrate first into `prepare-content.mjs` and Library/Home journey *without changing original 26 legacy IDs*; certify desktop/mobile/offline/a11y/family/backups. No external tier legend.
4. **F2/F3 sequence + calibration**: reviewed basic grammar, short question/answer comprehension and true re-use of first words. Check whether fundamentals/basic comprise **80% of instructional time**; existing 16:4 practice slots are only a proxy, not measured study minutes.

**Existing software invariants:** preserve all original 26 lesson sources, 482 items, 455 imported MP3s, the 14 `practice_only` Speak blockers, one Numbers 1–20 set with optional 10+10 practice, 8 original tourist T01–T08 units / 22 mode actions, personal lessons, family XP/consent/privacy, backup, and offline audio. No synthetic audio, physical iPhone/Safari/microphone assessment, paid provider inference or production deployment asserted.

**Merge rule:** require all four final-head GitHub Actions lanes PASS, as with C-03. Software certification validates quarantining and source-binary data safety, **not** Polish native/audio truth.
