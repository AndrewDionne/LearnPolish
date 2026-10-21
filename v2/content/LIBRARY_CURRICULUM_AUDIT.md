# Path to Polish — Library Content & Curriculum Audit

**Audited:** 21 October 2026 · **Source of truth:** `v2/content/library-catalog.json`

## Why reorganize

The 26 active V2 learning sets previously inherited mechanical names from file identifiers (for example `Basic_01R`, `Food_and_Dinning`, `H_M_clothes_shop_trying_on_a_T-shirt`). The Library showed them as one undifferentiated grid. Source content ranges from whole-word sound contrasts to place names, sentence patterns and longer reading conversations. Their filenames often do not identify that distinction.

**Scope:** exactly 26 existing sets / 482 items. Display titles and descriptions were reauthored against the exact original source content. Catalog position is an optional editorial classification; it does **not** modify `id`, `item.id`, Polish or English expressions, audio paths, current learning modes, reading position, XP, family activity or saved progress. There are no new sets, artificial eight-card lessons, auto-generated speaker voices or pronunciation scores. The learner may still choose **any** lesson immediately.

## Proposed learner organization now implemented

### 1. Fundamentals — sounds and single-word foundations

Sound contrasts, first numbers, then broader noun/place/number vocabulary. These are optional learning stages, not access gates.

| Existing source ID | New learner-facing title | Description |
|---|---|---|
| `contrast_l_lstroked` | L and Ł | Hear the difference between Polish L and Ł in real words. |
| `contrast_c_cz_cie` | C, CZ and Ć | Compare three Polish consonant sounds in recorded words. |
| `contrast_s_sz_sie` | S, SZ and Ś | Hear the contrasts between S, SZ and Ś or SI in everyday words. |
| `contrast_z_zh_zi` | Z, Ż/RZ and Ź/ZI | Compare the plain, deeper and softer Z-family sounds in context. |
| `contrast_krzy_przy` | KRZY and PRZY | Listen for these challenging consonant clusters inside complete expressions. |
| `numbers_1-20` | Numbers 1-20 | Learn the first twenty numbers, with optional practice in two groups of ten. |
| `Numbers_20-100` | Numbers Beyond 20 | Build number vocabulary with tens, combinations and larger values up to 1,020. |
| `Road_Terminology` | Streets and Road Words | Name roads, squares, intersections and common features of Polish streets. |
| `Districts_of_Warszawa` | Warsaw Districts and Landmarks | Recognize Warsaw districts and a few familiar local landmarks. |
| `The_Cities_of_Poland` | Cities of Poland | Hear and practise the names of Polish cities, from Warszawa to smaller centres. |
| `Names_of_Poland_1` | Polish First and Last Names | Get comfortable hearing and saying common Polish personal names. |
| `Countries_of_the_World` | Countries in Polish | Learn Polish names for countries across Europe and the wider world. |

### 2. Basic — expressions and sentences

Start with greetings and multiword expressions, then practise practical sentence-level requests and questions.

| Existing source ID | New learner-facing title | Description |
|---|---|---|
| `Conversation_1` | Greetings and Introductions | Say hello and goodbye, use polite words and introduce yourself. |
| `Conversation_-_shopping` | Shopping: Useful Questions | Ask prices, discuss payment and make simple shopping requests. |
| `Conversation_-_restaurant` | Ordering at a Restaurant | Ask for food and drinks, make requests and handle the bill. |
| `Food_and_Dinning` | Eating Out: Tables and Food | Ask for a table, describe food preferences and respond at a restaurant. |
| `Getting_Around_1` | Asking for Directions | Ask how to get somewhere and understand everyday directions. |
| `Transit_1` | Public Transport Phrases | Ask about stops, tickets, routes and getting around by public transport. |
| `Emergencies_and_Health` | Health and Emergency Phrases | Ask for urgent help, describe common problems and request medical assistance. |

