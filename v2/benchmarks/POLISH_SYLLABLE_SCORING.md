# Polish V2 syllable scoring — acoustic evidence gate (2026-10-20)

## Actual provider boundary (verified against Microsoft Learn)

- Polish `pl-PL` is a supported locale for **scripted** pronunciation assessment.
- Azure documents Polish full-text, word and phoneme **numeric** accuracy
  scores, but named phonemes and **native syllable groups are en-US only**.
  Therefore don't assume an automatic `Świę | to | krzy | ska` grouping
  exists in Azure's Polish output. Do not divide `AccuracyScore=84` into four
  grades, or treat Whisper `Sweczo Seska` as direct acoustic measurement.
- The provider scores are uncalibrated for our family's learning experience,
  especially for misread or repeated difficult words. A native control and
  labelled learner samples are required before presenting syllable percentages
  as meaningful user-visible estimates.
- Microsoft references:
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment

## Implemented, no voice data or paid requests

- `v2/frontend/src/speech/assessment.ts` now defines reserved
  `reviewed-acoustic-syllables-v1` feedback with an exact reference and
  every written syllable, numeric score `0..100` or **null for inconclusive**.
  Malformed/mismatched/Whisper text hypotheses get dropped. The existing
  production `speech_assessment.py` emits **NO syllableFeedback**.
- `SpeakPanel.tsx` is capable of showing the segmented Polish word with
  optional coloured score labels even when **Pronunciation guide is OFF**.
  When ON, approximate English cues appear beneath the same Polish syllables.
  A score missing from the assessment shows a dash, never an invented zero.
  Scores reset when starting another take and do not affect Repeat, Next,
  optional sound-practice navigation or XP.
- A **mocked** connected-browser scenario demonstrates `Świętokrzyska`
  with several numerical test values and a null segment to verify the
  visual contract; this is expressly synthetic and never a claim of
  successful Polish speech assessment.
- `v2/benchmarks/polish_phoneme_evidence.py` examines one already saved
  private **Azure raw JSON** purely offline. It counts structurally valid
  word/phoneme/natively grouped numeric score fields and reports whether
  ordered phoneme scores exist. It does **not** infer alignment, print
  the transcript, return raw syllable scores, or perform any network call.
  Raw human voice, phoneme arrays and keys stay on the owner's Mac.

### Offline evidence probe — from project root on owner's Mac

Only if a prior, explicitly approved benchmark already saved full Azure SDK
JSON under the ignored private `PathToPolish-Private-AI` folder, with one
spoken word and `engine=azure-pl-PL-scripted` and `locale=pl-PL` metadata:

```bash
git switch main && git pull --ff-only
python3 v2/benchmarks/polish_phoneme_evidence.py \
  --saved-private-json PathToPolish-Private-AI/<private-folder>/<azure-raw-result>.json
```

The parent directory must be private mode 0700 and the JSON mode 0600. Replace
the placeholders with the actual local, previously obtained path; do not run
a provider call, download new audio or paste raw transcripts, scores/identifiers,
WAV or credentials into GitHub. It prints only structural counts and
`can_publish_syllable_scores: false`. An earlier **sanitized** score/latency
JSON file with no `raw_azure_json` will correctly report insufficient
evidence. The full raw result can also be inspected locally directly via
`inspect_raw` if the report format differs. If there is no existing raw
sample, *do not* try to invent one or auto-run Azure.

## Research questions to clear before live syllable scoring

1. Does the already collected `pl-PL` result actually include **ordered
   phoneme score entries** for the exact single-word reference?
2. Can independent Polish orthographic/phonological segmentation, including
   `świę` and `krzy` devoicing, be aligned reproducibly to those numeric
   entries? No unnamed-phone-to-syllable projection without matching counts,
   timings or an independently validated reference.
3. Do native Polish recordings tend to score distinctly above adult learner
   incorrect/synthetic controls for every syllable? A couple of convenient
   examples cannot establish calibration. Include phones with Polish digraphs
   (`rz`, `cz`, `sz`, `ś`, `ć`) and nasal vowels, multiple voices/accent
   varieties, and scores stable enough to inform retries.
4. Which provider result shapes must fail *inconclusively*, rather than
   displaying 0%? Handle word insertions, omissions, ambiguous timing,
   partial/nonnative output, low signal and NoMatch.
5. Secure a correctly licensed, human-audited exact-word native reference
   recording. A full phrase saying `ulica Świętokrzyska` is not a
   drop-in standalone word reference; do not crop or label it silently.

**Release rule:** do not produce `reviewed-acoustic-syllables-v1` in the
server until actual adult voice experiments and explicit independent
human review support the per-syllable mapping. Keep scoring opt-in,
server-only, no hidden uploads, and zero new paid resources. This is
workable UI/data infrastructure, not a grading accuracy milestone.
