# V3 decision record — native SwiftUI, account-optional and local-first

**Date:** 2026-11-08  
**Status:** approved direction; native implementation in progress  
**Repository:** `AndrewDionne/LearnPolish` (same repository; V2 stays intact)  
**Branch:** `ai/v3/swiftui-local-first`

## Locked product decisions

1. **Real native iPhone application.** SwiftUI is the primary V3 learning interface. Not a WKWebView, website wrapper, empty prototype, or separate repository.
2. **No mandatory sign-in.** First launch goes immediately to a real lesson. No email, password, account creation, iCloud authorization dialog, subscription prompt or profile form to begin learning.
3. **Local-first and offline-capable.** The app persists learner state on the device without network access and bundles actual existing curriculum and licensed/reference audio for offline playback. No fabricated audio or linguistic approvals.
4. **Preserve V2 assets, learning contracts and stable IDs.** The V2 curriculum remains the versioned source while migration is in progress. Do not erase or edit legacy source IDs, core progression, lesson prerequisites, review semantics, XP policies, or privacy/consent requirements.
5. **Account and cloud are optional capabilities.** Investigate optional Apple iCloud private sync first. Actual CloudKit sharing, conflict resolution, Apple entitlements and child/guardian flows must pass an independent spike before replacing any backend or promising cross-device persistence.
6. **Keep existing Neon/Render family backend and four tester identities untouched.** Do not migrate, provision, reset, revoke or auto-sign-in accounts. The family service remains the authoritative source for shared XP/group memberships until a tested replacement exists. Optional connected family login is a later separate flow, not a first-run gate.
7. **Local capture, consented remote speech only.** AVFoundation-based capture/playback and replay are local. Azure/Whisper scoring requires explicit permission, credential-safe server mediation and real acoustic testing. No keys embedded in client, no fake pronunciation or syllable scores, no automatic remote uploads.
8. **Keep minimal UI.** Focus on the learning path, Listen/Read/Speak, clear feedback, 0.75x/1.0x playback, and simple continue/retry controls. Do not introduce onboarding tutorials or unrequested gamification.
9. **SwiftUI becomes the primary learner client.** The React/Vite V2 implementation stays runnable for parity tests/reference and the existing API; no parallel V2 feature expansion solely for UI parity.
10. **GitHub as durable source.** Implement via reviewable draft PR, tests and clear physical-device release gates. Never claim an untested Xcode build is certified.

## Architecture

```
SwiftUI iPhone client
  ├─ Bundled, versioned V2 lesson manifest + mapped MP3 assets
  ├─ Native lesson navigation + local assessment/review engine
  ├─ Application Support / atomic local progress store
  ├─ AVAudioPlayer and AVAudioRecorder for sound practice
  └─ Optional future connectivity:
      ├─ iCloud private sync (only after signed-in entitlement/conflict testing)
      ├─ secure V2 family API / Neon for group participation
      └─ consent-gated private speech assessment API
```

A locally generated anonymous profile ID is an internal record key, not an app account; no network transmission or onboarding consent is implied.

## Explicit non-goals in first native tranche

- No automatic CloudKit sync or silent linking to an Apple account.
- No bypass of backend authentication or public unauthenticated group score submission.
- No replacing V2 backend, deleting hosted data, or modifying live tester credentials.
- No claiming provider-calibrated syllable scoring or certified content beyond V2 evidence.
- No shipping to children, App Store or production before privacy, acoustic and on-device testing.

## Native delivery sequence and completion gates

- **A. Foundation:** compile and validate native projection of existing `lessons.json`, preserve original IDs and audio paths, enforce no duplicate IDs or missing media, add deterministic catalog tests.
- **B. Functional SwiftUI:** Home/Continue, lesson library and filters, Learn, Listen, Read, Speak (local record/replay), local progress and review, native iPhone icon/launch and recovery from restart. Real bundled lessons; no demo fixtures masquerading as release data.
- **C. Progress parity:** compare native outcomes with V2 on representative lessons, test atomic persistence, mode separation, card batching, last position and review scheduling.
- **D. Connected service spike:** iCloud availability and failure modes, CloudKit conflict strategy, sharing model and family/minor privacy; leave Neon family API isolated until demonstrated parity.
- **E. Physical release gate:** Xcode iOS simulator build plus owner iPhone test: first-run without account/network; Listen 0.75/1x; Speak mic permission, recording and replay; full lesson; force quit/relaunch; offline; eventual grouped account permissions and real provider speech assessment.

## Migration protections

Existing `v2/frontend`, `v2/server`, `docs/sets`, `docs/static`, `ptp_v2` Neon schema and production Render configuration are **not** changed by the V3 native tranche. Generation reads the current V2 catalog, does not mutate it. `main` merges only after relevant GitHub and device verification.

## Status of this tranche

Record and implementation are proposed on a draft PR branch. Passing static validations does not prove SwiftUI Xcode compilation; report precisely which checks have and have not run.


