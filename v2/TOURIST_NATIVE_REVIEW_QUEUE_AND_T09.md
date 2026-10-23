# B-08 — Native-content backlog and accommodation T09 editorial preparation

**Status: REVIEW PACKET ONLY. NOT PUBLISHED, APPROVED, RECORDED OR SCORED.** Baseline: GitHub `main` `de943ffefb9da054c6e0c99f8d76df28ad5bb2c6`, certified B-07 / T08. The 8-unit source-only tourist pathway and 26 existing built-in lessons remain unchanged.

## 1. Why the curriculum stops at eight live tourist units

Audit of the checked-in `docs/sets/*.json` inventory finds **no accommodation/hotel/check-in lesson**, approved fixed Polish hotel dialogue or matching inherited MP3s. Existing isolated phrases and number recordings are not a substitute for an authentic two-person check-in; adding an empty T09 or treating a text candidate as recorded/validated language would create false completion and risk the app's pronunciation grading.

B-08 therefore prepares (but does **not** serve) two JSON records:

- [Native reviewer queue](content/tourist-native-review-queue-v1.json): one unresolved work item each for **T02–T09**; exact GitHub issue, live/source status, language/voice/Read deliverables and **explicitly false** text/audio approval flags. T02–T08 remain source-only practice, while **T09 is absent** from the learner.
- [T09 editorial candidate](content/tourist-t09-accommodation-draft-v1.json): a **fictional, provisional** 16-turn guest/reception exchange, each with Polish candidate, English meaning, distinct speaker role, immutable *draft-only* `T09-D01…D16` editorial identifiers and **null audio**. The candidate is **not native-reviewed Polish**, not a canonical practice set and not a provider prompt. `Nowak` is a fictional surname; two-night booking, breakfast and check-out times are illustrative, **never verified hotel policy**.

The candidate gives a native reviewer something concrete to edit instead of asking for approval of an unscoped idea. It covers reservation lookup, number of nights, document request, room card/floor, breakfast hours, polite repetition, check-out time, elevator directions and leave-taking. A reviewer may reorganize or replace these turns; the current draft is **not** approval. After approval, publish a separate new/versioned content asset with **new stable canonical IDs**, rather than silently reclassifying `T09-Dxx` as imported source IDs or replacing original `docs/sets` content.

## 2. T02–T09 review board (issues remain open)

