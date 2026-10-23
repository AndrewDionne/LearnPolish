# B-00 / A-00 — Conversational Polish curriculum audit and gap-fill plan

**Owner brief 2026-10-23.** A deliberately **linear, coherent core learning programme** for an English speaker, prioritizing **Speak, Listen and Read in real everyday conversations**, not professional Polish. Three real-world phases: **1 Visiting Tourists → 2 Extended Stay → 3 Living in Poland**. Personal/custom lessons are separate, but remain fully usable. This is a **detailed editorial and source audit plus provisional new-course blueprint**, not a native-certified finished syllabus or permission to automatically invent lesson text/audio.

**Authoritative sources reviewed:** `v2/content/library-catalog.json`, earlier [topic/title audit](content/LIBRARY_CURRICULUM_AUDIT.md), all **23 original JSON sources under `docs/sets/`** (20 included original study sets and three unshipped/replaced letter-recognition banks), `v2/content/sound-contrasts.json` (5 derived contrast sets), `reading-checks.json` (24 source-linked questions across six reading sets), `micro-dialogues.json` (three small authored reply drills), `additional-speak-reference-blockers.json`, `v2/frontend/src/{model,modes,personal,library-curriculum,practice-batches}.ts`, and current `App.tsx`. `v2/content/library-catalog.json` remains the **current deployed Library editorial source** until a separately reviewed implementation PR.

## Verdict: substantial usable assets, not yet a structured course

- **Currently shipped 26 V2 sets / 482 learning items:** 5 sound-contrast sets containing **26 source-derived word examples**, 7 Fundamentals vocabulary source sets (**232 items**), 7 Basic vocabulary/sentence source sets (**172 items**), 6 reading dialogue sets (**51 turns**), and 1 separate unrecorded pronunciation lab (**1 item**). **232 + 172 + 51 + 26 + 1 = 482**. There are **455 preserved original MP3s** associated with the migrated 20 original source sets. Curated contrast examples **reuse** original audio, not independently recorded phoneme references. All counts source-backed; source audio *linguistic quality* remains unverified.
- The raw `docs/sets` folder has **23 legacy files, 488 original rows**, including three bundled-word `letter_recognition_1/2/3` source collections of **9 + 14 + 10 = 33** rows that are **not 33 active V2 lesson items**. The rebuilt V2 uses five curated, individually sourced sound-contrast sets instead. Avoid counting all 488 raw rows as present-day V2 items or claiming original raw sound bundles are phoneme-verified.
- Historical labels **Fundamentals → Basic → Learning** express kind of material, not a child's/tourist's progress through capabilities. Fundamental stage currently lists all sound contrasts and standalone large noun/name/place inventories *before* the basic greeting lesson. This is the principal sequence defect.
- **Listening** is sometimes choice-of-English-translation rather than understanding a realistic spoken reply; six reading dialogues have 24 exact-source comprehension questions; only **three short source-based reply scenes** exist. Speaking mode supports vocabulary/sound items but **not reading dialogues** (`availableModes`). The app therefore supports all three skills **across** the library but not yet as a connected conversational unit.
- **Some source items are unsuitable for automatic scoring:** 14 ambiguously phrased/slash/ellipsis/numeral records are already marked `practice_only`; new conversations must not claim reliable spoken reference audio until native review and recording QA.

## Disposition of every active built-in V2 learning set

**Disposition codes:** **ANCHOR** = use selected authentic source material early in the proposed core; **SUPPORT** = reusable context/review, not mandatory whole-set advancement; **EXPAND** = viable source, but needs connected scenario, missing activity modes and/or new vetted lines; **OPTIONAL** = outside linear core (remain Library discovery); **LAB** = standalone technical/pronunciation work, not course.

**Course placement is proposed**, never an automatic re-tag of old metadata. `P1` below = tourist, `P2` = extended stay, `P3` = resident. Some source sets naturally support multiple course phases through **references to the same existing item IDs** rather than copying or overwriting them.

