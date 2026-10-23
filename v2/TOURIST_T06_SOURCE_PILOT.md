# B-05 — T06 route and stop questions (source-only pilot)

**Status: implementation candidate, NOT native-reviewed or physically certified.** Baseline from GitHub main `4866542ec59154c0a86817924a057f12e4dc35f7` (certified A-05). This audit uses exact original Polish, English and inherited audio; there is **no** newly recorded left/right/straight dialogue and no authored location sign.

## Learner outcome, limits and source matrix

T06, **Finding your way to the centre**, is a *bridge* between the existing tourist price/shop units and the upcoming T07 public-transport unit: ask where a stop is, ask the way to the centre or airport, check whether a tram goes to the centre, and hear the reply identifying the stop. The name/description deliberately does **not** claim a complete pedestrian-navigation conversation.

| Activity | Original lesson ID | Exact source indices | Honest content |
| --- | --- | --- | --- |
| Listen | `Asking_the_tram_driver_for_directions` | `0–4` | Real question to a tram driver, confirming the centre route and hearing the stop where to get off; 5 source recordings |
| Speak | `Getting_Around_1` | `0, 1, 2, 11, 20, 22` | Six recorded *isolated* questions about stops, city centre, metro, airport, tram routing, and distance; not full interactive speech roleplay |
| Read | `Asking_the_tram_driver_for_directions` | `0–4` | The same original five recorded scene turns, with existing reading/comprehension mechanics; not a newly authored map or wayfinding sign |

**Key immutable source examples**:
- `Getting_Around_1:0` — “Gdzie jest przystanek?” / “Where is the bus/tram stop?”
- `Getting_Around_1:1` — “Którędy do centrum?” / “Which way to the city center?”
- `Getting_Around_1:20` — “Czy ten tramwaj jedzie do centrum?” / “Does this tram go to the center?”
- `Asking_the_tram_driver_for_directions:1` — “Przepraszam, czy tym tramwajem dojadę do centrum?” / “Excuse me, does this tram go to the city centre?”
- `Asking_the_tram_driver_for_directions:2` — “Tak, ten tramwaj jedzie do centrum.” / “Yes, this tram goes to the centre.”
- `Asking_the_tram_driver_for_directions:4` — “Proszę wysiąść na przystanku \"Centrum\".” / “Please get off at the ‘Centrum’ stop.”

**Guarded unsuitable legacy recordings**: `Getting_Around_1:23` (“Idzie pan/pani w dobrą stronę”) is `practice_only` owing to spoken address alternatives; `Road_Terminology:10` (“Jak dojść do …?”) and `Transit_1:4` (“Przepraszam, jak dojadę do …?”) have unfinished destinations. None enter the T06 pilot or any validated scored Speak source. There is **no verified left/right/straight-ahead turn sequence, pedestrian request+reply+clarification, or short map/sign** among the selected recordings. T06 does not claim those competencies are complete.

The T07 *public transport* future unit may reuse original tram dialogue material for a richer ticket/transfer story, but T06 source-only reuse is **not** a new credit, re-recording, ID, spoken response grade, or automatic prerequisite. No expectation to drill Warsaw district names.

## Integration and backward compatibility

- Append a sixth ordered unit to `v2/content/tourist-units-v1.json` as Journey 1 / internal middle only, preserving T01–T05 exactly. No nine-tier titles/hover/help or user-facing rank. Manifest still has `editorialStatus:source_refs_only_native_review_pending`.
- Unit and original-audio validators reject missing source/MP3, unsafe `practice_only` phrase, wrong mode, duplicate/unsorted ID or personal lesson. Existing `tourist-editorial-gate.mjs` continues protecting T01–T03 review status and blocked speech.
- Preserve the A-05 source-ID-validated local `ptp-v2-tourist-activity` record. Existing T01–T05 saved attempts and cursors remain valid; T06 gains its own optional `N / 16 tried`/Resume with real practice actions only. V1 local backup schema and atomic rollback remain unchanged.
- Unit tests pin original Polish/English source identity, protected/missing audio rejection, and old activity migration. Desktop/mobile E2E cover 6 unit cards/16 Listen-Speak-Read entry points, T06 mode/audio/text and optional resume, and unchanged explicit Home core cursor. All original 26 lesson sources, 482 items, 455 MP3s, 14 protected reference entries and Numbers 1–20 10+10 optional split remain untouched. No XP, family consent/privacy, caching, speech provider or scoring code changes.

## Native/editorial work still required

Human language reviewers must author and approve a short pedestrian asking-for-directions exchange with **turn left, turn right, go straight**, natural polite register (pan/pani where needed), a repeat/clarification reply, and a short real sign/map-text exercise. Then approve recorded exact-text multi-speaker Polish voice with provenance and checksums. Do not treat this synthetic integration as native/audio certification. T02/T03 [#126](https://github.com/AndrewDionne/LearnPolish/issues/126) and T04/T05 [#129](https://github.com/AndrewDionne/LearnPolish/issues/129) human blockers remain open. T06 pedestrian editorial work is tracked separately.

## Merge gate

Require **all four** jobs PASS at the final PR head: frontend migration/TypeScript/Vitest/build/desktop+mobile/browser/audio/offline/a11y; connected family; private family backend; benchmark. Physical iPhone/Safari/live mic, paid provider tests and production cutover are still deferred.
