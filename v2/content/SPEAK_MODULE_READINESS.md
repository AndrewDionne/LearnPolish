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

## Reading & dialogues — 6 modules currently **without** Speak mode

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

## Proposed prioritization for owner review

I suggest starting with **Conversation 1**, **Numbers 1–20**, and **Road Terminology**, together with the **five sound-contrast modules**. They provide basic Polish practice, cover hard letter combinations, and already contain the only 23 editorial grouping instances. Then work through Shopping / Getting Around / Transit / Restaurant / Food / Emergencies, before proper names and the larger country catalog. Decide separately whether Reading should gain phrase-level Speak; it is not just another boundary-edit task.

**How to update this tracker:** Change the last-column `Owner priority` entries after owner decides; use brief values such as P1/P2/P3/Defer. As editorial boundaries are added to `v2/content/pronunciation-segment-overrides.json`, regenerate normal V2 content and rerun `npm run audit:speak` to update the A/E/D and blocked counts. **Do not call provisional segmentation "complete"**, and do not turn on paid/network providers as a side effect of content review. This Markdown snapshot is informational; source data + code remain the authoritative machine-readable state.
