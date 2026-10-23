# B-07 — T08 museum tickets, opening hours and visitor information (original-source pilot)

**Source baseline:** GitHub `main` `eda7c3cd5319a6da534e1c08101807b8a845c5f2`, certified B-06. **Editorial status:** original source references only; neither the nine-turn recording nor its translations have new native/editorial/physical certification in this tranche.

## Source-grounded learning, not real-world visitor guidance

The original `Museum_buying_tickets_and_basic_info` dataset has a nine-turn ticket/visitor exchange: greeting and request for two museum tickets; choice between normal and reduced tickets; request for normal tickets; asking about opening hours; illustrative reply “Dzisiaj jesteśmy otwarci do osiemnastej”; asking where the cloakroom is; directions to the right past stairs; location of the first exhibition; closing thanks. **Six p.m. is a scripted dialogue detail, not the hours of any real museum.**

| Mode | Original source | Indices | Count | Honest scope |
| --- | --- | --- | --- | --- |
| Listen | `Museum_buying_tickets_and_basic_info` | `0–8` | 9 | Existing recorded ticket/visitor conversation, not a live venue source |
| Speak | `Getting_Around_1` | `6,7,8,9,14,15,17` | 7 | Original generic ticket count/class, price, card payment, purchase location requests; no recording of museum-specific roleplay |
| Read | `Museum_buying_tickets_and_basic_info` | `0–8` | 9 | Original museum dialogue text in existing Read practice; no independent sign, price notice or visitor information sheet |

**Exact original Polish/English anchors**:
- `Museum_buying_tickets_and_basic_info:0`: “Dzień dobry, poproszę dwa bilety do muzeum.” / “Good morning, two tickets to the museum, please.”
- `Museum_buying_tickets_and_basic_info:1`: “Normalne czy ulgowe?” / “Regular or reduced tickets?”
- `Museum_buying_tickets_and_basic_info:3`: “Do której godziny muzeum jest otwarte?” / “Until what time is the museum open?”
- `Museum_buying_tickets_and_basic_info:4`: “Dzisiaj jesteśmy otwarci do osiemnastej.” / “Today we are open until six p.m.”
- `Museum_buying_tickets_and_basic_info:5`: “Gdzie jest szatnia, proszę?” / “Where is the cloakroom, please?”
- `Museum_buying_tickets_and_basic_info:6`: “Szatnia jest na prawo, za schodami.” / “The cloakroom is on the right, past the stairs.”
- `Getting_Around_1:6`: “Jeden bilet, proszę” / “One ticket, please”
- `Getting_Around_1:7`: “Dwa bilety, proszę” / “Two tickets, please”
- `Getting_Around_1:15`: “Czy mogę zapłacić kartą?” / “Can I pay by card?”

The scenario and generic ticket phrases are useful sources of practice, but using them does **not** establish mastery of visiting attractions. No newly reviewed ticket prices, current opening hours, audio/English variants, family/child ticket requirements, accessibility services, closure notices, mixed dialogues, venue-specific directions, independently authored opening-hours sign or comprehension questions are introduced. These require reviewed wording and aligned recordings before considering T08 complete. Avoid using data in the lesson as operational visitor guidance.

## Technical scope

Append T08 as internal Journey 1/middle, order 8. Preserve the complete T01–T07 manifest, existing audio files and lesson item IDs, 26 original sets/482 items/455 inherited MP3s, 14 `practice_only` reference exclusions, Numbers 1–20 and optional 10+10 batch, local progress/review/XP/consent/family/offline and invisible 3×3 placement semantics. Eight tourist cards offer 22 mode entry actions. Existing A-05 version-1 local source-unit activity and backup support T08: 25 original item/mode attempts, an optional Resume cursor, no retroactive source-level inference and no T07 attempt duplication for shared ticket phrase IDs.

Unit-source validator fails closed on absent/unsafe MP3, source substitution with a personal set, wrong mode, duplicate/out-of-order reference and invalid content metadata. Existing unpublished T02/T03 native editorial guard must remain effective. Desktop/mobile synthetic browser tests cover the museum script, original spoken ticket phrase, source-local Resume, old unit history, 320px layout and explicit Home course cursor. No speech scoring or AI paid provider invoked.

## Merge gate and next human content

All **four final-head GitHub Actions lanes** required: frontend migration/TS/Vitest/build/desktop+mobile/offline/audio/a11y, connected-family browser, private backend and benchmark. Passing CI certifies source integrity and synthetic learning navigation **not** native Polish, voice recording accuracy or actual venue information. Open issues #126, #129, #132, #134 continue independently; T08 museum-specific native text/audio and visitor-sign editorial review must be separately tracked.

After this source-backed candidate, T09 accommodation/check-in has **no dedicated original recording**; do not silently fabricate lodging content just to fill the curriculum. Prefer a native-approved editorial packet before any T09 learner-facing source promotion. Physical iPhone/Safari, microphone, acoustic expert review, paid cloud speech engines and deployment remain deferred.
