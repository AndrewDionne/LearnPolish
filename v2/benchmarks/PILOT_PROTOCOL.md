# Polish pronunciation AI pilot — controlled study protocol (2026-10-17)

**Research-only, not an AI provider decision or a production pronunciation grader.**
No real Whisper or Azure inference has been run. All experiments must be explicit,
consented and free-first: **no paid API calls, upgraded plans, auto top-up, or silent model downloads**.
GitHub is the continuity record, never the storage location for identifiable voices.

## Questions we need to answer

1. Can a multilingual recognizer **identify the intended Polish word** from an English-first learner?
2. Does Azure `pl-PL` pronunciation assessment **separate native, intelligible-with-errors,
   and hard-to-understand speech** accurately enough for useful feedback?
3. Can either candidate **localize the wrong sound** rather than just saying the whole
   word was inaccurate? Are errors consistent on identical recordings?
4. Can an explainable second-stage phonetic component produce reliable **actionable
   guidance** for `sz/ś`, `cz/ć`, `ż/ź`, `c/cz`, `ł/l`, nasal vowels and
   clusters/stress, without fabricating phoneme identity?
5. What are false failures on native Polish, false successes on deliberately
   changed sounds, inconclusive rates, privacy, latency and recurring costs?

**Crucial vendor limitation (official docs checked 2026-10-17):** Azure explicitly
supports Polish `pl-PL` pronunciation assessment, with accuracy/fluency and
word/phoneme *scores*, but Azure's **named phoneme labels**, **spoken-phoneme
alternatives**, **syllable groups**, and **prosody assessment** are not supported
for Polish in the same way as `en-US`. Do not infer a particular Polish phoneme
from its *position* in an unnamed score array. Whisper large-v3 is ASR:
transcription accuracy is NOT a sound-level assessment.

Sources:
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/speech-to-text

## Small first pilot (adults only)

Start with **12 short Polish stimuli**, two distinct takes each (24 recordings
per adult). Plan a learner and a native-speaker control if they separately consent;
with two such speakers, **48 takes** should fit comfortably within our
100-recording/600-second benchmark cap. Speak naturally at normal pace; record
one word/short phrase per take; use the same microphone for paired providers,
not necessarily between people.

Representative targets to find in existing built-in/personal learning sets:
- `sz` vs `ś`: **szafa / siostra**
- `cz` vs `ć`: **czapka / ciasto**
- `ż` vs `ź`: **żaba / źle**
- `c` vs `cz`: **cena / czysty**
- `ł` vs `l`: **łódź / lody**
- nasal vowels `ą` vs `ę`: **wąż / węże**

These are **sound contrasts**, not strictly linguistic minimal pairs.
They are study prompts, NOT an automatic addition to learner content.
Use the exact intended words from the actual lesson catalog where possible;
the corpus builder will reject uncatalogued item IDs. Deliberate incorrect
pronunciations, stress and consonant clusters can be added in a *second*
consented pilot using separate private references.

**Do not use child voices for the first research corpus.** A later study
involving minors needs specific guardian consent, child-appropriate data
handling, provider retention review and deletion controls before recording.

## Collect reproducible audio

1. Record each selected word using the V2 **Speak** mode. Click
   **Save 16 kHz WAV for private AI test** for each take. A normal lesson
   attempt does not upload/export automatically.
2. Place WAV exports in an **unshared private folder in ignored `repo/temp/` or outside the repository**,
   without names, accounts or children’s identifiers. Each filename encodes its
   catalog item ID and capture time; IDs and intended text might be visible
   in filenames, so an independent listener should not see filenames or
   this manifest *before* the blind first pass.
3. From the cloned repository, generate current built-in references:

       cd v2/frontend
       npm run content
       cd ../..

4. Build and dry-check the private audio corpus (does not call AI):

       python v2/benchmarks/corpus.py --audio-dir "/private/path/polish-pilot" --catalog v2/frontend/public/generated/lessons.json
       python v2/benchmarks/benchmark.py --manifest "/private/path/polish-pilot/manifest.json" --engine dry-run

