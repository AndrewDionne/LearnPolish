# B-09 — T02–T05 two-way dialogue review and recording packet

**Status: Unapproved human-editorial candidate material, NOT a language/audio sign-off.** B-08 certified base `a701793a0d8c26da6e9d09be7bab9c9ff00cad69`. There are **no new audio files** and **no new learner units** in B-09.

## Why this tranche exists

The source-backed T02–T05 learning units currently contain individual Polish phrases or incomplete slices of recorded dialogues. The missing capability is to listen to, understand and answer a **coherent exchange** with another speaker using natural replies. We cannot call original isolated phrase clips a vetted two-speaker encounter, and an unreviewed model-authored Polish script is **not a suitable recording or scored Speak target**.

The new [review packet](content/tourist-t02-t05-dialogue-drafts-v1.json) supplies a fixed and printable draft for an independent native speaker to correct. Every Polish and English line remains provisional, every audio entry is `null`, and all six review flags per unit remain false. The provisional `T0x-Dxx` labels are **editorial row IDs**, not source-item identifiers.

## The four candidate scenes

| Unit | Native reviewer issue | Draft conversation | Draft turns | Source anchors | Fictional written comprehension |
| --- | --- | --- | ---: | --- | --- |
| T02 | [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) | Ola and Marek introduce themselves informally in a class; fixed learner-name example, hometown, polite close | 8 | `Basic_01R:2,3`; protected `Conversation_1:25` | Short classmate introduction; who comes from Canada? |
| T03 | [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) | Customer buys two fictional water bottles at 4 zł each; cashier says 8 zł and confirms card payment | 8 | `Conversation_-_shopping:0,1,2` | Fictional written price list: one water 4 zł, two 8 zł |
| T04 | [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) | Customer and waiter: table, menu, tomato soup, water, bill | 10 | `Conversation_-_restaurant:0,2,7` | Invented menu with tomato soup and water |
| T05 | [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) | One kilogram of fictional red apples; seller answers with price, card and receipt | 10 | `Grocery_store_very_basic_shopping:1,2,6,7` | Example 10 zł/kg apple price and checkout receipt |

**Key source distinction:** `Grocery_store_very_basic_shopping:6,7` already contains a recorded price/payment response, and that original source remains untouched. B-09 does not pretend the new ten-turn draft has corresponding audio. The original `Conversation_1:25` incomplete name reply remains **protected** and is only a negative/contextual source anchor, never a scored Speak utterance.

### Print or inspect the complete 36-turn reviewer sheet

From the GitHub repository root:

```bash
cd v2/frontend
npm run test:migration
node scripts/tourist-dialogue-review-gate.mjs --review-sheet
```

The second command prints the candidate Polish, English, speaker, written Read, questions and reviewer decisions to stdout. It neither creates audio nor opens an AI provider connection. The source JSON is fully versioned and remains the authoritative author draft for feedback.

## Native language, recording and reading acceptance

A Polish reviewer **must correct or approve each exact line** and English equivalent, register, role, numerals and inflections before voice rendering or scoring. Specific high-risk items:

- **T02:** `ty` is an informal exchange between two fictional peers; any formal `pan/pani` form must be a **separately approved fixed recording**, not a slash-separated pronunciation target. `Ola` and `Marek` are example names, **not** a user's personal details or learned identity.
- **T03:** verify `cztery złote` and `osiem złotych` as spoken numerals, exactly reconciling 2 × 4 zł = 8 zł, cash/card response and a comprehensible original receipt. The sample price is not current vendor pricing.
- **T04:** review waiter/guest service register, turn-taking, an actual order and the bill, then contextual menu reading. The draft menu is fictional; it is not an authentic restaurant listing.
- **T05:** review `kilogram czerwonych jabłek`, seller variant/quantity replies, price and card response, consistent 10 zł/kg on the sample receipt. Coordinate the recorded amount and payment grammar with T03's separate script.

After native text/translation approval, define **new stable canonical lesson/content IDs**, not the `T0x-Dxx` draft labels. Record every approved, full utterance with **two distinct properly licensed speakers** (guest/staff or both classmates), an exact text hash, original recording SHA-256, voice provenance/rights and second listening reviewer. Check natural Polish cadence, final syllables, numeric stress, no clipped endings and whether the file says *exactly* the approved text. Zero recordings exist in this PR; there is **no** generated audio manifest and no approval inferred from a plausible transcript.

Approve new contextual Listen prompts and Read questions **against the actual recorded and written sample**. The four current fictional written snippets and answer keys are reviewer candidates, **not scored learner material**. Only the later **separate** native-reviewed source/audio PR may introduce new assets/lessons, after full source-integrity and four-lane CI. The existing T02–T05 units retain only their original source-based buttons until then.

## Build/runtime protection

`v2/frontend/scripts/tourist-dialogue-review-gate.mjs` and its regression tests run within mandatory `npm run test:migration`. The gate locks source anchors to original `docs/sets` IDs, checks the protected `Conversation_1:25` classification, checks the 36 fixed editorial rows, speaker alternation, four fictional written answer anchors and human acceptance checklist. It fails on invented audio filenames, an approval flip, wrong GitHub blocker, a missing row, a shifted speaker role, a new live ninth unit, learner import of this packet, fabricated Read source, or changed original anchor. The B-03 and B-08 review gates remain independent and effective.

**Existing runtime remains completely unchanged:** T01–T08 eight source-backed tourist units, 22 activity buttons; 26 original legacy lessons, 482 rows, 455 MP3s, 14 protected Speak references, Numbers 1–20 with optional 10+10, A-05 factual unit activity/Resume/backup, chosen Home core cursor, family XP/privacy/consent and offline. Internal three-journey tiers remain visual-only, without added text/hover/accessibility descriptions. No public source data, audio provider, microphone, production app or physical device changed.

## Next real action

Share the printed sheet or JSON with an independent native Polish reviewer; get feedback **line by line**, version the corrections and only then authorize appropriately licensed source recordings. Closest priority is **T02/T03** (pronunciation name response and realistic prices); T04/T05 follow with waiter and shopkeeper voices. Issues [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) and [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) remain open until approved *recorded* content and contextual Read are integrated. Physical iPhone/Safari, human-acoustic and paid inference work remain separately gated.

**Merge gate:** all four GitHub Actions lanes at the final PR head must PASS: frontend migration/TS/Vitest/build/full desktop/mobile/browser/audio/offline/a11y, connected family browser, private backend and benchmark. CI validates draft containment and software regression, **not Polish correctness or pronunciation quality**.
