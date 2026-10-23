# Path to Polish V2 — execution roadmap and learning programme decisions

**Owner decision: 2026-10-23.** This document is the current priority authority alongside the root `chat ai workflow.md`, `V2_REBUILD_PLAN.md`, `v2/DEFERRED_PHYSICAL_TEST_ROADMAP.md`, and GitHub issue #2. Later checkpoints override old historical TODO text. GitHub—not chat—is the source of execution continuity.

## Development execution order — locked

| Sequence | Workstream | Done when | Boundaries |
|---|---|---|---|
| A | **Learning experience and progression** | Exhaustive journey audit and prioritized P0/P1/P2 backlog, then coherent self-directed daily Learn/Listen/Read/Speak/Review path, course position, resume, next lesson and practice transitions. | **First action is audit and recommendations, not an unsolicited code/curriculum rewrite.** No arbitrary prerequisite gates or duplicated explanation/advice. |
| B | **Curriculum architecture and content quality** | Audit every existing lesson against conversational competencies and missing links. Agree a new three-phase course structure and a sequenced gap-fill plan, then author, validate and integrate the missing content. | Run audit/planning concurrently with A; do not create/generated lessons or change XP/IDs before review. New language examples/audio require verification. |
| C | **Family progression and engagement** | Group progress, weekly friendly recognitions and map achievements reflect the coherent core course without misrepresenting improvement. | No involuntary opt-in, fake pronunciation improvement, or required competitive route. |
| D | **Production reliability, privacy and security** | Deployment-ready family service, tested email/recovery, age-appropriate guardian consent, retention/deletion and recovery, encrypted off-host backup, monitoring and incident controls. | Can prepare in parallel. No real accounts or deployment claim until approved operational gates. |
| E | **Pronunciation calibration and physical release validation** | Real representative Polish speaker/learner evidence, human-rated grading, native review of corpus, real mobile Safari/mic/offline tests, production cutover/release. | Real-provider, paid inference and physical testing **remain explicitly deferred**. Continue synthetic safety tests now. |

**Priority rule:** Stop repeated styling micro-tranches unless there is a specific usability/accessibility defect. A & B now outrank cosmetic cleanup; B's curriculum audit can be included in A's first audit so the plan is coherent.

## A-00 / B-00 source audit deliverables (2026-10-23)

This audit is the **first action** under the locked execution order, not a rewrite of the learner app.

- [Phase A source-backed learning audit](PHASE_A_LEARNING_AUDIT.md): 24 prioritized P0/P1/P2 improvement findings, exact React/progress/review/personal-set evidence, acceptance criteria, and independent A-01..A-06 implementation PR sequence.
- [Comprehensive curriculum gap map](CORE_CURRICULUM_GAP_PLAN.md): all 26 active V2 lessons and 482 items dispositioned individually; existing source audio/protected references, conversational mode coverage and gaps, and provisional **Tourists T01–T12 → Extended Stay E01–E10 → Living in Poland R01–R10** functional course units.
- Current Library's sound/first-word/vocab/sentences/reading tracks are source-kind browsing categories, **not the conversational unit order**. Home resumes the last visit; Listen/Read authoring exists; actual Speak mode on reading dialogue is absent. Existing personal sets have a correct separate Library section and lesson IDs but are included in aggregate activity counters and can replace Home's last active lesson. These are implementation facts, not assertions that production is broken.
- Core progression design must maintain a **separate course map and evidence** from Library stage filters, local practice and personal imported lessons. No compulsory lesson unlocks, no professional Polish track, no false speech grades and no unapproved new recordings.

**Next owner decision:** review course phase outcomes and priority order. Then implement `A-01/B-01` stable manifest, independent Home-core resume and source-referenced tourist pilot, each under four final-PR-head CI lanes. Physical tests, live provider calls and native audio/editorial sign-off still deferred.

---

## The intended CORE language programme — owner-approved product direction

