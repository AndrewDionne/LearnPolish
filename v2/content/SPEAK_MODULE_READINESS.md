# Speak module readiness & owner priority tracker

**Catalog audited:** 20 October 2026, against `main` following PRs #73–74. This is the **normal V2 catalog**, not legacy menus. Recheck figures with `cd v2/frontend && npm run content && npm run audit:speak` after any lesson or pronunciation-data changes. This tracker is an owner prioritization document; do not interpret an empty owner-priority cell as approval to change learning content.

## Status means three different things

1. **Speak entry point:** ✅ YES for vocabulary and sound-contrast lessons (20 modules, 431 items). The 6 **reading** modules have `Read` only (51 items); their pronunciation groups exist but a learner cannot launch regular Speak in these modules.
2. **Original-text grouping data:** Every one of 482 items has an exact-concatenating sequence for colour display. **A = 1 authored**, **E = 23 editorial draft instances** from 19 word/phrase overrides, **D = 458 automatically generated orthographic draft instances**. None has been independently verified against a native-speaking Polish reviewer; the Świętokrzyska guide is itself marked `needs_native_speaker_review`. A coloured segment is a **Whisper transcription proxy**, never an acoustic syllable grade.
3. **Real AI operation:** **OFF for all modules on the public Free deployment.** Private adult-only local session requires a configured family API, both confirmed providers/free-plan guards, learner identity and distinct user-triggered Azure + Groq consent. There are no real provider recordings or pronunciation calibration across the training sets. A technically wired module is therefore **NOT live/certified**.

Legend below: `A/E/D` gives counts of authored/editorial-draft/automatic-draft groups; audio counts are normal listenable MP3 items; `Blocked` means the backend's current text proxy cannot parse the reference as one fixed Polish utterance (alternatives `/`, digits), and `Unfinished` is a technically parseable but incomplete ellipsis prompt. Owner priority is deliberately **unset** pending discussion.

## Vocabulary and ordinary Speak — 15 modules

| Module | Items | A/E/D | Audio | Blocked | Unfinished | Suggested first pass | Owner priority |
|---|---:|---:|---:|---:|---:|---|---|
| Speak test · Świętokrzyska | 1 | 1/0/0 | 0/1 | 0 | 0 | Baseline, then supply matching native audio | — |
| Conversation 1 (greetings) | 26 | 0/6/20 | 26/26 | 1 | 1 | **Foundations**; resolve `pan/pani` and name placeholder | — |
| Numbers 1–20 | 20 | 0/6/14 | 20/20 | 0 | 0 | **Foundations**; consonant/vowel distinctions | — |
| Road Terminology | 27 | 0/7/20 | 27/27 | 1 | 1 | **Foundations**; remove numeric and placeholder ambiguity | — |
| Conversation – shopping | 25 | 0/0/25 | 25/25 | 0 | 0 | Everyday conversation | — |
| Getting Around 1 | 26 | 0/0/26 | 26/26 | 1 | 0 | Everyday travel | — |
| Transit 1 | 20 | 0/0/20 | 20/20 | 0 | 1 | Everyday travel | — |
| Conversation – restaurant | 25 | 0/1/24 | 25/25 | 2 | 0 | Everyday conversation; split alternate forms | — |
| Food and Dinning *(source spelling)* | 25 | 0/0/25 | 25/25 | 2 | 0 | Everyday conversation; resolve `pan/pani` | — |
| Emergencies and Health | 25 | 0/0/25 | 25/25 | 4 | 0 | Useful but edit gender-alternative references | — |
| Numbers 20–100 | 36 | 0/0/36 | 36/36 | 0 | 0 | Vocabulary extension | — |
| Districts of Warszawa | 20 | 0/0/20 | 20/20 | 0 | 0 | Names and place stress | — |
| Cities of Poland | 29 | 0/0/29 | 29/29 | 0 | 0 | Names and place stress | — |
| Names of Poland 1 | 32 | 0/0/32 | 32/32 | 0 | 0 | Personal names (Whisper proper-noun bias) | — |
| Countries of the World | 68 | 0/0/68 | 68/68 | 0 | 0 | Larger, lower-frequency name catalog | — |

## Sound-contrast practice — 5 Speak modules

Each contrast module has a genuine recorded example for every item. The groups are practice exercises, **not isolated-phoneme recordings or verified acoustic minimal pairs**.