5. Create a separate never-overwritten human review sheet:

       python v2/benchmarks/pilot_labels.py init --manifest "/private/path/polish-pilot/manifest.json" --labels "/private/path/polish-pilot/human-labels-rater-A.json"

   This is an **unrated** template. It deliberately sets outcomes to `null`;
   there are no fabricated test scores. Keep independent labels for each rater
   rather than sharing the intended answers in advance.

6. Have a fluent Polish reviewer listen **without seeing intended text**.
   Write `heard_without_reference` (empty string if nothing intelligible),
   then label `intelligible`. On a **separate reference-aware pass**, mark
   `target_correct` and any clearly audible `sound_error_tags`.
   `sound_error_tags: []` means *actively reviewed and no tag observed*;
   `null` means *not reviewed*. Mark audio quality
   `clear/noisy/clipped/silence`; `stress_correct` may be `null`
   when not assessed. Do not guess sound errors from machine transcripts.
   Include simple reviewer notes, with no personal identifiers.
7. Validate completion **without running inference**:

       python v2/benchmarks/pilot_labels.py check --manifest "/private/path/polish-pilot/manifest.json" --labels "/private/path/polish-pilot/human-labels-rater-A.json"

A second independent fluent reviewer is strongly preferred; preserve
disagreements instead of adjusting labels until they match. Keep a separate,
explicit consent/retention record privately, not in Git.

## Controlled model stage — requires real evidence and account check

- **Whisper large-v3**: first try the already supported local
  `--engine whisper-local` with a **pre-downloaded actual large-v3
  model directory** and optional `faster-whisper`. No model download,
  remote API call or price is implied. If local hardware cannot run it,
  Groq offers a Whisper large-v3 free API plan, but check the **actual
  account's remaining limits and billing status** before approving requests.
  Groq documents a **10-second minimum billed duration per file** even for
  shorter audio (relevant to future unit economics), and the free-tier
  per-file limit differs from the developer tier. Do not assume provider
  use is free simply because the web app is free.
- **Azure**: only after checking the active Azure Speech F0 resource and
  billing protection; produce a fresh raw `pl-PL` scripted pronunciation
  result for the **exact same WAV checksum and intended reference**.
  Store native JSON privately. Prefer a clean reference-aware assessment,
  not the legacy app's lexical mismatch or time/energy multipliers.
  Parse it using `--engine azure-raw`; this is local parsing, not an Azure
  call. Do not infer named Polish phonemes when the API does not provide them.
- Run the existing `compare.py` only with real matching provider results
  and independent labels. Its current exact-ASR-match-vs-intelligibility
  summary is a *limited recognition proxy*, **not a phoneme metric**.
  Annotate where human-recognized intent and phonetic correctness diverge.
  No provider may receive audio without informed consent and retention review.
- Reserve repeated exact WAVs to measure **service score stability** and
  a separate noisy/blank control set to test **inconclusive** handling.
  A 0% pronunciation failure is not an acceptable replacement for silence
  or corrupted audio.

## Pilot acceptance and decision

Do not select a provider from a single overall number. Review evidence in
five columns: **(1) intended-word recognition, (2) false native failures,
(3) expert-rated sound-error localization, (4) inconclusive/capture handling,
(5) latency and ongoing price/privacy**. Record disagreements and failures
individually with immutable audio hashes; don't choose undocumented weights
or promise exact `cz`/ `ć` coaching until a phonetic method validates it.

Only once adult pilot evidence is sufficient should we decide whether to
ship Azure scores, use Whisper for recognition alongside a separate scorer,
or keep pronunciation feedback qualitative and repeat/listen-focused.


## Ready-to-run Groq comparison (added 2026-10-17)

After consented adult WAV capture, reference-verified `manifest.json` and
two-pass human labels, `groq_pilot.py` now makes it possible to compare
**Whisper Large v3** and **Large v3 Turbo** on the same SHA-256-locked bytes.
Its default is preview-only with zero API calls. Use the [benchmark README]
(README.md#groq-whisper-large-v3--turbo--explicit-free-tier-research-runner)
for exact Mac key entry, account-free-tier confirmation and one-recording,
two-model hard-capped execution commands.

Transcripts from either model measure word recognition **only**. They cannot
show that a particular Polish phoneme was articulated correctly. Both models
share one Groq API key and account; no live evaluation has been run in CI.
