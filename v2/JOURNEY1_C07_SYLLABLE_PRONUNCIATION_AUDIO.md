# C-07 — Syllable-level pronunciation guide and authentic source-audio playback gate

## What exists and what remains missing

C-07 audits the full Journey 1 pronunciation/audio workflow against the actual current source. The content migration already produces a `pronunciationSegments` field on **all 482** items, but most are heuristic **orthographic drafts**; several dozen are editorial drafts, and only the bespoke Świętokrzyska guide has an authored multi-syllable English approximation. They **are not** independently reviewed syllable-by-syllable acoustic transcriptions. Existing **455 imported MP3s** are whole utterance/word files (reused in other curated exercises); *none of them has a verified per-syllable timestamp/alignment or isolated original-voice syllable MP3*.

**This release does not assert that individual syllable audio is already available.** We cannot generate safe syllable offsets from letters, proportional durations, silent padding, or crude `timeupdate` events; doing so would teach cut-off consonants. We also do not silently synthesize unrelated voice syllables from browser TTS or pass fabricated confidence scores to a learner.

### New real learner functionality

- On an original source Learn item, **Pronunciation guide** can now reveal the existing orthographic partitions with small visual spaces, without changing the original spelling, full source word, pronunciation grading, progress, XP, or lesson IDs.
- The same Pronunciation guide in **Speak** now offers those sound-part groupings on ordinary beginner words, not only the previous special Świętokrzyska case. Existing combined Azure/Whisper **whole-word** score, syllable-coloured text and English-cue guide remain unchanged; no experimental per-syllable numerical grades are added.
- Learners can always listen to the **complete inherited MP3** at the existing 0.75×, 0.85× or 1× supported rates. Longer expressions' draft textual groupings should be interpreted as **optional spelling guidance**, not independently reviewed syllable boundaries.
- If an exact source item ever has genuinely accepted independent syllabification **and** sample-accurate source-audio boundaries, a small **clickable syllable button** will play that excerpt from the exact existing original MP3, preserving its own voice. The WebAudio engine fetches/decodes only the original trusted local MP3 and uses `AudioBufferSourceNode.start(offset,duration)` rather than imprecise HTMLAudio `timeupdate` seeking. It respects the selected learning rate, stops cleanly on navigation/recording changes and aborts stale audio fetches. WebAudio is unlocked in the direct click gesture for Safari compatibility. It does not upload audio or call any provider.

The **currently published** [reviewed syllable audio manifest](content/reviewed-syllable-audio-v1.json) is intentionally `blocked_pending_independent_native_syllable_and_acoustic_timing_review` with **zero approved items/segments**. Therefore no "Play syllable" button appears by default, and it would be incorrect to say isolated syllable audio has already been delivered. The correct next step is real alignment/voice review, not UI work.

### Approval and integrity gate

[The original-MP3 timing verifier](frontend/scripts/reviewed-syllable-audio.mjs) is integrated after original audio copying and existing draft segmentation in `prepare-content.mjs`. Only a separate release-manifest review phase accepts any nonempty entries. For each fixed original source item it must verify:

1. Exact existing immutable item ID, Polish text and original trusted audio URL; rejects all `practice_only` Speak-blocked items, missing or changed sources, unknown IDs and duplicates.
2. **Actual binary SHA-256** of the recorded original MP3 (not a text-only fingerprint); source duration independently probed using `ffprobe`, with only a bounded tolerance for codec timing.
3. Ordered, nonoverlapping timing intervals, each with exact Polish syllable text whose concatenation reconstructs the whole original spelling, sane durations and recording bounds. Unreviewed guessed timings are not seeded. Wrong rows fail atomically, without partially granting clips.
4. References to independent native syllabification review, audio-boundary listening review, original voice/rights review and explicit owner release authorization. **Reference strings do not authenticate people or prove language/acoustic correctness.** Evidence must be separately inspected before changing the production manifest.

The generated lesson schema has an additional **`syllableAudio` type**, accepted only for non-personal original/curated lessons and exactly matched to the source audio. It is distinct from `pronunciationSegments` (draft/orthographic). This ensures independent source audio can be surfaced without relabelling drafts as human-approved. Personal imported lessons cannot smuggle approved clip metadata. Backend pronunciation estimates remain whole-word only without independent calibration.

### Release tests and next real content gate

`npm run test:migration` includes new fail-closed source-audio review tests and asserts the **zero** approved segments in the unreviewed production corpus, unchanged original 26 lessons, 482 items and 455 MP3s. Schema/unit negative tests cover incorrect text, time overlaps, out-of-range snippets, fabricated hashes and missing independent evidence; new Playwright desktop/mobile tests cover the Learn and Speak spaced-guide controls, full-word audio, 320px width and deliberate absence of false syllable audio playback. Existing family, offline, XP and tourist modes remain under the normal 4-lane final-head CI certification.

**Remaining external dependency** tracked in [issue #140](https://github.com/AndrewDionne/LearnPolish/issues/140): obtain independent native-syllable and word pronunciation review, exact-source reviewed segment start/end timing and original recording hash/duration verification. Start with **the 40 existing C-05/C-06 beginner items** and the 19 editorial example words already targeted. Once real evidence exists, commit a **small reviewed batch** with actual playable clips; only then can we honestly claim "syllable-level pronunciation and audio" are available for those items. Do not confuse 482 orthographic partitions with 482 acoustically timed words, or claim the 80% actual Journey 1 teaching-time target is attained.

No paid Azure/Groq inference, native-acoustic QA or real iPhone/Safari microphone test is claimed by this software tranche.