| Current set ID | Learner-facing title | Items | Recommended disposition | Core use and specific gap |
|---|---|---:|---|---|
| `contrast_l_lstroked` | L and Ł | 4 | SUPPORT P1–P3 | Optional English-speaker sound contrast; not a compulsory first course unit or graded syllable diagnosis |
| `contrast_c_cz_cie` | C, CZ and Ć | 6 | SUPPORT P1–P3 | Trigger on relevant phrases as an ear-training link; examples are whole recorded words |
| `contrast_s_sz_sie` | S, SZ and Ś | 6 | SUPPORT P1–P3 | Embed listening contrast when useful, not five sound drills before hello |
| `contrast_z_zh_zi` | Z, Ż/RZ and Ź/ZI | 6 | SUPPORT P1–P3 | Existing contrasts are useful; not full native minimal-pair/acoustic evidence |
| `contrast_krzy_przy` | KRZY and PRZY | 4 | SUPPORT P2–P3 | Challenging phrases later; avoid demanding these clusters before basic exchanges |
| `numbers_1-20` | Numbers 1–20 | 20 | ANCHOR P1 | First prices/tickets/quantity: preserve **one** lesson and optional 1–10, 11–20 internal sessions |
| `Numbers_20-100` | Numbers Beyond 20 | 36 | SUPPORT P1/P2 | Source includes numbers up to 1,020; teach selected practical prices/time before all combinations |
| `Road_Terminology` | Streets and Road Words | 27 | SUPPORT P1/P3 | Use only relevant location/direction terms with short spoken requests, not whole list as prerequisite; 2 unsafe reference records |
| `Districts_of_Warszawa` | Warsaw Districts and Landmarks | 20 | OPTIONAL P2/P3 | City-specific geography does not belong in mandatory traveller entry path |
| `The_Cities_of_Poland` | Cities of Poland | 29 | OPTIONAL P1/P3 | Names useful in travel context, but whole-set drilling is not conversational progression |
| `Names_of_Poland_1` | Polish First and Last Names | 32 | OPTIONAL P2/P3 | Listening to names is useful; full list is not a course unit, prefer name introduction/dialogue first |
| `Countries_of_the_World` | Countries in Polish | 68 | OPTIONAL P2/P3 | **Large isolated geography inventory**; not core conversational lesson; sample home country only when context requires |
| `Conversation_1` | Greetings and Introductions | 26 | **ANCHOR P1** | Earliest genuine dialogue phrases; 2 last ambiguous prompts require native/recording resolution before scored practice |
| `Conversation_-_shopping` | Shopping: Useful Questions | 25 | ANCHOR P1 → EXPAND P2 | Price, size and checkout language; add clerk follow-ups/real replies and listening questions |
| `Conversation_-_restaurant` | Ordering at a Restaurant | 25 | ANCHOR P1 | Functional requests; some alternatives are bundled (2 protected references), needs source-audio reviewed scenario |
| `Food_and_Dinning` | Eating Out: Tables and Food | 25 | SUPPORT/EXPAND P1–P2 | Useful table, preferences, payment. Overlaps Ordering at a Restaurant; deliberately weave as advancing rounds, not competing beginner sequences (2 protected) |
| `Getting_Around_1` | Asking for Directions | 26 | ANCHOR P1 | Pair learner question with understandable reply, left/right/stop, missed direction clarification (1 protected) |
| `Transit_1` | Public Transport Phrases | 20 | ANCHOR P1 | Pair with existing tram readings; add direction confirmation / disruption interactions (1 protected) |
| `Emergencies_and_Health` | Health and Emergency Phrases | 25 | ANCHOR essential P1 / EXPAND P2 | Distinguish safety phrases from medically precise dialogues; 4 protected text/audio; professional medical language not expected |
| `Basic_01R` | Everyday Conversations: Greetings | 6 | **ANCHOR P1** | Read/listen two-way greetings; two source-based micro-dialogues. Natural conversational speaking turn still needs a common workflow |
| `Grocery_store_very_basic_shopping` | At the Grocery Store | 9 | ANCHOR P2 / preview P1 | Fully useful food transaction; three-turn reply scene; needs richer follow-up/clarifications |
| `H_M_clothes_shop_trying_on_a_T-shirt` | Buying Clothes: A T-Shirt | 10 | ANCHOR P2 | Sizes/assistance/fitting: reuse source with conversational Speak, add returns/exchanges later |
| `On_the_tram_talking_to_another_passenger` | On the Tram: A Conversation | 9 | ANCHOR P1 → P2 | Existing listener context about seats/stops; no speaking dialogue mode on reading lesson today |
| `Asking_the_tram_driver_for_directions` | Asking a Tram Driver | 8 | ANCHOR P1 | Recorded route/ticket exchange; bridge phrase drills to spoken response |
| `Museum_buying_tickets_and_basic_info` | At the Museum | 9 | ANCHOR P1 | Well-aligned tourist scene; add optional answer-turn and transfer to other venues |
| `speak_swietokrzyska` | Świętokrzyska Pronunciation Lab | 1 | **LAB ONLY** | Experimental place name without validated reference; explicitly outside every course phase until independently certified |

