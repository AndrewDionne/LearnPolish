# C-12 — Authoritative first-word → basic-vocabulary → first-sentence progression

**Curriculum owner decision:** Within Journey 1 fundamentals, the content sequence is **First words → Basic vocabulary → First sentences / basic grammar**. Alphabet/letter combinations and sound-recognition fundamentals remain available before this sequence. These are normal **instructional headings** requested by the owner, NOT the app's hidden three-by-three journey tier indicators; never add accessibility labels or hover legends for the internal position-tier scheme.

## Actual learner sequence

| Learner stage | Existing source-backed exercise | Material |
| --- | --- | --- |
| **First words** | Yes and no (2), Polite essentials (3), Hello and goodbye (3) | **8 original item IDs**, primarily one-word expressions (two recorded greetings are two-word phrases) |
| **Basic vocabulary** | Street and place words (6), Getting around: first words (6), More everyday replies (5) | **17 original item IDs**, 12 lexical nouns, plus basic one-word replies and two existing short expressions |
| **First sentences / basic grammar** | Simple food requests (5), Questions in a shop (5), Asking where things are (5) | **15 original complete recorded short expressions / questions** |
| **First sentences / basic grammar — understand the pattern** | Polite requests, Where, Permission, Negation, One/two | **20 recorded source examples** (some intentionally overlap focused exercises), with five short grammar observations and optional whole-sentence listening-comprehension checks |

The basic vocabulary stage now starts with words before longer question/requests; latter original C-06 source groups have **not** been deleted or resynthesized, but are taught alongside the actual first-sentence material. **There are still exactly 40 distinct original C-05/C-06 source item IDs across three visible stages**, not 40 new recordings; the C-11 20 grammar examples may overlap source rows. Original English/Polish/MP3/XP progress remains tied to stable source IDs, not presentation location. No migrated review/proficiency data.

**End-to-end progression:** Completing the first word groups leads to the street/transport/everyday vocabulary groups, then to the short food/shopping/location sentence practice groups. Completing the last short-sentence group opens **Build your first sentences** with the first grammar pattern already expanded. Each source-group session still supports the existing **Learn, Listen, Speak** workflows; when Speak assessment is enabled, the owner's C-08 **complete recorded word/utterance → learner recording → one overall score and colour-coded Polish word text → Try again/Next** remains unchanged. The 20 original full recorded guided steps remain separately available below as **Complete recorded lessons**, without a reordered or shortened original source curriculum. Source selection still cannot advance the Home course cursor. The optional 1–10/11–20 practice slices do not truncate full Numbers 1–20.

### Integrity and QA

- [The deterministic stage ordering helper](frontend/src/foundation-progression.ts) accepts only source-verified C-05/C-06 groups, rejects unknown/duplicated IDs and returns three ordered slices.
- Existing [C-05 strict source manifests](content/foundation-first-expressions-v1.json), [C-06 strict manifests](content/foundation-next-words-v1.json) and [C-11 original grammar examples](content/foundation-sentence-patterns-v1.json) are **unchanged**.
- [Journey 1 guide](frontend/src/Journey1Guide.tsx) has exactly three ordinary learner headings in this order. Familiar existing navigation/testing selectors are preserved for original group panels; full sentence groups get their own recognizable entry points.
- [App](frontend/src/App.tsx) now computes session handoff using this same ordered curriculum, not source file order. After the last focused sentence group, a **Next: First sentences / basic grammar** button opens the original C-11 grammar component in the Library. No new sound files, provider interactions or progress records are created.
- Unit tests assert all 8 + 17 + 15 original source IDs remain **40 distinct references** and reject shadow/unknown groups. Desktop/mobile Playwright verifies the visible three-section order, original 26 source lesson tiles, valid Learn/Listen/Speak modes and the actual last-group → grammar handoff at 320px.

**Remaining substantive gap:** Stages are now linear, but the **actual instructional minute ratio** (the owner's target is about **80% fundamentals and basic vocabulary in Journey 1**) remains unmeasured. The existing 16/4 guide step split is a count of scheduled entry points, **not real learner teaching minutes**. C-02's unpublished new phonetic and lexical material remains behind native review and exact licensed full-word audio, [issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140). Physical microphone, paid voice-provider response quality and native/acoustic curriculum approval are not certified by CI. Next content work should expand genuine high-frequency word/phrase coverage and elementary grammar **with properly matched whole-word recordings**, not invent syllable-only audio or another empty scaffolding system.

**Certification gate:** Final PR head must pass all 4 existing CI lanes: frontend source migration/types/unit/build + desktop/mobile/audio/offline/a11y browser, connected-family browser, backend and benchmark before merge.
