> **Later extension (2026-10-23):** This page describes the **original T01–T03 pilot**. T04 and T05 have been added in a separate source-only tranche; consult [T04/T05 source audit and remaining gaps](TOURIST_T04_T05_SOURCE_PILOT.md). Original T01–T03 source references and missing content gates are unchanged. The section below retains original pilot evidence.

# A-03 / B-02 — First tourist conversation-unit pilot

**Owner-facing goal:** build a coherent learning path from recorded original material before commissioning new native-reviewed dialogue. This tranche is intentionally a **small, source-referenced, partial** slice. The complete [curriculum gap plan](CORE_CURRICULUM_GAP_PLAN.md) remains editorial authority for missing units. No professional language, no nine-tier labels, and no invented native voice.

## What is integrated

Versioned, editorially draft `v2/content/tourist-units-v1.json` maps **three functional tourist units** to **only existing fixed item IDs** within the 26 original lessons. UI exposes normal unit names and source-backed **Listen / Speak / Read** actions in a compact area of `Your path`; this is distinct from the tiny, owner-approved, unlabeled 3×3 journey icon on lesson cards. No tooltip/hover explanation/legend/tier narration.

| Unit | Real material | Available steps | Known limitation |
|---|---|---|---|
| T01 Greetings and polite replies | `Basic_01R:0,1,4,5` and `Conversation_1:0,2,8,12,20` | Listen (2 recorded turns), Speak (5 source phrases), Read (4 source lines with authored questions where present) | Original recorded/text material not separately native certified; clarify/repair variants still limited |
| T02 Introductions and names | `Basic_01R:2,3`; `Conversation_1:23` | Listen (2 recorded turns), Speak (existing question), Read (2 original lines) | First-person spoken name reply `Conversation_1:25` remains **practice_only**, not reintroduced as a scored or purportedly verified reference |
| T03 Numbers, prices and payment | `numbers_1-20:0..9`; `Conversation_-_shopping:0,1,2` | Listen (numbers 1–10), Speak (price and card-payment questions) | **No Read step**: existing corpus lacks a coherent numbers+prices reading/transaction text. New native-checked source needed before publishing that activity |

All example counts refer to **existing item references**, NOT newly created lesson items, XP sources or copied recordings. Reusing one item across different modes preserves original item ID, unique completion guard, backend sharing policy and existing XP calculation; entering or switching unit activities does not itself award XP. Existing Learn/Speak pronunciation is optional and uncalibrated; all 14 historical practice-only exclusions continue to apply.

## Behaviour and implementation contract

- `v2/frontend/src/tourist-units.ts` validates manifest schema/sequence, exact reference uniqueness and within-lesson ascending order. Missing source lesson/item/audio, `practice_only`, personal sets and unsupported mode **fail closed**; no missing step is replaced with generated audio/phrases. The normal Library remains usable even if the draft unit cannot run.
- `TouristUnitCards.tsx` displays short ordinary unit titles and *real actions*, without visible phase/tier classification. All 26 original lesson cards remain searchable and browsable, and personal sets remain independent.
- Clicking one action launches a **temporary item subset** from the original lesson and selects its already supported mode. This is an explicit learning practice session, not a new canonical lesson record. A completion panel can advance to the next source-backed step; no artificial proficiency or hard unlock. Manually changing mode returns to normal full-lesson practice.
- Temporary activity context clears when navigating away, opening another normal lesson or visiting focused sound practice. It is **not persisted as fake course mastery**. Current Home A-02 core continuation remains lesson-based; source items are still tracked by existing progress/review keys.
- The existing full Numbers 1–20 lesson retains its voluntary **1–10 / 11–20** practice groups in ordinary mode. T03's recorded 1–10 subset is an additional optional tourist exercise, not a rewrite of that source or a 1–8 batch.
- `unit-practice-head` is compact progress context inside the active session; no technical course tier text is displayed. Speech capture permission is never triggered by navigating the unit. Live assessment remains guarded by existing consent/source/provider checks.

## Next content and quality work (NOT part of this PR)

- Native editorial QA on all referenced phrases/dialogues, English translations, registration (pan/pani and pronoun alternatives) and source recordings. The code validates source identity and availability, **not accent/linguistic correctness**.
- T02: obtain a complete verified personal-introduction reply/audio, rather than promote ellipsis `Conversation_1:25` to gradeable.
- T03: author and review short prices/quantities transaction and its recorded replies + practical price-sign reading before adding a Read activity. Do not falsely equate numbers list listening with understanding a spoken full price.
- T04–T12: expand coherent scenarios one small verified tranche at a time with real source-grounded listen/roleplay/reading. A subsequent step can add optional unit-level return/resume evidence only when tested, without conflating XP with competency.

## Certification

Unit tests cross-validate the draft references against original JSON source rows, audio eligibility, missing assets/practice-only failures and invalid manifests. Browser tests prove all three entry points, T01 Listen/Speak/Read, T02 authored comprehension handoff, T03 honest lack of Read, existing Numbers groups, 320px layout and preserved original Library. Four CI lanes at final PR head are required before merging. Real devices, native Polish/acoustic assessment, paid providers and public release remain deferred.
