# Speak pronunciation practice — locked learner loop and optional Sound Lab detour

**Owner decision, 2026-10-20.** Supersedes any suggestion that the main
Speak flow needs an automatic letter-by-letter correction or coaching stage.
The intended feature is **credible syllable-level scoring and voluntary repeat**,
with optional linked sound learning sets. This is a product/UX contract,
not a claim that validated acoustic syllable grading is already shipped.

## Primary loop (one existing Speak card, minimal UI)

1. Hear the actual Polish reference recording for the current word/phrase.
2. Record one learner attempt; allow personal replay.
3. Display per-syllable scores **only if calculated from sufficiently reliable
   acoustic/reference-aware evidence** on THIS recording, with appropriate
   uncertainty. Keep a stable one-word display segmented on the word itself.
4. Offer **Record again** on the SAME item and **Next** to move on, with no
   pass/fail lock, score gate, "correct this letter" prose or tutorial.
5. Every new usable take replaces the displayed feedback. Failed/unavailable
   assessment is **not 0%** and never hides playback or disables Next.

**Guide toggle:** Off by default. In either state, scored Polish syllables
may be coloured/highlighted after a real assessment. Turning Pronunciation
guide ON reveals existing English-friendly cues aligned directly BELOW those
same syllables, and the stressed syllable. Turning it OFF hides the English
guide, **not** the scoring of the Polish word. No duplicate Polish word.

**Recording/upload consent:** Microphone capture and private replay remain
local. Where scoring requires remote audio transfer, obtain transparent,
explicit informed user/guardian permission first (a clear session opt-in
can permit score-after-record UX while in scope), then show assessment
results automatically for subsequently authorized takes. No hidden audio
upload, provider changes or costs. In offline/no-quota cases, replay/retry/Next
remain available with scores marked unavailable, never fabricated.

**Score meaning:** Percentages for syllables must mean *calibrated
reference-aware pronunciation similarity*, not character or orthographic
recognition agreement. The old `50 / 50 / 0 / 100` came from the saved
Whisper texts via `v2/benchmarks/phonetic_similarity.py`; it is an
uncalibrated transcription-derived proxy and must NOT populate a learner
pronunciation score. Existing Azure 84/100/100 is aggregate, uncalibrated
accuracy/fluency/completeness and cannot be evenly distributed over four
syllables. If the provider yields only credible word-level scores, show
the word-level estimate or no syllable scores, **never invent splits**.
Use stable, vetted syllable/phoneme timing and independently validated
native/learner audio before enabling real syllable scores. If we cannot
reliably assign a syllable, show `—` / `Not reliably assessed` for that
syllable; do not assign a score of zero. "Correct"/"mastered" threshold is
not invented before human calibration. The learner can self-decide to move on.

## Optional sound-practice detour (not a correction step)

Only when an actually relevant, authored sound-practice set EXISTS,
and credible syllable/sound evidence supports the focus, surface a small
link such as **Practise krzy sounds →** or **Practise cz →** beneath the
assessed word; do not manufacture links or claim specific phonemes were wrong
from a Whisper transcript alone. This is a normal Speak-capable sound learning
set with model/reference audio and the same record → score → repeat loop,
not a standalone explanation or a forced remedial exercise.

- Clicking the link stores a *temporary navigation return context*:
  `{sourceLessonId, sourceMode:'speak', sourceItemId, sourceIndex,
     guideVisible, targetSoundId}` (and any necessary review list/session
  state). No audio blob/token, transcript or score is needed in URLs/storage.
- It opens the existing relevant Sound Lab lesson **at the linked
  sound/group/item**, not an unfiltered catalog or a new modal.
- Sound practice has a prominent contextual **← Back to Świętokrzyska**
  (or source word) link, and **Return to word** when the small practice set
  finishes. Both return to the *exact originating lesson, card and Speak mode*
  without restarting the whole set or advancing XP. Return to an idle,
  ready-to-record state; re-listen and retry that word at the learner's choice.