| Module | Items | A/E/D | Audio | Blocked | Suggested first pass | Owner priority |
|---|---:|---:|---:|---:|---|---|
| C · CZ · Ć (hard/soft CH) | 6 | 0/2/4 | 6/6 | 0 | **Core sound distinctions** | — |
| S · SZ · Ś (three SH families) | 6 | 0/1/5 | 6/6 | 0 | **Core sound distinctions** | — |
| Z · Ż/RZ · Ź/ZI | 6 | 0/0/6 | 6/6 | 0 | **Core sound distinctions** | — |
| L · Ł | 4 | 0/0/4 | 4/4 | 0 | **Core sound distinctions** | — |
| KRZY · PRZY consonant clusters | 4 | 0/0/4 | 4/4 | 0 | **Core sound distinctions** | — |

## Reading & dialogues — 6 modules currently **without** Speak mode## E2: first short dialogue practices inside existing reading lessons (2026-10-21)

### E2 comprehension pilot (2026-10-21)

The same THREE existing scene records now contain one **authored three-choice listening/reading comprehension check** each, focusing on how the second speaker is doing, the supplied name, and the colour of apples selected. In **Listen first**, Polish and English stay hidden until explicit reveal (or English after an answer), with selectable original turn recordings available throughout; feedback follows one answer without saving a score, claiming phonetic quality or awarding XP. Switching back to **Read dialogue** resets the temporary question while preserving original saved reading progress. No new passages, lessons, learner profiles, audio, API calls or family rewards. Both content migration and frontend schema reject malformed questions and ambiguous duplicate choices. Native human/voice review remains pending.



**Implemented pilot (pending CI):** three source-matched optional **micro-dialogues** are attached to two existing Reading lessons: `Basic_01R` has two exchanges of **2 turns** each (greeting/how are you; asking a name), and `Grocery_store_very_basic_shopping` has one **3-turn** apple purchase (Customer → Shop assistant → Customer). They use the exact original Polish + English + individual mapped MP3 recordings at the exact existing reading indexes; no newly generated or edited audio. The learner can see both speakers together, play any turn, switch to `Listen first` to conceal Polish until revealing, and optionally reveal the English translations. This is **additional practice inside the original reading lesson**, not an extra lesson, not automatically sliced reading passages, not true uninterrupted dialogue audio, and not pronunciation grading. The catalog remains 26 modules / 482 items / 51 reading passages, 6 reading lessons, 24 authored comprehension questions, 14 ungraded Speak reference blockers, and unchanged user progress/XP. Polish fluency and voice match await actual/native audio review. The next E2 extension should follow owner UX feedback and review of these actual scenes, not bulk creation of fabricated dialogues.



All 51 reading items have source audio and automatic pronunciation text groups (none editorial-reviewed), but `availableModes()` intentionally offers **Read**, not Speak. This is a **workflow absence**, distinct from normal vocabulary drafts needing review. Their often longer sentences may need a different, phrase-aware assessment experience, rather than turning on the current short-utterance Azure SDK route wholesale.

| Module | Reading items | A/E/D | Audio | Speak available | Owner priority |
|---|---:|---:|---:|---:|---|
| Basic 01R (foundational reading) | 6 | 0/0/6 | 6/6 | No | — |
| Grocery store – very basic shopping | 9 | 0/0/9 | 9/9 | No | — |
| H&M clothes shop – trying on a T-shirt | 10 | 0/0/10 | 10/10 | No | — |
| Museum – buying tickets & basic info | 9 | 0/0/9 | 9/9 | No | — |
| On the tram – talking to another passenger | 9 | 0/0/9 | 9/9 | No | — |
| Asking the tram driver for directions | 8 | 0/0/8 | 8/8 | No | — |

**Retired, not missing:** `letter_recognition_1`, `letter_recognition_2`, `letter_recognition_3` are still present as legacy source JSON but **intentionally excluded** from V2. Their former bundled word examples were replaced by the five curated sound-contrast modules. Do not treat them as three unbuilt V2 modules.

## Concrete input issues to resolve before treating normal Speak data as ready

## All 14 source-blocked Speak references have practice-only safeguards (2026-10-20)

Following the initial two Conversation 1 safeguards, the remaining **12** reference-blocked items across **six existing lessons** are now registered by their original IDs and exact Polish spellings in `additional-speak-reference-blockers.json`. All **14** remain present as Learn and unscored local Speak practice, keeping existing lesson item counts/IDs, original MP3s, review history and XP. Their legacy recordings are **not** shown as reliable Polish examples, they are excluded from Listen quizzes, and private Azure/Azure+Whisper scoring refuses both flagged source IDs and unmarked new slash/digit/ellipsis targets. This is a **guard**, NOT release-quality replacement audio or an editorial resolution of the written text. The normal `npm run audit:speak` now reports `practiceOnlyReferences:14` separately from the underlying `speakBlockedReferences:11` and `speakUnfinishedReferences:3`. Exactly matched original recorded audio must be independently verified before a completed grammatical alternative or number can be introduced, without silently changing old data. The full reference issue table below remains the editorial queue.