**Total mapped: 26 distinct active built-ins / 482 items.** Optional sets stay discoverable; omission from *mandatory* course does not remove, rename or devalue source lessons. Tourist phase must not require learning all 68 country names.

## Proposed coherent COURSE structure — review blueprint, NOT produced lessons

**Unit size and pace are editorial, not tied to arbitrary 8-card slices.** One functional outcome per unit, as much existing source as makes a natural arc plus newly native-reviewed bridging text/audio. Every unit should have the same learner-facing pattern:

**(1) Hear and notice context → (2) learn a few reusable phrases → (3) answer/listen and replay → (4) record/speak without mandatory grading → (5) read a short exchange/sign/text → (6) review in later sessions.** Some units will have fewer components; do not fake the missing ones. Unit completion shows honest “activities attempted” not fluency/mastery.

### Core Phase 1: Polish for Visiting Tourists

| Suggested order | Functional outcome (“I can…”) | Available source anchors | Concrete missing content / skill |
|---|---|---|---|
| T01 | Hear/give a polite greeting, apology and basic clarification | `Conversation_1`, `Basic_01R` | Listen/speak quick roleplays and *please repeat / slower / I don't understand* follow-up; native review of polite variants |
| T02 | Introduce myself and answer a simple personal question | `Conversation_1`, `Basic_01R` micro-dialogues | Small-name pattern and reciprocal questions; guided reply without hiding pronunciation errors |
| T03 | Understand useful numbers, a price and quantity | `numbers_1-20`, selected `Numbers_20-100`, Shopping | Counterparty pricing replies, real listening values; keep Numbers lesson intact |
| T04 | Order a drink/meal and pay | Restaurant, Eating Out | One recorded coherent waiter–guest exchange plus clarification and choices; distinct from bundled phrases |
| T05 | Buy something in a shop | Shopping, Grocery reading | Ask price/quantity/card, understand seller response, short roleplay |
| T06 | Ask where a place is and follow simple directions | Getting Around, Road Terms | Two-way left/right/straight, repeat/clarify, short wayfinding text |
| T07 | Identify a public transport stop/route and ticket | Transit, both tram readings | Dialogue Speak return, stops, line, time, correct platform/direction |
| T08 | Buy a ticket and ask opening times at an attraction | Museum reading | Tour guide/ticket confirmation reply and practical opening-hours sign |
| T09 | Check in or ask basic questions at accommodation | **No dedicated existing source** | **New validated lodging check-in and room/key/wifi/breakfast mini-dialogue**, short message/sign |
| T10 | Handle an urgent need and ask for help | Emergencies/Health | Safety-first short requests, lost object/misdirection, clear distinction from nuanced medical advice |
| T11 | Repair a conversation when I do not understand | Reuse greeting, shopping, direction phrases | **Dedicated repair/repetition phrases** and quick response exercises across several settings |
| T12 | Complete a mixed short travel exchange | Reuse T01–T11 sources | **Cross-scenario audio listening + user-choice reply + reading recap**, honest ungraded Speak evidence |

**Phase 1 exit target (qualitative, not score gate):** A tourist can participate in everyday short situations using learnt requests and understand predictable replies. No compulsory graded pronunciation/CEFR claim. The earliest learning experience must feature **conversation, not sound quizzes or world geography**.

### Core Phase 2: Extended Stay

| Suggested order | Functional outcome | Existing anchors | Key missing content |
|---|---|---|---|
| E01 | Shop for groceries with alternatives and follow-up | Grocery reading, Shopping | Quantities/options, unavailable item, packaging, clarification |
| E02 | Buy or return clothing and ask about fit | Clothes reading | Exchange/returns, sizes, changing-room replies |
| E03 | Explain a daily plan, date, time or schedule | Selected numbers | **Days/dates/time, future/plans, time expressions and spoken scheduling** |
| E04 | Make, change or cancel an appointment | None dedicated | **Phone/reception exchanges, appointment confirmations and short messages** |
| E05 | Explain a common minor health need or pharmacy request | Emergencies/Health | **Pharmacy and appointment dialogue**, distinct from emergencies/medical instruction |
| E06 | Handle accommodation and routine services | Tourist lodging bridge | **Landlord/concierge/utility basics, service requests, room problems** |
| E07 | Handle public transport changes or delays | Tram readings, Transit | **Unexpected change, rerouting, late/early clarification and public notices** |
| E08 | Make social plans and manage everyday small talk | Greetings | **Invitations, preferences, weather, simple past/future in context** |
| E09 | Handle everyday errands and deliveries | Shopping source | **Parcel/pickup, checkout problems, delivery directions and texts** |
| E10 | Manage a longer back-and-forth transaction | Reused scenarios | **4–8-turn exchanges**, varied but native-authored replies and honest comprehension |