The V1 library was a collection of topics, **not** an intentionally sequenced course. Do not re-label its legacy Fundamentals → Basic → Learning *content buckets* as proof of a coherent course. Design the course around useful, spoken everyday Polish and short realistic exchanges for an **English-speaking learner**, **not Polish for professional communication**.

These are **COURSE PHASES**, distinct from delivery workstreams A–E:

1. **Polish for visiting tourists** — essential polite interaction, greetings, pronunciation that makes words understandable, introductions, numbers, ordering, tickets, getting around, directions, immediate needs, and short travel encounters. Exit: comfortably initiate/respond in common tourist situations using Listen, Speak and accessible Read.
2. **Polish for an extended stay** — repeatable everyday transactions and follow-up questions: accommodation, shopping beyond a single purchase, food preferences, pharmacy/appointments, dates/times, transport disruptions, social plans and ordinary small talk. Exit: handle predictable short exchanges with follow-up questions and read brief practical Polish notices/messages.
3. **English speaker living in Poland** — ordinary independent day-to-day life: neighbours/friends, home and maintenance, services, deliveries, healthcare, everyday administration, school/family contexts where relevant, community conversations, and longer informal dialogues/messages. Exit: sustain understandable, useful everyday interaction; **exclude professional Polish fluency as the aim**.

**Pedagogical structure:** progressively scaffold sounds → essential words/expressions → short utterances → two-way exchanges → authentic listening/reading. Each course unit has a real-life communicative outcome, prerequisites for suggested order (NOT locked access), reusable phrases and review loop. Spoken/listening comprehension and conversational reading take precedence over abstract topic vocabulary drills; Speak attempts remain user-directed and ungraded until validated. Track suggested mastery with honest evidence (self-recall != pronunciation proficiency).

**Course progression is separate from library browsing.** Core `coursePhase / unit / lesson order` (or equivalent versioned editorial mapping) must not silently overload historical `curriculum.stage` values that are currently Library presentation filters or progress/XP identifiers. Keep original lesson/item IDs and audio paths stable, keep existing 26/482 originals, the original Numbers 1–20 single lesson and its 1–10/11–20 *optional sessions*, and 14 excluded pronunciation references.

**Personal / custom learning sets — distinct product lane:** Learners can create, edit, import/export and practice their own sets, but these belong to **Your lessons** and never enter or reorder the core course automatically, create course-completion evidence, alter recommended core lesson links, or secretly acquire canonical curriculum placement. Personal sets can retain independent per-item practice history; whether they contribute local XP continues according to existing policy, but must not counterfeit verified course milestones. Optional explicit copying into personal collections does not mutate protected originals. Keep content authoring readily accessible without dominating the core learn path.

## What happens next

**A-00: evidence-led learning + curriculum audit.** Read active `App.tsx`, `library-curriculum.ts`, `lesson-resume.ts`, `review.ts`, `progress.ts`, `model.ts`, Speak/Read/Listen and existing Playwright contracts. Inventory `v2/content/library-catalog.json`, `LIBRARY_CURRICULUM_AUDIT.md`, source-linked audio/reference safeguards, and **each existing set**. Deliver `v2/PHASE_A_LEARNING_AUDIT.md` (detailed journey issue register and P0/P1/P2 acceptance/test/PR slice plan) and `v2/CORE_CURRICULUM_GAP_PLAN.md` (all 26 IDs classified keep/reuse/supplement/defer/lab, phase placement, holes and curriculum sequencing). Explicitly distinguish *code-proven finding*, *source-editorial inference*, *requires native review*.

**A-01 onward:** implement audit-backed improvements in coherent independently CI-certified PRs; no new course mechanics/scoring/XP formula before review. Content gap-fill uses separate editorial/content tranches after decisions; missing Polish examples/voices are proposals, not unverified production lessons.

**Acceptance:** four GitHub Actions final-head lanes PASS before code merge; docs-only audit work stays reviewable in GitHub and updates issue #2/root workflow. No actual Safari/device/audio/provider tests, native Polish linguistic validation or public deployment implied.