## Conversation 1: practice-only reference safeguards (2026-10-20)

The two existing Conversation 1 entries `Conversation_1:24` (`Jak ma pan/pani na imię?`) and `Conversation_1:25` (`Mam na imię…`) are now explicitly marked **practice-only reference pending** in the generated V2 catalog. Their original 26-item lesson, Polish prompts, recorded MP3 files and progress keys remain unchanged. Learners can see these items in Learn and record/replay in Speak, but **there is no claimed verified reference playback, no listening quiz on the two, and no private Azure-only or Azure+Whisper score**. Frontend and private backend enforce this independently. This removes false assessment eligibility; it **does not resolve** their content or audio provenance. Before releasing scores for either, choose a **single complete Polish utterance**, verify/replace the recording to match exact text, and have it independently reviewed. The rest of the reference issue table below remains pending.



The **11 backend-unscorable reference expressions**, grouped by module, are:

| Module | Current Polish reference | Issue / proposed editorial decision |
|---|---|---|
| Conversation 1 | `Jak ma pan/pani na imię?` | Select a grammatical complete alternative, e.g. pan **or** pani; separate cards if both needed |
| Conversation – restaurant | `Chciałbym / Chciałabym zamówić` | Split grammatical variants into independent entries |
| Conversation – restaurant | `Jestem wegetarianinem / wegetarianką` | Split alternative forms |
| Emergencies and Health | `Jestem ranny / ranna` | Split gender variants |
| Emergencies and Health | `Zgubiłem się / Zgubiłam się` | Split gender variants |
| Emergencies and Health | `Zgubiłem dokumenty / Zgubiłam dokumenty` | Split gender variants |
| Emergencies and Health | `Złamałem / Złamałam nogę` | Split gender variants |
| Food and Dinning | `Czy ma pan/pani menu po angielsku?` | Split pan/pani |
| Food and Dinning | `Co pan/pani poleca?` | Split pan/pani |
| Getting Around 1 | `Idzie pan/pani w dobrą stronę` | Split pan/pani |
| Road Terminology | `droga wojewódzka 634` | Specify spoken number in an authored reference, keep displayed road number if desired |

The **3 additional unfinished reference texts** are `Mam na imię…` (Conversation 1), `Jak dojść do …?` (Road Terminology), and `Przepraszam, jak dojadę do …?` (Transit 1). The current proxy can strip `…`, but the spoken target remains underspecified: either author a specific completed example or keep it for ungraded speaking practice. These are **14 problematic Speak items total**, with no overlap between those 11 and these 3.

## E1 Sound Lab focus letters — teaching cue added, pronunciation still unverified (2026-10-20)

The existing five contrast modules now show the **exact target Polish grapheme(s)** coloured and underlined within **all 26 original example phrases**. Editorial `focus` fields in `sound-contrasts.json` are checked against the exact source text and audio mapping during migration. The target spelling remains inside the full original expression: e.g., `Cz` in *Cztery*, `ć` in *Pięć*, `Si` in *Siedem*, `Rz` in *Rzeszów* and `krzy` in *ulica Świętokrzyska*. This is a **spelling/attention aid**, not a phonetic audio assessment, not additional grouped syllable scoring, and not evidence of native-reviewed reference audio. All 26 references, 482 source items, and the 26-module inventory remain unchanged. Owner priority columns are still unset.

## Curated Numbers 1–20 practice ranges (2026-10-20, supersedes arbitrary eight-item groups)

The owner rejected automatic 1–8 / 9–16 / 17–20 slicing as educationally arbitrary. **Numbers 1–20 remains ONE existing learning module** with its original 20 recorded items, full item-level progress, and identical audio/XP identities. Learners may work through **Numbers 1–10** and **Numbers 11–20** as optional internal sections, without creating two lesson records. Moving between Learn, Listen and Speak preserves the chosen range. Re-entry starts at the first unvisited range, and earlier ranges remain accessible. The separate `numbers_1-20` catalog still contains 20 items.

**All other vocabulary lessons remain intact, without automatic chunking.** Splitting greetings, shopping or directions into groups requires genuine pedagogical boundaries and explicit content review; a universal count-based cap is not authorized. Small sound-contrast lessons, Read sessions, due review queues and partial-audio personal sets retain existing behavior. These changes do not certify reference audio, syllable splits, Azure/Whisper scoring, or any other pronunciation quality decision.


