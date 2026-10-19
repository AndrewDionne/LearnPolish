# Path to Polish — Syllable-highlighted phonetic similarity, first scoring tranche

## Product decision

The owner proposes a deliberately minimal pronunciation feedback UI:
**one coloured word split by syllables, one phonetic similarity estimate,
and tap-to-expand differences between the target and the transcript**.
The highlighted letters/digraphs identify which Polish combinations
deserve practice. This is more useful than leading with a provider's
aggregate 84/100/100 score or a paragraph of advice.

**Important measurement boundary:** Whisper returns a written ASR
transcript, NOT a verified IPA/phone sequence. It can hallucinate a
plausible word or transliterate sounds inconsistently. We CANNOT claim
this is exactly what a learner pronounced, and cannot yet give a
human-calibrated pronunciation percentage, even though the original
Świętokrzyska recording owner confirmed the weird transcript resembled
their spoken attempt. Do NOT enforce grades as XP gates.

## Shipped as research prototype (offline, zero providers)

`v2/benchmarks/phonetic_similarity.py` computes a transparent
`ptp-transcript-phonetic-proxy-v1` report from the ORIGINAL adult WAV
plus the ALREADY COMPLETED private Azure and Groq JSONLs. It first
validates those saved files and matching audio hashes using our existing
model harnesses; it never makes a network request or reads API keys.

- Exact *human-reviewed spelling segmentation* for the first word:
  `Świę | to | krzy | ska`. No unreviewed Polish syllabifier is
  implied for all other lesson words.
- Both Whisper hypotheses are normalized into APPROXIMATE Polish
  sound-grapheme units, including common digraphs, `rz` devoicing
  after `k/p/t`, and **equivalent W/V spelling** (do NOT award a
  different pronunciation merely because one Whisper model writes V).
  Spaces in hallucinated split words are ignored for sound alignment.
- Weighted unit-level edit alignment maps substitutions, deletions,
  and extra recognized units to the intended syllables; similar
  grapheme sound classes incur partial costs. The provisional
  similarity formula is `max(0, 1 - sum(edit_cost)/number_of_target_units) * 100`.
  The weights are EXPLICIT researcher hypotheses, not acoustic or
  human-calibrated evidence.
- Scores are exposed per syllable and overall. When Whisper models
  disagree after normalization, show the range, mark **uncertain**
  in neutral grey and do not invent one falsely confident score.
- The standalone private HTML review is made of clickable/tappable
  `<details>`, has keyboard focus, visible numeric percentages and
  names along with the colours, and no JS, analytics or remote assets.
  Green = closer **transcription-derived** match; amber = review;
  red = focus; grey = models disagree. These are candidate
  coaching priorities, NOT verified speaker errors.
- The report lists the expected vs hypothesized SOUND UNITS and edits
  per syllable; it does not fabricate word timestamps, real
  recorded phonemes or precise tongue-position diagnoses.
- No automatic provider requests, storage in the family profile,
  scoreboard/XP gate, backend routes, or secret in the browser.
  Our existing live Speak UI remains unchanged until scoring is
  validated and its audio source appropriately connected.

## Use the ALREADY TESTED owner Świętokrzyska recording

From `path-to-polish` repository root, **after merge**:

```bash
git pull --ff-only origin main

WAV='PathToPolish-Private-AI/swietokrzyska-01/ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav'

PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/phonetic_similarity.py \
  --wav "$WAV" \
  --azure-result PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl \
  --whisper-result PathToPolish-Private-AI/swietokrzyska-01/whisper-01.jsonl \
  --html-output PathToPolish-Private-AI/swietokrzyska-01/phonetic-review-01.html

open PathToPolish-Private-AI/swietokrzyska-01/phonetic-review-01.html
```

This makes **ZERO Azure, ZERO Groq** requests. It only creates a NEW
owner-private `.html` (0600) next to existing research files and
prints the reproducible proxy data locally. If the output file
exists, it REFUSES to overwrite; open the existing file or choose a
new name. No saved audio, Azure, Groq evidence is modified. Never
copy/publish the private HTML: it contains Whisper's transcription
of your voice. It is gitignored, NOT encrypted. If you want to review
just the JSON without creating a file, omit the `--html-output`
argument.

## Interpretation and acceptance

The literal earlier Whisper outputs were `Sweczo Seska` and
`Sveczo Seska`. Their W/V difference is treated as a **proxy match**,
not as a speaker error; their other spelled units produce candidate
differences. The `-ska` ending should score better than at least
some of the other target syllables. **Do not mistake the resulting
percentages for phoneme measurements**: the hypotheses are
nonstandard written forms, not raw audio transcriptions.

This first tranche establishes an understandable model/data/UI
contract, NOT a final grading system. Before publishing it as
learner-facing scored feedback, compare it against verified native
and human-reviewed learner audio, improve Polish phonology and
uncertainty handling, and decide whether actual speech alignment /
phoneme posterior data is required. The next approved tranche should
integrate **the same component** into the real Speak UI without asking
families to import files or copy Whisper transcripts manually.
Keep practice/replay/Next functional whether any provider works or not.