### 3. Learning — short conversations and reading

The six original reading lessons, ordered by their existing authored reading pathway. The first two also contain three opt-in micro-dialogues.

| Existing source ID | New learner-facing title | Description |
|---|---|---|
| `Basic_01R` | Everyday Conversations: Greetings | Read greetings and introductions, then practise two short exchanges. |
| `Grocery_store_very_basic_shopping` | At the Grocery Store | Follow a simple apple purchase, then practise the customer-assistant exchange. |
| `H_M_clothes_shop_trying_on_a_T-shirt` | Buying Clothes: A T-Shirt | Read a clothing-store interaction about sizes, fitting rooms and paying. |
| `On_the_tram_talking_to_another_passenger` | On the Tram: A Conversation | Follow a passenger asking about seats, stops and the city centre. |
| `Asking_the_tram_driver_for_directions` | Asking a Tram Driver | Read questions about destinations, stops and buying a ticket on the tram. |
| `Museum_buying_tickets_and_basic_info` | At the Museum | Practise a museum visit, including tickets, opening hours and finding exhibitions. |

### Separate practice tools — not a curriculum level

The existing unrecorded Świętokrzyska pronunciation/latency test stays accessible but outside the beginner lesson path.

| Existing source ID | New learner-facing title | Description |
|---|---|---|
| `speak_swietokrzyska` | Świętokrzyska Pronunciation Lab | Try recording a difficult Warsaw place name; reference audio and pronunciation guide still need review. |

## Findings and next editorial steps

1. **Inaccurate inherited titles corrected:** `Numbers_20-100` actually extends through *tysiąc dwadzieścia* (1,020), so the new name is **Numbers Beyond 20** and the description states its true range. `Districts_of_Warszawa` also includes Warsaw landmarks and an institution, not only official districts; its new name explicitly acknowledges this. `Food_and_Dinning` had a spelling problem in the source filename; only its learner-facing display was corrected. Source IDs remain as-is for compatibility.
2. **Sound lessons are contrast work:** the five source-backed exercises use real recorded words and phrases; they are **not** isolated-phoneme audio or certified minimal pairs. Labels and descriptions avoid such claims. Written target letters can be highlighted independently of speech assessment.
3. **Mixed-size vocabulary is intentional:** `Road_Terminology` mixes single words and longer street terms; it sits within expanded vocabulary without automatically splitting its 27 original items. **Numbers 1–20** remains one 20-item lesson with only its previously accepted optional 1–10/11–20 practice sections.
4. **Two sentence-oriented lessons overlap:** `Conversation_-_restaurant` emphasizes ordering and practical requests, while `Food_and_Dinning` covers tables, preferences and dining dialogue; their distinct descriptions make this clear without pretending they are a rigid sequence.
5. **Reference review limitations remain:** 14 source phrases are still practice-only until exact Polish wording and MP3 correspondence are reviewed. The separate `speak_swietokrzyska` diagnostic has no trusted native MP3 and should not be treated as a foundational production lesson. All six reading sets have original imported recordings, but native-audio quality verification is still open.
6. **Progression is guidance, not locking:** the three named learning stages coexist with the existing Sound/Vocabulary/Reading filters, full-text Polish search, saved progress and independently created personal lessons. The diagnostic is visibly separate from those three educational stages; personal lessons appear in a separate collection. Future lesson additions should receive editorial stage, topic, description and placement before launch, rather than deriving level from file names or item counts.

## Validation contract

The V2 migration must find exactly one catalog entry for each of 26 original built-in lesson IDs and reject duplicate/missing catalog rows, invalid stage–track–kind combinations, empty descriptions, or overlapping track order. The frontend's strict manifest validator also checks metadata. Tests confirm the 12 Fundamentals + 7 Basic + 6 Learning + 1 optional Practice Tools split, title/descriptions, preservation of IDs/MP3s, ordered grouping, search by original filename and responsive filter behavior.