## Owner direction and proposed granular rollout (2026-10-20)

**Owner-confirmed teaching priority, not yet an approval of every row order:** (1) beginner **vocabulary + listen + Speak**, emphasizing recognizable daily-use expressions and Polish sound contrasts; (2) **very short multi-line Read + Listen dialogues**; (3) **longer Read + Listen passages/dialogues** later. Do not turn all six longer reading modules into regular short-word Speak automatically. The exact set-by-set order below is a recommendation for owner review; keep the **Owner priority** cells in the inventory above unset until separately confirmed.

### Stage E1 — beginner vocabulary, sound distinction, listening and speaking (15 existing modules / 281 items)

All **281/281** E1 examples already have reference audio and an existing Speak entry point. All **23 editorial-draft instances** lie in these modules; the other 258 are automatic drafts. The **11 backend-unscorable alternatives/digit references and 3 unfinished ellipsis prompts** also all lie in E1 and require source-content decisions before AI scoring. All live provider scoring stays OFF on the public Free deployment.

| Order | Existing V2 module | Items | Why this order / next editorial action |
|---|---|---:|---|
| E1.01 | Conversation 1 (greetings) | 26 | First useful polite phrases; choose one `pan/pani` form and complete `Mam na imię…` before scoring |
| E1.02 | C · CZ · Ć | 6 | Fundamental difficult consonant contrast; review draft splits against recorded words |
| E1.03 | S · SZ · Ś | 6 | High-impact hearing/speaking distinction, including soft sounds |
| E1.04 | Numbers 1–20 | 20 | Short, repeatable everyday words; 6 editorial drafts ready for review |
| E1.05 | L · Ł | 4 | Short high-value listening contrast without overloading beginners |
| E1.06 | Conversation – shopping | 25 | Requesting, sizing, basic transactional vocabulary |
| E1.07 | Food and Dinning (existing source ID/spelling) | 25 | Everyday food expressions; split 2 `pan/pani` references |
| E1.08 | Conversation – restaurant | 25 | Ordering and simple responses; split 2 gender-alternative targets |
| E1.09 | Z · Ż/RZ · Ź/ZI | 6 | Sound distinction after learners know several real example words |
| E1.10 | Getting Around 1 | 26 | Basic directions, movement and city vocabulary; split 1 `pan/pani` target |
| E1.11 | Transit 1 | 20 | Tram/bus/stops; complete 1 route question with ellipsis |
| E1.12 | Road Terminology | 27 | Practical street terms, plus 7 existing editorial drafts; spell out one numeric spoken road reference and finish one placeholder |
| E1.13 | KRZY · PRZY | 4 | Cluster-focused listening with actual recorded phrase examples |
| E1.14 | Emergencies and Health | 25 | Survival expressions; split 4 gender-alternative targets |
| E1.15 | Numbers 20–100 | 36 | Wider number comprehension after foundational numbers and transactions |

**E1 learner loop:** existing audio **Listen → recognize meaning → Speak → hear/reference → record/replay → voluntarily repeat or Next**. Preserve the user's minimal Speak result: coloured Polish **text** with small visual segment gaps + one experimental blended overall score, **no per-syllable percentages, coloured boxes, explanation/legend or XP gate**. Show English pronunciation cues only when the guide is switched on. Do not show a remote score unless the authenticated, separately consented Azure/Whisper test is actually available. Rather than forcing learners through 25–36 unfamiliar entries at once, consider ordered 6–10-item *learning subsets*; these are a curriculum proposal, **not** 15 extra existing modules.

**E1 implementation order within each set:** (a) settle fixed spoken targets, especially the 14 flagged entries; (b) confirm example audio matches the exact target and listenability; (c) editorial Polish segmentation review prioritizing the difficult sound combinations; (d) check Learn/Listen/Speak modes, guide toggle, retry, incomplete/inconclusive states and family/offline safeguards; (e) physically benchmark pronunciation only after explicit owner-authorized audio/provider consent. An exact orthographic split or passing synthetic test is NOT acoustic calibration.

### Stage E2 — very basic multi-line Read + Listen (existing 1 bridge set, plus proposed short excerpts)

**Existing bridge module:** `Basic_01R` (**6 recorded reading lines**, source audio present, currently Read + Listen but **not Speak**). Its existing passages can introduce line-by-line comprehension, but do not automatically label six independent lines a natural continuous dialogue.