**Phase 2 exit target:** a learner can handle a predictable, multi-turn everyday situation, adapt after one extra question and read a short practical message.

### Core Phase 3: English Speaker Living in Poland

| Suggested order | Functional outcome | Existing sources | Key missing content |
|---|---|---|---|
| R01 | Speak casually with neighbours and acquaintances | Greetings, place/name references | **Natural social small talk**, conversation opening/closing, polite/formal shift |
| R02 | Explain a household problem and request repair | Road/location terms tangential | **Home, utilities, maintenance and deliveries** |
| R03 | Book/resolve routine local services | Shopping, appointments from E04 | **More detailed service confirmations and misunderstandings** |
| R04 | Handle follow-up healthcare, pharmacy and practical health conversations | Emergencies/Health + E05 | **Common non-urgent appointments**, body/need descriptions reviewed by Polish speaker |
| R05 | Understand a local notice, text or simple email | Reading six imported contexts | **Notices, service messages and practical written Polish** |
| R06 | Discuss payment, billing or a missed delivery | Shopping, numbers | **Bills, subscriptions, payment problems and corrections** |
| R07 | Have a short school/family/community conversation where relevant | None dedicated | **Family, neighbours, community, school contexts** as optional non-mandatory subtracks |
| R08 | Tell a brief story about yesterday or plans for tomorrow | Basic phrases only | **Natural simple past/future and linking expressions in real dialogue**, not a standalone grammar exam |
| R09 | Sustain a longer exchange with follow-ups and clarifications | Existing Read scenes as starter | **Natural 6–12-turn colloquial conversations**, progressively varied listening and spoken replies |
| R10 | Navigate a real-life “living here” scenario end to end | Reusable E01–R09 | **Integrated scenario** combining spoken interaction, listening and short reading, no business/professional jargon |

**Phase 3 exit target:** practical conversational independence in common social, home, services and community situations for a non-native English-speaking resident. **Professional Polish is explicitly not a goal**. Optional regional vocabulary (Warsaw districts, cities and personal names) remains helpful enrichments, never mandatory graduation.

### Coverage gap matrix

| Capability | Visiting tourists | Extended stay | Living in Poland | Production status |
|---|---|---|---|---|
| Single high-utility phrase Learn/Speak | Many reusable originals | Many reusable originals | Some reusable | Existing activities; 14 source restrictions |
| Real recorded short exchanges | Greetings, trams, museum | Grocery and clothes | Nearly none | Six Read sets (51 turns) but little unit-based scaffolding |
| Contextual Listen response | 24 authored comprehension checks total | Small coverage | Missing | Source-audited original only; new native editorial work |
| Spoken dialogue turn-taking | Two greeting + one grocery mini-scenes | Nearly none | Missing | Current 3 reply-choice scenes; reading kind has no Speak mode |
| Everyday reading (menus, signs, texts) | Partial via museum/tram dialogues | Limited | Missing | Requires short practical reading material |
| Numbers, everyday prices | Existing | Existing | Existing | Need application, not every possible count as entry prerequisite |
| Time, schedule, appointments | Mostly missing | **Major gap** | Reused deeper | New content required |
| Repair/clarification under confusion | Fragmentary | **Gap** | **Gap** | Need repeated context-independent repairs |
| Household/neighbour/services | Missing except basics | Gap | **Major gap** | New scenarios, no forced profession content |
| Contextually progressive grammar | Incidental source phrases | Incomplete | Incomplete | Draft short functional patterns, native review, no grammar-heavy course |
| Review/spaced repetition | Existing Learn only | Existing Learn only | Existing Learn only | New course/skill orchestration without fake Speak scoring |
| Natural/acoustic correctness | Not independently certified | Not independently certified | Not independently certified | Owner-deferred native/audio/provider gates |

## Curriculum construction policy and acceptance requirements

