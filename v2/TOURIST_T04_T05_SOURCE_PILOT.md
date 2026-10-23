# B-04 — Tourist practice T04 and T05, original-source-only expansion

**Status:** implementation candidate pending four final-head CI lanes. Source baseline: GitHub main `b411262120052e2aef2f5499b7069c4fa5257c9f`, certified A-04 review [PR #127](https://github.com/AndrewDionne/LearnPolish/pull/127). This is **not** a newly authored or native-speaker-approved restaurant/retail dialogue.

## Why T04/T05 can be practiced now, and what remains missing

All source references below point to previously checked-in Polish/English rows and inherited individual MP3s. The **existing source identity and audio presence** are machine-verifiable, but this is not independent verification of pronunciation, cultural register or native acoustic accuracy.

| Unit | Source-backed activity | Precise item IDs | Honest scope and withheld content |
|---|---|---|---|
| **T04 — Ordering food and drinks** | Listen common orders / polite restaurant phrases from `Food_and_Dinning`; Speak a subset of `Conversation_-_restaurant` requests. | Listen `:0,:1,:3,:5,:6,:9,:10,:17,:18`; Speak `:0,:2,:3,:4,:7,:20,:21,:24` respectively. | Source-only **individual phrases**; **no Read**, no claimed complete waiter/guest exchange, no invented waiter replies or unreviewed native dialogue. Protected `Conversation_-_restaurant:1,5` and `Food_and_Dinning:2,4` never enter the activity. |
| **T05 — Shopping for groceries** | Listen/Read first six original `Grocery_store_very_basic_shopping` passages; Speak `Conversation_-_shopping` questions/requests. | Listen + Read grocery `:0–:5`; Speak shopping `:0,:5,:8,:20,:23,:24`. | Opening grocery turns include a **quantity and apple choice**, not the incomplete price/payment passage; these six source turns are not independently native certified. No new spoken shopkeeper price, reliable clerk payment response or newly approved price reading. T03 therefore **remains** without its missing integrated price/quantity/payment Read workflow. |

**T01–T03 remain bit-for-bit identical in the five-unit v1 metadata extension.** T03's full price listening/response gap remains open in [issue #126](https://github.com/AndrewDionne/LearnPolish/issues/126), alongside T02's complete first-person introduction. T04's restaurant story and T05's coherent cashier response similarly require actual editor/native/audio review before being called complete.

## Learning flow

The Library's **Your path** now offers five short unlabeled-internal-tier topic cards. T01–T03 remain internal Journey 1 / beginning; T04 and T05 are Journey 1 / middle. The 3×3 colour+icon hierarchy is only internal and remains invisible, without tooltip, spoken label, explanatory legend, or public tier title.

Each card exposes only the modes for which a particular **complete existing recording and original item** are available. Clicking uses the unchanged `openTouristUnitStep` temporary subset, existing Listen/Speak/Read controls and optional next-mode handoff. Temporary tourist source sessions no longer override an **already selected** Home core continuation: T05 reads a source tagged Journey 2 but still belongs to the optional Journey 1 tourist path. The source lesson can remain normal Recent practice. First-time course positioning remains lesson-evidence-derived until a separate unit-level position design is certified. The source `numbers_1-20` remains exactly one lesson with voluntary 1–10 and 11–20 sections. Ordinary Library actions, user-authored sets, Home core continuation, source-keyed progress, XP/consent/family, offline caching and review scheduling do not change.

## Fail-closed and regression contracts

- `v2/content/tourist-units-v1.json`: exactly ordered T01–T05, unique mode per unit, no invented files, sorted original item IDs, `editorialStatus=source_refs_only_native_review_pending`. No standalone new lessons, IDs or asset copies.
- `v2/frontend/src/tourist-units.ts`: reject unsupported mode, absent recording, missing item/lesson, personal or `practice_only` sources, malformed sequence, unexpected order/position or duplicated item reference. Unavailable units disappear safely while all normal Library sets remain accessible.
- Unit tests pin key exact original Polish and English anchors; fixture protections cover all 14 source blockers, missing audio, source replacement and T04/T05 partial modes. Browser tests check 5 units, 13 actual Listen/Speak/Read buttons, source-backed listen reveal, no fictitious restaurant Read, grocery Listen/Read/Speak, independent Library navigation, 320px overflow, existing T01–T03 and Numbers practice.
- The existing 26 original curated/built-in lessons, 482 original rows and 455 imported MP3 files remain unchanged. No speech scorer, AI credit, certification badge or completion/competence inference is added.

## Source review and next decisions

Human reviewer must confirm the actual Polish and voice/translation match and supply a complete restaurant response/story for T04 and a seller response plus contextual shopping practice for T05. If previously recorded material is unreliable, repair via a separate native-reviewed re-recording and a versioned content promotion, never by unprotecting blocked items or fabricating a grade.

For T02/T03 priority and complete transaction dialogues, see [issue #126](https://github.com/AndrewDionne/LearnPolish/issues/126) and [B-03 native/editorial handoff](TOURIST_T02_T03_EDITORIAL_REVIEW.md). Subsequent B-04 work should prepare **T06 directions and travel** from equally source-locked data, then seek human acoustic/editorial review. Physical iPhone/Safari, real mic, cloud pronunciation calibration and production rollout are still deferred.

## Merge contract

All **four** final-head V2 CI jobs must pass: frontend TS/Vitest/content/build/desktop+mobile+a11y/offline/audio, family-connected browser, private family backend and offline benchmark harness. A passing CI certifies the software mapping and synthetic workflow, **not** the editorial or native-acoustic suitability of each recording.
