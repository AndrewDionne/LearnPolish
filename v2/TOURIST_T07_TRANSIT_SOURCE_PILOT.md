# B-06 — T07 Taking a tram and buying a ticket: source-only pilot

**Status:** software source-integration candidate; native review and real microphone/Safari testing deferred. Based on certified B-05 source and GitHub main `ea1a1b4e94fe6ce3f7be958ee92a310c6d3e8701`.

## Learning purpose, exact original assets

T07 intentionally revisits and extends T06's real recorded tram-driver scene: T06 includes source turns 0–4 about the route and stop. T07 retains those turns and adds turns 5–7, which contain **a question about buying a ticket aboard the tram, the driver's recorded answer mentioning a ticket machine, and a closing thanks**. This is *one* existing source, not independent recordings or a full travel announcement. Individual spoken requests come from the original Getting Around set. The target is to recognize a simple transit exchange and practise basic ticket/platform questions—not to master transfer rules, fares or a live transport system.

| Mode | Exact source lesson | Source indices | Count | What is grounded |
| --- | --- | --- | --- | --- |
| Listen | `Asking_the_tram_driver_for_directions` | `0–7` | 8 | Original recorded question/answer about the centre, getting off, ticket purchase and ticket machine |
| Speak | `Getting_Around_1` | `3,4,6,7,8,9,14,17` | 8 | Existing standalone questions for line/platform, requesting one/two tickets, regular/reduced tickets, price, and purchase location |
| Read | `Asking_the_tram_driver_for_directions` | `0–7` | 8 | Original short conversational text with existing Read mode; no invented public notice |

Immutable exact source and English checks include:

- `Asking_the_tram_driver_for_directions:5`: **Czy mogę kupić bilet w tramwaju?** / “Can I buy a ticket on the tram?”
- `Asking_the_tram_driver_for_directions:6`: **Tak, może pan kupić bilet w automacie.** / “Yes, you can buy a ticket in the machine.”
- `Asking_the_tram_driver_for_directions:7`: **Dziękuję bardzo, do widzenia.** / “Thank you very much, goodbye.”
- `Getting_Around_1:3`: **Na którą linię?** / “For which line?”
- `Getting_Around_1:4`: **Który to peron?** / “Which platform is this?”
- `Getting_Around_1:6`: **Jeden bilet, proszę** / “One ticket, please”
- `Getting_Around_1:7`: **Dwa bilety, proszę** / “Two tickets, please”
- `Getting_Around_1:8`: **Bilet normalny** / “Regular ticket”
- `Getting_Around_1:9`: **Bilet ulgowy** / “Discounted ticket”
- `Getting_Around_1:14`: **Ile kosztuje bilet?** / “How much is the ticket?”
- `Getting_Around_1:17`: **Gdzie mogę kupić bilet?** / “Where can I buy a ticket?”

**Important distinction:** the original story's statement about a ticket machine is **dialogue content**, not verified, current public transport ticket-sales policy. No current timetable, fare, route number, stop announcement, correct service direction, transfer, platform reply, disruption handling or new mobile ticket purchase instruction is approved. T07 does **not** claim any of these competencies. The named **T07 native editorial blocker** requires a genuine answer about lines, stops, tickets and connections, an authentic sign/timetable Read task, and recorded reply voice checked line-for-line. Real-time Warsaw transit data is outside this application's lesson-content scope.

The known protected `Transit_1:4` (“Przepraszam, jak dojadę do …?”) remains excluded because its destination is unfinished. `Getting_Around_1:23` and `Road_Terminology:10` remain restricted, and no `practice_only` item enters source-backed Speak. Original source files and 455 inherited MP3s remain unchanged.

## Progression and compatibility

- Append **T07** as internal Journey 1/middle, order 7; keep T01–T06 byte-equivalent in the source manifest. Seven existing topic cards now expose **19 real mode actions** in the Library. No user-facing 3×3 stage names, hover tips, accessible-label stage annotations or course gates.
- Preserve single original Numbers 1–20 source with optional 1–10 / 11–20 practice, personal lessons, family consent/XP, saved Home course cursor, source/migration test guards, offline and audio engine.
- Current A-05 `ptp-v2-tourist-activity` local-only schema remains version 1, validation accepts T07 source IDs and keeps saved T01–T06 attempt records. The same recorded item may be practised in T06 and T07 but **unit/mode activity is never merged** or used as a skill grade. Old backups continue to load unchanged; a new T07 entry only appears after voluntary learner activity.
- Validators fail closed on wrong order, altered source mode, missing source audio, accidental `practice_only` status or personal content substitution. T01–T03 B-03 native review packet stays unpublished. Source-lock tests pin exact Polish and English; desktop/mobile E2E cover original ticket request in Listen, distinct Speak phrase, reading, zero-attempt Resume, and independent Home course cursor.

## Editorial gaps and acceptance

For a **complete** T07 public transport outcome, native-reviewed content must include a realistic tram/bus route number and line, which direction/platform to take, a validated ticket/fare/validation dialogue, transfer or interruption clarification, and an authentic route sign/timetable text. Verify natural register, numbers, gender-appropriate forms, English meaning, recorded audio aligned to every approved turn, rights and provenance. Do not convert original phrase recordings into fictional conversation or infer pronunciation mastery from a completed click sequence. Separate native editorial issue records these requirements. Earlier human review blockers [#126](https://github.com/AndrewDionne/LearnPolish/issues/126), [#129](https://github.com/AndrewDionne/LearnPolish/issues/129), [#132](https://github.com/AndrewDionne/LearnPolish/issues/132) remain open.

## Merge authority

Require all **four CI lanes** at **final PR head**: migration/TS/unit/build/full desktop-mobile/offline/audio/a11y, connected-family browser, private backend and benchmark. Passing synthetic CI is source/software certification only. No physical, paid speech model, deployment or real-world transit-policy certification.
