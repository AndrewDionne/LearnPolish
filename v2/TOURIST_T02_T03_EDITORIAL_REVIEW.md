# B-03 — T02/T03 native-review and recording handoff

**Status: editorial draft, not approved learner content (2026-10-23).** Source of truth: `v2/content/tourist-editorial-review-v1.json`. Read with `v2/TOURIST_UNIT_PILOT.md` and `v2/CORE_CURRICULUM_GAP_PLAN.md`. This package deliberately adds **no user-visible lessons, written Polish targets, recordings, audio calls, new XP or assessment eligibility**.

## Decision and factual source audit

The shipped source-only tourist pilot has T01–T03. T02 currently uses `Basic_01R:2,3` for Listen/Read, but the only spoken greeting/question in its Speak step is `Conversation_1:23`. Reading text `Basic_01R:3` says *Mam na imię Andrew.* ("My name is Andrew.") and has original imported audio; it is **not** a generic dynamically personalized recorded name reply or a reviewed phrase-level Speak reference. The source vocabulary `Conversation_1:25` is the unfinished *Mam na imię…*; it remains **practice_only**. Don't silently substitute the reading example or unprotect the ellipsis.

T03 currently plays the original numbers 1–10 and lets a learner practice `Conversation_-_shopping:0,1,2`: *Ile to kosztuje?*, *Ile to razem?*, *Czy mogę zapłacić kartą?*. These are buyer questions, **not** a recorded price from a clerk, a spoken quantity, a clerk's answer about card payment or a usable short price sign. A contextual Read step is correctly absent. Numbers 1–20 remains **one full lesson** with optional 1–10 / 11–20 practice sessions.

Original 26 lessons / 482 items / 455 preserved MP3 files, all protected Speak references and the current family/consent/offline/progress rules are frozen. Source file presence and exact text identity do **not** establish native acoustic, semantic or translation approval.

## Human editorial decisions and minimum deliverables

| Unit | Review outcome required | Important edge cases |
|---|---|---|
| **T02 — Introductions** | One natural two-turn name introduction (question and **complete spoken reply**), fixed Polish/English per recorded utterance, register decision, and reviewer-approved recording(s). The user must be able to hear, answer and read the same real exchange. | Informal vs `pan`/`pani`; a name must not be treated as a universal learner response; exact audio/text matching; incomplete `Conversation_1:25` stays excluded until explicitly replaced via a reviewed new item or otherwise repaired with migration. |
| **T03 — Prices and payment** | Short buyer/clerk scenario with clear **quantity, actual price and payment response**; audio that says the exact quoted value; a brief everyday price-sign/receipt/menu example with a written comprehension check. | Polish złoty/grosz inflection, numerals vs spoken amount, currency pronunciation, natural quantity phrasing, card acceptance vs mere buyer question; consistent speaker turns and translated amount. |
| **Both** | Named native-Polish linguistic reviewer; second acoustic check against every final recording; English translation and register check; rights/provenance and licence; stable source IDs; scenario/mode QA in desktop/mobile/offline/connected family suites. | No fabricated provider scores, no implication that a T02/T03 step is native-certified just because a legacy MP3 exists. |

The packet lists **original source snippets only**, not proposed approved Polish. Human reviewers should supply the *exact* new authored lines, translations, turn order, context, target audience/formality, currency/numeric formatting, per-line recording (or independently verified reuse), voice/licence provenance, reviewer identities and sign-off. The owner can first approve the pedagogical content before purchasing/recording any new voice assets.

## Integration contract after actual human review

1. **Editorial submission:** commit a separate reviewed-content candidate with source/author attributions and versioned IDs distinct from the protected original rows. Human review signs off the Polish, English, conversational naturalness, inflection and scenario/turn consistency. This current draft packet never acts as an approval flag.
2. **Audio submission:** commit/associate only licensed per-utterance clips with matching exact transcript, recording provenance, audible review evidence and checksums. No unapproved TTS synthesis or automatic replacement of protected MP3 bytes.
3. **Mode assembly:** source-backed Listen comprehension should ask about the **actual price or response**, not just numbers 1–10. T02 gets a **complete** learner answer and genuine reply. T03 Read appears only when authentic reviewed contextual text and questions exist. Preserve existing canonical personal/source separation, original IDs, XP, consent, offline and Numbers batch policy.
4. **Certification:** regression of exact item/audio identity, protected 14-source gates, phrase alignment, Listen/Read/Speak entry/handoff, 320px touch UI, keyboard/axe, no synthetic sound, browser offline, family permissions and private backend. All four final GitHub Actions CI lanes must pass at the **final PR head** before a recommended merge. A CI pass certifies software wiring, not linguistic correctness.
5. **Remaining release gates:** independent native-acoustic acceptance, actual iOS/Safari playback and real microphone/AI calibration remain owner-deferred. Do not claim release readiness on this tranche.

## Automated draft integrity gate

Run from `v2/frontend`:

```bash
npm run test:migration
# Or the isolated draft gate:
node scripts/tourist-editorial-gate.mjs
node --test scripts/tourist-editorial-gate.test.mjs
```

The check asserts that both work items remain **unpublished**, every listed Polish and English snippet matches an exact checked-in source row, protected `Conversation_1:25` remains classified correctly and does not enter T02 Speak, and T03 has no unapproved Read activity. Adding a field resembling new recordings or marking the draft approved is **rejected**. A future approved content model requires an explicit separate version and tests.

## Next after this tranche

Request T02/T03 transcript and audio editorial review, log concrete reviewer feedback and resolve both gaps. Only then expand into natural recorded tourist **T04 restaurant** and **T05 shopping** scenarios, reusing original source where appropriate. Curriculum opportunities for everyday dates, transport clarifications, accommodations and resident listening/reading remain in the audited B-00 gap plan. This is intended to avoid a cosmetic task cycle while real course quality still has missing content.
