# A-01 / B-01 — quiet core journey foundation

**Status:** conservative first implementation based on the owner-approved [execution order](EXECUTION_ROADMAP.md) and the [A-00 learning audit](PHASE_A_LEARNING_AUDIT.md) / [curriculum gap plan](CORE_CURRICULUM_GAP_PLAN.md). This is **not** a complete 32-unit course or native-validated corpus.

## What this tranche actually ships

- New authoritative, versioned **`v2/content/core-journey-v1.json`** contains only 20 existing source-backed course placements. Each record references a stable existing `lessonId`, a `journey` (1, 2, 3), a private `position` (`beginning`, `middle`, `end`) and deterministic order **within that position**. It does not duplicate or rename any item or lesson, invent an audio reference or claim graduate competence.
- The pilot currently has **17 Journey 1** and **3 Journey 2** source lessons. **Journey 3 deliberately has no records yet**: no verified existing resident-life reading/conversation corpus supports honest placement. Likewise Journey 2 End is empty. The 3×3 API/icon set supports all nine combinations, but no fake courses/content are shown.
- **Six original built-ins** remain under `Explore more`: `Road_Terminology`, `Districts_of_Warszawa`, `The_Cities_of_Poland`, `Names_of_Poland_1`, `Countries_of_the_World`, and isolated `speak_swietokrzyska` pronunciation lab. All 26 sets remain available and searchable.
- The Library no longer exposes outdated **Fundamentals / Basic / Learning / Practice stage headings or filter buttons**. It shows **Your path** in source-grounded suggested order, **Explore more** for supporting/optional topics and **Your lessons** only when personal sets exist.
- Core cards receive **purely decorative** subtle markers: colour family for journey 1/2/3; open circle / centre-dot / check-circle for beginning/middle/end. **No hover info, accessible tier copy, tooltip, aria label, title or nine-stage legend**, per owner. Actual lesson titles/descriptions/controls remain ordinarily accessible; completion, access and error states are independent of the icon.
- Source-backed **Next** recommendations use the pilot core ordering rather than the old alphabetical topic/stage walk. For example the `Conversation_1` greeting lesson suggests `Basic_01R` next, not general shopping. Optional and personal source lessons have no automatic core successor.
- Existing Home **Continue** remains last activity for now, not yet course resume. That is the separately scoped **A-02** implementation; avoid claiming otherwise. Existing library source `curriculum.stage` is retained as metadata for legacy compatibility and past backup keys, not rendered as named course tiers.

## No change to learning evidence or personal data

There is **no XP/review/scoring/lesson item/MP3/assessment/provider logic change**. Keep one original Numbers 1–20 lesson with its optional 1–10/11–20 sections, all 14 `practice_only` Speak references, 455 inherited MP3 assets, the original 482 item IDs, 26 built-in sets, editable/importable/exportable personal lessons with independent practice, group privacy and offline backups. A course placement is an editorial **suggestion**, not a mastery judgment or locked route.

## Validation contract

- `src/core-journey.test.ts`: exact active-source catalogue membership (20 mapped / 6 unmapped), no duplicate IDs or positions, deterministic journey order, deliberately empty resident slots, personal source exclusion even with forged metadata, and fail-closed schema parsing.
- `src/JourneyMarker.test.ts`: all nine theoretical combinations render distinguishable shapes and journey colour classes and are hidden from assistive-tech announcements, without hover/tooltip labels.
- `e2e/core-journey.spec.ts`: all 26 source lessons accessible, 20 silent icon marks, first greeting card, no stage filters/labels, exclusions for optional/lab, personal import/create isolation, and 320px mobile layout. Existing `learning-next-lesson` now expects real course-adjacent greeting reading rather than mismatched shopping; special Numbers 1–20 sections unchanged.
- **Gate:** four CI lanes green on final pull-request head before squash merge. Physical Safari, actual language and MP3 native verification, paid/private speech-provider calls, final icon aesthetic approval and public deployment remain separate/deferred.

## Next independent work

**A-02:** Core continuation separate from most recent personal activity. Introduce a small honest Core Continue button/position derived from existing item events, preserving backups and personal flow; then graduate to genuinely coherent situational **units**, not merely whole legacy sets. **B-02:** Draft and validate actual T01–T03 lesson-item links in the course manifest, flag missing dialogue components and require native review before new Polish text/audio becomes production content. No fabricated completion credit.