## Owner refinement, 2026-11-11: activity-centric learning

The old per-card Learn/Listen/Read/Speak picker is an interim migration design and is superseded by the approved objective to curate a single sequence with distinct Speak (original audio + meaning + speaking feedback), Learn (vocabulary recognition/retrieval, optional flip card) and Listen (real dialogue comprehension). Home is a personal and optional team progress dashboard, not a course list; Library is browse-only and organized into small source-backed journeys plus Extras; Practice owns all started, paused and resumed activities. Only genuine results may appear as scores, and pronunciation grading requires independent acoustic/provider acceptance. See [UX_LEARNING_ARCHITECTURE.md](UX_LEARNING_ARCHITECTURE.md) for the current implementation phases and release gates.

### UX-02A exercise evidence contract — 11 November 2026

Legacy `learn` record `completed/attempts` may mean self-rated recall;
**never call it objective accuracy**. New multiple-choice matching is always
source-option based and tagged `NativePracticeEvent.Evidence.matching`, while
source-audited contextual dialogue answers are tagged `.dialogue` and logged
under the original last source item with mode `.listen`. Optional evidence
tags and optional counters preserve old `LocalLearner` JSON files, imports and
full journal projection. Ungraded flashcards, Replay/Play and Skip award no
attempts or XP. Original MP3s and optional consenting pronunciation service
are unchanged. The ordinary card mode picker is removed; a source-derived
deterministic Speak/Match sequence is provisional pending the curriculum
dependency audit. Only existing 3 V2-authored micro-dialogues are genuine
Listen tasks at this stage. Guided foundation groups await UX-02B migration.

### UX-02B — source-backed guided exercise phase contract (2026-11-11)

Keep **all 16 original guided foundation groups** and original item IDs,
Polish text, English meaning, grammar cues, and recorded MP3s. Teaching begins
with recorded Speak practice for each original phrase; once a group contains
at least three distinct *original same-group* meanings, give a true 3-choice
matching recap (objectively tagged `Evidence.matching` on original source
item IDs). The first two-word Tak/Nie group must **not** invent a third
choice. Progress is a persistent independent optional phase/index cursor per
guided group; legacy V3 `learn` self-ratings remain prior participation but
are not converted into objective matching accuracy. No XP for Play/Skip/
reveal or mere navigation. True Polish syllable score remains separately
uncertified. See [UX_LEARNING_ARCHITECTURE.md](UX_LEARNING_ARCHITECTURE.md)
and the V3 execution ledger for native XCTest gates.

### UX-03A — one source-validated Journey 1 navigation path (2026-11-11)

Replace parallel Guided Continue and Core Continue with one 35-activity,
8-chapter **Journey 1** after the owner's iPhone UX review: first words,
five original sound contrasts, practical vocabulary, beginner sentences,
recorded early listening, everyday situations, and practical conversations.
Exactly 16 original guided groups and 19 original Core Journey 1 lessons
remain; their V2 media, word/lesson identities and user attempt ledger are
never duplicated. Moving sounds before the lengthy first original greeting
source lesson intentionally changes the old *pilot* ordering, not original
recordings or approved Polish. Each activity can be opened in Library but
**runs in Practice**. Home offers the first not-practised source entry,
not the last opened lesson; no hard locks, required percentage or XP for
Skip. Chapters report real attempted activity progress and objective
matching only where actual answers exist. One next-route works through
the guided/core boundaries. User's history remains in its existing local
profile and the 55 shared source IDs are reused, not cloned.

Only author-declared concept prerequisites are currently verified; this
is navigation/identity coherence, **not independent human certification**
of all first-use vocabulary, letter sounds or grammar. UX-03B must extend
the current guided-only first-use ledger to all 19 core lessons and
address every verified gap using authorized original teaching content.

### UX-03B — single authored V3 Journey 1 source manifest, first-use gate (2026-11-11)

The source-backed 8-chapter, 35-activity native course order MUST come from
`v3/content/journey1-unified-v1.json`, not a divergent manually-maintained
Swift tuple. Native source preparation validates the same 16 original guided
and 19 original core IDs and the app loads that exact generated JSON. The
full original-item written-form ledger in `v3/JOURNEY1_UNIFIED_FIRST_USE.md`
is generated from V2 and checked byte-for-byte by CI, with every human
linguistic/audio review status PENDING. Sound exemplar exposure is not
automatically an independent word-meaning introduction.

An introductory **Learn** three-choice match must NEVER use an English
translation taken from a later source card in the same lesson. Initially
the source-wide audit found 68 candidate premature-card quiz cases. The
new `NativeExercisePlan.choices` uses the exact original English gloss
and two distinct earlier original source-card glosses. Without two earlier
meanings, continue with Speak, not a fabricated distractor. Scheduled
spaced-review exercises retain their own flow. No new source IDs, attempts,
XP, cloud accounts, or backend connections. Seeing an earlier card does not
prove its mastery; independent human-first-use/inflection/acoustic signoff
and deliberate repeated retrieval remain separate release gates.