| Unit | Native-review issue | Unfinished language outcome | State |
| --- | --- | --- | --- |
| T02 introductions | [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) | Complete natural first-person named reply, pronunciation target and register | Original source practice only |
| T03 numbers / buying | [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) | Genuine quantity, price, clerk/payment answer and verified receipt/sign | Original source practice only |
| T04 restaurant | [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) | Waiter/customer role-play, real response and menu/bill Read | Original source practice only |
| T05 grocery | [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) | Seller reply, quantity selection, price/checkout; depends on T03 price correctness | Original source practice only |
| T06 wayfinding | [#132](https://github.com/AndrewDionne/LearnPolish/issues/132) | Left/right/straight pedestrian directions, repeat/clarify and wayfinding sign | Original source practice only |
| T07 transport | [#134](https://github.com/AndrewDionne/LearnPolish/issues/134) | Correct line/platform, transfer, ticket validation and authentic timetable Read | Original source practice only |
| T08 museum | [#136](https://github.com/AndrewDionne/LearnPolish/issues/136) | Museum-specific staff/visitor exchange, ticket-hours notice and native QA | Original source practice only |
| **T09 hotel** | [#137](https://github.com/AndrewDionne/LearnPolish/issues/137) | **NEW** native-reviewed check-in dialogue, licensed 2-voice recordings, booking notice | **Not a live unit / no audio** |

The queue is an **editorial work scheduler**, not part of the user's visible three-journey taxonomy, a skill score or a release-status badge.

## 3. Per-turn native review and recording acceptance contract

Each proposed T09 guest/receptionist utterance requires, **in this order**:

1. **Text and comprehension review:** two-role coherent exchange, realistic polite Polish, plausible gender-neutral vs `pan/pani` forms, natural word order, exact English match, numeric pronunciation ("dwie noce", "siódmej", "dziesiątej", "jedenastej") and Polish room/floor conventions. In the draft, text and translations are **unverified hypotheses**. Reviewer approves a fixed, unambiguous reference, not a speech model's plausible transcription.
2. **Scenario constraints:** use explicitly fictional reservation name/property, nights, breakfast/check-out hours and room floor; no real pricing, government ID handling, reservation integration, personal data or claim of present-day hotel policy. Check whether the request to repeat has a natural staff reply.
3. **Voice plan:** one naturally spoken *full utterance per canonical turn*, **guest and receptionist as audibly distinct reviewed voices**. Record and listen end to end, especially word-final consonants/syllables, stress, numbers, turn transitions and truncation.
4. **Provenance:** licensed right to use both voices/audio; canonical text SHA-256, canonical audio SHA-256, recording file format/length/sample rate, voice identity or consent metadata, first native text approval, independent acoustic reviewer sign-off. Record provenance **on actual files**, never generate hashes for absent recordings.
5. **Training tasks:** construct a contextual listening question/answer based on the recorded line; a practical booking confirmation or check-in notice with verified written text and unambiguous Read questions; a Speak target with only one approved fixed form. No claim of mastery based on a listened-to clip, skip, XP or attempted count.
6. **Integration:** a **separate human-approved source/audio PR** with meaningful exact item IDs (not editorial `T09-Dxx`), proper exported offline assets, reviewed pronunciation guides and reference exclusions. All four final-head GitHub jobs pass; physical iPhone/Safari and real microphone evidence and native acoustic review remain separate. Azure/Whisper use and production launch require their own authorization.

Proposed private recording file convention is **only a specification**: after full text review, stage `staged/private/t09/{draftId}.mp3` per line and match it to a new content ID via a reviewed manifest. The folder and files have **not been created**, nor are the draft IDs considered source lesson IDs. Avoid TTS/cost, even free tier, until authorized.

## 4. Gate integration and rollback behavior

`v2/frontend/scripts/tourist-native-review-gate.mjs` and its negative tests are added to the mandatory `npm run test:migration` path. They reject:

- Publishing/approving an editorial row, changing required issue coverage, forgetting one of T02–T09, inventing an already-recorded T09 source or altering protected review status;
- Any audio file path in a T09 draft turn, changed speaker/order/ID, missing Polish/English, premature rights/voice sign-off or missing Read/audio acceptance specification;
- Quiet promotion of a ninth T09 tourist unit or importing the draft/queue into learner source code.

This gate intentionally needs a **new, explicit, reviewed contract** when content actually receives human approval; no boolean flip can confer certification. The prior B-03 T02/T03 packet and its source-anchor/protected-Speak guard still run independently and unchanged.

**Unchanged release safeguards:** 26 original lessons / 482 inherited items / 455 original MP3s; 14 restricted Speak references; one Numbers 1–20 source with optional 1–10 / 11–20; A-05 per-unit/mode factual attempted practice/Resume/v1 local backups; Home core cursor, family XP/privacy/consent, offline storage and non-labelled internal 3×3 journey styling. No physical, native acoustic, paid inference, personal content migration or production deployment performed.

## 5. Next engineering action after certification

Do **not** add further source-only tourist modules simply to increase count. The next highest-value effort is getting native language and voice reviews completed for **T02, T03 and the first two-way restaurant/shop exchange**, then reintegrating those reviewed assets with checksums. The T09 packet can move to a human native Polish reviewer alongside them. Until then, the app should continue to offer **exactly eight** source-backed tourist modules; it must not label these modules native-approved or pronunciation-mastered.