1. **Separate canonical course vs Library vs personal:** versioned `coreCourse` definition references stable original item IDs. Three core `coursePhases`, ordered units and optional supporting practice; existing `curriculum.stage` remains presentational and is **not** silently reused as tourist level. A user can still open any unit or source lesson directly. Personal `source:'personal'` and its import/export remain entirely outside course mapping and core completion.
2. **No destructive repackaging:** preserve 26 existing sets/482 V2 items, 455 legacy original MP3 assets, original IDs and progress storage, one Numbers 1–20 source + 1–10/11–20 optional internal practice. Do not fabricate new unit-sized slices from generic counts.
3. **Clearly classify content:** each unit's component labelled original-validated-source, source-audio-needs-human-review, authored-unreviewed, recorded-native-reviewed, assessment-eligible. Every new item must have an identified source, spelling/translation editorial check, review owner and approved licence/recording process before production.
4. **Speak, Listen, Read are distinct but share context:** a core unit reuses a small set of expressions in a natural exchange and has listening-for-meaning, repeat/record (unscored by default), and a relevant reading/response. Keep identity of each practice event; do not create duplicated XP just because two cards refer to one phrase.
5. **Skills without model overclaim:** correct multiple-choice comprehension is one evidence type; self-rated Learn is another; a usable mic take is practice. Never infer pronunciation mastery or future unlocking from experimental Azure/Whisper. No forced score gate. Difficulty/growth XP should not be altered in a curriculum-planning PR.
6. **Personal lessons aren't a branch of the core:** import/edit/export in `Your lessons`; never suggest as next course unit, never count toward a phase’s completion; preserve personal review/history and current eligible local effort XP where applicable. Core progress indicator uses only explicitly mapped built-in activities.
7. **Phased content production:** work from high-priority pilot **T01–T03** first, then T04–T08 and T09–T12, then extended/resident. This is an **editorial production plan** that must be confirmed before generating Polish prompts or audio; don't bulk invent 30+ lessons.
8. **Native QA and transcript quality gate:** each scenario needs native Polish speaker review of pronunciation/idiom, consistent register/pan/pani/gender alternatives, and a verified transcript/audio match. Old 14 protected records remain untouched until reviewed, revised and re-recorded. Default app can function with unscored Speak; AI assessment remains off unless separately authorized.
9. **Accessible steady progression:** compact learner outcomes, optional suggested next, core vs personal separation, offline viability and clear “review earlier” interaction. All units freely selectable; milestones honest, review scheduling/version migration tested.
10. **What counts as curriculum DONE:** not merely 26 renamed topic titles. It means a traceable, sequence-tested mapping from tourist through resident with meaningful situations, Listen/Read/Speak exercise coverage, sourced accurate conversational language, complete no-fake-grade honesty, and native-review gates explicitly resolved before release.

## Proposed delivery packages and owner review points

| Content or product package | Scope | Approval / verification |
|---|---|---|
| **B-01 Course sequence approval** | Decide unit titles/outcomes from provisional T/E/R blueprint; lock metadata schema, core vs personal boundary and accessibility. | Owner approves outcomes/order; no new audio or scoring. |
| **B-02 Reference-to-unit inventory** | Machine-validate exact original item reuse for T01–T03, no missing/duplicate IDs, audio provenance and protected entries. | CI source integrity; old catalogue intact, items not moved/deleted. |
| **B-03 Tourist pilot** | Author only **T01–T03** missing short two-way situations + comprehension + practical reading, with mode integration. | Native transcript and audio rights/editorial review required before treating new speech as verified; then four lanes CI. |
| **B-04 Tourist complete** | T04–T12 coherent scenes and review, addressing lodging/repair-of-misunderstanding and short travel loop. | Spoken/reading/listening coverage and native QA; learner acceptance later. |
| **B-05 Extended stay** | E01–E10 focus on scheduling, services, social/errands, shorter colloquial multi-turn conversation. | Scenario QA, gradual difficulty and regression. |
| **B-06 Resident** | R01–R10 focus on home/community/services, simple informal written interactions and longer follow-ups. | Same gate, optional subtracks, no professional-language expansion. |
| **B-07 Full course quality release** | First-run/resume/switch personal/due review/phase advancement offline/Mobile + source metadata and saved backup migration. | Four green CI per PR + final physical/native spoken validation when resumed. |

**Immediate next action after this audit:** User review/approval of the T/E/R outcomes and core-vs-personal boundary. Then implement **A-01/B-01** versioned course mapping before rewriting navigation or manufacturing new learning materials. This file is a **planning deliverable**, not a new curriculum in the shipped app.
