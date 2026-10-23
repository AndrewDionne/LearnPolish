# C-03 — F0/F1 native reviewer intake and recording work orders

**Stage:** GitHub issue [#140](https://github.com/AndrewDionne/LearnPolish/issues/140). **Editorial intake and software validation ONLY**, not completed native language approval, voice production or a learner release. This adds a way to **collect reviewer corrections**, which did not exist in C-02. It never writes back to the C-02 candidate corpus.

## Input and output

Source: [C-02 F0/F1 candidates](content/journey1-f0-f1-editorial-v1.json), which must continue to pass `foundation-editorial-gate.mjs`. Derived deterministically on each run — no second competing curriculum list.

| Separate human review jobs | Count | Important audio distinction |
|---|---:|---|
| Spoken letter **name** | 32 | Polish spoken name must be supplied/reviewed; the letter symbol is **not** its spoken sound |
| **Whole** example word for the letter | 32 | Needs its own exact word, meaning, natural stress and audio |
| Phonetic spelling **concept** | 20 | Explains a contextual contrast; **not itself a recordable utterance** |
| First everyday vocabulary item | 42 | Eight cite legacy **full utterances**, never isolated phonemes; 34 have no source voice |
| First sentence-builder preview | 10 | Grammar, register and case are unreviewed; no voice |
| **Total** | **136** | **116 possible utterance recording targets** are blocked pending real text/audio review |

All 136 review jobs have deterministic stable IDs, SHA-256 *candidate content fingerprints* and an aggregate inventory fingerprint. These hashes detect editorial changes/stale forms. **They are not a cryptographic signature proving a native reviewer's identity, expertise or approval.**

### Step 1 — generate forms on a trusted local machine

From the GitHub repository root:

```bash
cd v2/frontend
npm run test:migration

# Human-readable reviewer worksheet (UTF-8 CSV)
node scripts/foundation-review-intake.mjs --review-csv > ../../foundation-review-worksheet.csv

# Full machine-checkable response template; 136 pending rows
node scripts/foundation-review-intake.mjs --template-json > ../../foundation-review-feedback.json

# BLOCKED recording planning list: 116 possible utterance targets; no approved text
node scripts/foundation-review-intake.mjs --recording-csv > ../../foundation-recording-work-order.csv

# Smaller reviewer worksheets for the individual sections
node scripts/foundation-review-intake.mjs --section=f0-letters --review-csv > ../../foundation-f0-letters.csv
node scripts/foundation-review-intake.mjs --section=f0-patterns --review-csv > ../../foundation-f0-patterns.csv
node scripts/foundation-review-intake.mjs --section=f1-words --review-csv > ../../foundation-f1-words.csv
node scripts/foundation-review-intake.mjs --section=f2-preview --review-csv > ../../foundation-f2-preview.csv
```

Only write these files to a **private working directory** if they will later include the human reviewer's name, contact details or recording contracts; avoid uploading personal identity/contract data to this public repository. The tool does not make network requests, modify source, synthesize audio or write files automatically. `foundation-review-worksheet.csv` is a readable planning/review worksheet; **JSON is the versioned, machine-checkable feedback interchange**. Review decisions from annotated CSV must be transcribed back to the matching JSON rows with exact IDs before validation.

### Step 2 — native reviewer feedback

Use separate editorial reviewers for Polish spelling/word sense, register and grammar, plus a voice/acoustic reviewer later. Give the reviewer the C-02 draft and its limitations. The prefilled JSON feedback template starts with `decision: "pending"` for every row.

For each row where review feedback is available, set exactly one of:

- `"suggest_change"` — propose `proposedPolish`, `proposedEnglish`, `phoneticNotes` or `grammarAndRegisterNotes`; must also give `reviewerReference`, `reviewDate` and `evidenceNotes`.
- `"feedback_submitted"` — reviewer believes the editorial candidate is acceptable or has a contextual note; must include those same identifying/date/reason fields. **This is not independent certification**.
- `"pending"` — leave every reviewer response field `null`. Missing responses remain visible; no silent acceptance.

For a Polish letter-name row (`F0-N-XX`), the original `polish` is **null**. Record a *proposed* spoken Polish letter name; do not copy the letter symbol or reuse the example-word recording. For a word row (`F0-W-XX` / `F1-...`), annotate exact spelling, translation, accent/stress and dictionary vs inflected form. For a spelling concept (`F0-XX`), explain whether the claimed contrast is contextually accurate, without manufacturing a supposed standalone consonant sound. For the ten preliminary F2 sentences, check case government, forms, register, situational accuracy and whether natural reply alternatives require separate fixed recordings.

**Polish pronunciation risk areas:** `ą/ę` are strongly contextual, `ó/u`, `ż/rz` and `ch/h` often share sounds despite distinct spellings, `ć/ci`, `ś/si`, `ź/zi`, `ń/ni` depend on spelling context, and `dz/dź/dż` must not be flattened into one sound. A Polish professional must verify stress and phrase delivery; avoid English approximations masquerading as acoustic truth.

### Step 3 — validate the returned response, but DO NOT publish it

```bash
cd v2/frontend
node scripts/foundation-review-intake.mjs --validate-feedback=../../foundation-review-feedback.json
```

This checks exact source fingerprint, every ID and row in original order, allowed reviewer-decision vocabulary, syntax of dates and explanatory notes, and rejects invented approval/audio fields. It prints only counts and `status: "unverified_reviewer_feedback_only"`; `approvedText: 0`, `approvedAudio: 0`, `learnerImportAllowed: false` **even for a fully filled response**.

Never infer an authenticated native reviewer, language correctness, a real licensed voice, acoustic QA or ability to publish from this script, a submitted reviewer name or a SHA-256 checksum. Authentic reviewer contract/evidence must be checked **outside the tool** and explicitly approved in a separate controlled production process.

## Recording production gate — deliberately blocked

The 116 possible utterance recording work orders identify **32 letter names + 32 letter example words + 42 first vocabulary items + 10 sentence candidates**. All 116 are blocked until exact Polish text and use case are verified; the 20 *explanations* are not themselves recording targets. The eight original `Conversation_1` utterance refs are legitimate source references but must be individually checked for exact text, licensing and acoustic fitness before reuse; no cropping to unverified isolated phonemes.

After approved text, give each intended utterance a unique canonical future content ID, recording kind (letter name / whole word / full sentence), speaker/voice release and allowed modes. Verify bitstream integrity (file SHA-256), exact canonical text hash, recording duration/format, no clipping/truncation, independent native listening and recorded consent/rights. Store sensitive contracts privately and only safe provenance/reference IDs in GitHub. A later **separate C-04 content integration PR** must own these assets and the genuine Learn/Listen/Read/Speak teaching interactions; not this C-03 editorial intake. Do not put prospective MP3 paths in active source data and do not let a user-submitted feedback decision bypass approval.

## Software gates and continuity

`npm run test:migration` includes the new fail-closed native-feedback intake tests, covers all 136 derived jobs, 8 exact source references, stale row/sha, duplicate/missing/reordered rows, false approval/published/voice fields, invalid feedback, spreadsheet-formula injection and 116 blocked recording candidates. Earlier C-01/C-02, B-09 and existing source integrity and protections are unchanged.

**No new learner lessons in C-03.** Original 26 / 482 / 455 recordings, 14 protected Speak rows, one complete Numbers 1–20 (optional 10+10 within practice), T01–T08 tourist units, 16:4 guided-slot ratio, family privacy/XP/backups and offline unchanged. The real instructional-time 80% target remains an unmeasured goal.

**Next:** import actual independent human feedback, resolve changes, attest licensing and record separately, then implement true audio-backed F0/F1 lessons and graded but honest interactions in C-04. Issue #140 stays OPEN. Four final-head GitHub CI lanes must pass before merging the *software intake*, but green CI does **not** certify Polish linguistic accuracy or a native human reviewer.