### UX-03C1 — record-backed introduction-before-match (2026-11-11)

A first-contact original Polish phrase **must never** open directly as an
objective Learn test. The source-cadence `NativeExercisePlan.mode` is only
a proposed revisit; runtime `mode(for:records:)` requires a saved
`speak:<item>` or legacy `learn:<item>` attempt for the target and
at least two distinct *earlier* source items with genuine saved practice
records. Polish/English and original MP3 references remain exact. A
successful usable-recording **Mark practised** can immediately transition
the same item to a graded source-only Learn question. Skip, Play, Return
and Show Meaning give no practice event or XP. No forced locks or 80-percent
thresholds. Previously credited legacy self-rated Learn attempts may
signal earlier exposure but are never turned into objective correctness.

Scheduled source Learn reviews can draw distractors from any previously
practised original same-lesson items, never future unpractised entries.
If only 0/1 alternatives are eligible, use an explicitly **self-rated**
reveal instead of manufacturing options or a matching score. Existing
Daily Review scheduler and historical XP are unchanged. Neither a prior
attempt nor the full automatic first-use report certifies human lexical,
phonetic or syllable mastery. Physical headset acceptance remains open.

### UX-03C2A — optional source-backed interleaved reinforcement (2026-11-11)

Practice may offer a short optional cross-chapter reinforcement set using
no more than six **original, previously practised** recorded vocabulary
items from completed earlier Journey 1 chapters. Do not reissue identity,
Polish text, English meaning or audio; do not expose unintroduced later-
chapter words, sound contrast-only examples, flagged `practice_only` media,
or English distractors without saved source practice. Objective answers
are actual `learn:<original item>`+`Evidence.matching` events in the
existing atomic offline review/XP journal and enter the original review
schedule. Playback, Skip and preparation never count. Reinforcement does
NOT fabricate new due dates or override Daily Review and does not replace
human linguistic mastery/certification.

Original vocabulary **practised counts** cannot regress when Speak makes
a word newly eligible for an additional Learn recap; count the original
source Speak-or-Learn attempt once. For Numbers 1–20, preserve the 1–10 /
11–20 sections, using actual recorded exposure to decide which subsection
should resume.

Existing authentic dialogue activities may show exact original lines/
glosses in an optional ungraded preparatory disclosure for lines with no
recorded source exposure; the comprehension question is still assessed
only on a submitted answer. This does not claim entire phrase/syllable
comprehension or physical headset playback certification.

### UX-04A — UI navigation / optional real pronunciation result (2026-11-11)

Pause further substantive Polish curriculum refinements for a focused owner
holistic iPhone review after Home/Library/Practice/Expedition/Progress tabs
fulfil their separate roles. Home activity and today-local XP are actually
stored source events, not duplicate Library tiles or invented team scores.
A connected adult sees only read-only server-provided weekly team XP,
member count and unlocked regions from the selected first connected group;
without a verified connection no team totals are shown or estimated.
Refresh never transmits new personal learning events.
Library browses original chapters and Extras; launching lessons switches to
Practice. Practice keeps individually paused sets, due review, authentic
Speak, Learn and Listen. Expedition remains the genuine 16-region XP map.
Progress starts with real chapter/attempt/matching/XP metrics; private backup,
restore, merge and optional family controls move into a nested Data and
account screen, retaining all prior permissions and confirmation gates.

The visible Speak result combines exactly **one original, source-bound Polish
word**, small spaces between genuine source pronunciation segments, coloured
transcript-proxy hints and **one experimental Azure+Whisper blended overall
score**, only when the private service returns a valid response after explicit
per-take Azure AND Groq consents. Green/orange/red are NOT independent
acoustic syllable percentages. No connection, rejected, or inconclusive
response gets a fabricated display. Offline recording/replay still works
without sign-in; optional adult verified connection is discoverable directly
from Speak without mandating authentication on launch. Main vs guided Speak
must use the same presentation. Keep PR #169 draft until owner physical
headphone/recording/provider/UI review, not simply green simulator CI.


## Owner override — 2026-11-12: pronunciation is first-class without an account

Supersedes the V3 requirement to connect an adult private family account and separately opt into Azure/Groq as the user-facing route to basic pronunciation review. Every Speak exercise should play existing original Polish audio, record/replay on the iPhone, and automatically produce **source-grounded multicolour recognized-transcript feedback and one overall text-match estimate** from the real on-device multilingual speech recognizer. No Family form, service URL, user credentials, new accounts, remote speech providers or uploading personal recordings. A first model install can use public model hosting; subsequent inferences are offline. Transcript agreement is a useful first native review but is *not* independently proven phonetic/syllable acoustic grading. Genuine acoustic accuracy calibration remains separately outstanding. Preserve the old backend/family accounts; remove sign-in screens from the current native learning flow.