- Standard Back to library and Next stay functional. Repeated/abandoned
  attempts do not multiply XP; existing effort XP semantics stay independent
  of unverified raw speech scores. Clear temporary return context when
  navigating away entirely. Screen-reader label and keyboard return work.
- No link is a necessary condition for marking a lesson complete or for
  moving to the next word. Direct Sound Lab access from Library remains.

**Important Polish sound distinction:** `krzy` in Świętokrzyska includes
`rz` devoiced after `k` (approximately /kʂɨ/). The existing Sound Lab's
`CZ` group teaches /t͡ʂ/, which is **not the same sound or cluster**;
the existing `Ż / RZ` group uses voiced example words and does not
automatically teach this devoiced `krzy` combination. Do not link
`krzy` to a superficially similar `cz` card. Author/validate a
dedicated cluster/devoicing practice set (with real reference audio)
before showing a `krzy` deep link. Existing curated Sound Lab contrast
lessons for `c / cz / ć`, `s / sz / ś`, `z / ż / ź`,
`l / ł` remain useful for matching sound patterns in other words.

## Current code audit / exact gaps

- `v2/content/pronunciation-swietokrzyska.json`: curated `Świę | to |
  krzy | ska` and English cues, review still marked
  `needs_native_speaker_review`.
- `v2/frontend/src/speech/SpeakPanel.tsx`: recording, replay, optional
  aggregate Azure numbers, Record another take and Next already exist;
  English cues appear only under the Pronunciation guide toggle.
  **No live per-syllable colour/score feedback**.
- `v2/benchmarks/phonetic_similarity.py`: actual numeric per-syllable
  estimates are calculated solely from normalized *Whisper text* and
  displayed only in an owner-private HTML PoC; no acoustic timing/phoneme
  evidence or production API contract.
- `v2/server/speech_assessment.py` and `v2/frontend/src/speech/assessment.ts`:
  transport currently exposes only three Azure aggregate scalars; does not
  convey credible Polish phoneme/syllable scores.
- `v2/frontend/scripts/prepare-content.mjs`: the built-in single-word
  Świętokrzyska Speak item explicitly has **no native example audio**.
  The primary "listen first" loop cannot meet product acceptance for
  this word until an independently reviewed recording is supplied.
- `v2/content/sound-contrasts.json` + `SoundContrastDeck.tsx`:
  Sound Lab provides grouped recorded words with **listen-and-compare**,
  but no scored single-sound take loop, deep link mapping, or return-to-item.
- `v2/frontend/src/App.tsx`: lesson, index, mode and guide are component
  state; `openLesson` currently resets card/mode/guide, so a Sound Lab
  detour requires explicit scoped return-context restoration.
- Free Render deployment currently disables account/speech provider backend,
  so this is not yet a live scoring feature on hosted V2.

## Implementation order and acceptance, deliberately small

1. Ensure real Polish reference audio for target words and Sound Lab
   exercises, human-review pronunciation/segmentation metadata.
2. Validate a reliable per-syllable acoustic score source against labelled
   adult learner and fluent Polish controls; record which syllable can
   truthfully be graded; do NOT repurpose Whisper text similarity.
3. Expose a compact, provider-agnostic graded-or-unavailable syllable
   result contract and add scores to the SAME Speak word after explicit
   assessment consent. No suggested-correction stage.
4. Add stable `soundId → practiceLessonId + group/item` links where
   genuinely relevant, plus a one-step return context. Add specialized
   `krzy` practice only when its reference audio and sound mapping exist.
5. Run mobile/desktop end-to-end journeys: audio → take → score →
   take again → Next; low-confidence no-score; guide Off/On; sound link →
   relevant sounds → return to *same* original word → record again;
   back/abort, repeat XP dedupe, offline/cost/privacy constraints.

**Design invariant:** short, pleasant and optional; measurement under
the hood can be sophisticated, but visible results are a scored
syllable-highlighted word, retry, next, and (where available) practice
a relevant sound.