| Order | Short dialogue / bridge | Content source and minimum useful behavior |
|---|---|---|
| E2.01 | Greeting and response | New curated **2–4-turn** micro-dialogue, starting from existing greeting/Basic 01R expressions where audio is an *exact* match |
| E2.02 | Introduce yourself | New 2–4 turns for name, polite response and a simple question; eliminate placeholder/non-fixed spoken targets |
| E2.03 | Grocery purchase | New 2–4 turns sampled/edited from the existing 9-line grocery scene, recording new audio if text differs |
| E2.04 | Simple ticket purchase | New 2–4 turns from ticket/buying vocabulary and the 9-line museum source |
| E2.05 | Ask about a tram or stop | New 2–4 turns from the passenger/driver scenes, without launching either full scene yet |
| E2.06 | Basic 01R bridge review | Retain existing 6-line set as a short Read + Listen comprehension/review pathway |

**E2 UX goal:** display speaker turns together in reading order, play **a selected line** or **the short dialogue in sequence**, reveal English only when requested, and use a small number of authored comprehension prompts. Never claim combined playback/role-labelled turns already exist: the current catalog uses **one audio item per passage**, and the normal `Read` / `Listen` modes are present but this dialogue-specific composition needs design/implementation. Keep repetition of an individual line optional; implementing automated grading for longer multi-turn utterances is not an E2 prerequisite. New micro-dialogues are **proposed new units, not part of the existing 26-module/482-item count**.

### Stage E3 — longer Read + Listen, names and extended content (9 existing modules / 194 items)

| Order | Existing V2 module | Items | Treatment |
|---|---|---:|---|
| E3.01 | Grocery store – very basic shopping | 9 | Full scene after E2 short purchase conversation |
| E3.02 | On the tram – talking to another passenger | 9 | Full route/seat conversation after short tram exchange |
| E3.03 | Asking the tram driver for directions | 8 | Longer navigation and ticket information |
| E3.04 | Museum – buying tickets & basic info | 9 | Full ticket/closing-time/directions scene |
| E3.05 | H&M clothes shop – trying on a T-shirt | 10 | Full shopping, sizing and fitting-room exchange |
| E3.06 | Districts of Warszawa | 20 | Optional name/pronunciation enrichment; ASR proper-name caution |
| E3.07 | Cities of Poland | 29 | Broader place-name listening and recognition |
| E3.08 | Names of Poland 1 | 32 | Optional people-name recognition; avoid confident unvalidated ASR corrections |
| E3.09 | Countries of the World | 68 | Largest and lowest-frequency name catalog; last bulk editorial pass |

E3's five existing extended reading scenes have **45/45** reference audio items and no ordinary Speak button. The four existing proper-name vocabulary sets have **149/149** audio items and Speak entry points, but their auto-generated spelling partitions/ASR proper-name behavior are **not** reviewed. These 9 remain selectable in the library today; **E3 defers new-workflow editorial investment**, not access to existing lessons. Richer listening (connected whole-scene playback, review questions, natural pacing, optional individual line repetition) belongs here after E2 succeeds.

### Separate research fixture — not a beginner learning set

`Speak test · Świętokrzyska` = **1 item / 0 native reference MP3**, with authored but unreviewed grouping and an existing private historical owner test. Retain it as a **lab/diagnostic fixture**, not the first beginner lesson; obtain exact native reference audio and separate external review before promoting it. It is the remaining item needed to reconcile the catalog: **E1 281 + E2 6 + E3 194 + lab 1 = 482**, and **15 + 1 + 9 + 1 = 26** existing modules.

### Next action and acceptance boundary

1. Begin E1.01 greetings and the paired E1.02/E1.03 sound contrast exercises; review the existing authored/editorial source and the ambiguous targets, not all 458 auto-generated draft instances.
2. Regenerate and rerun `cd v2/frontend && npm run content && npm run audit:speak` after changing content; preserve exact source-to-audio mapping and the current regression totals until changes are intentional.
3. Once a few E1 sets have passed the content/review gates, prototype ONE E2 2–4-turn dialogue using source-matched audio. Evaluate line-by-line and whole-scene listen UX before adding the remaining dialogues.
4. Leave hosted AI activation, pronunciation-score calibration, the five full reading scenes, and large-scale place/name editorial review as separate later gates. Do not turn on providers, incur costs or store identifiable voice data as a side effect of this priority plan.

**Track decisions:** The stage order (E1/E2/E3) follows the owner's instruction. Specific E1/E2/E3 row order is **proposed** and open to owner reprioritization. Keep the existing per-module `Owner priority` cells above unset until approved, then record actual choices there. This table is a *human plan*, not proof that any item has been certified for live two-provider pronunciation assessment.
