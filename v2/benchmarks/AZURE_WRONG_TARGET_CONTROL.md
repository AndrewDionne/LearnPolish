# Pronunciation teaching quality — next measured control

## Why this change

The user **actually** ran a successful Azure Speech SDK `pl-PL` assessment
against public native Polish `Dzień dobry` after repairing the Mac's F0 key.
It returned **Accuracy=100, Fluency=100, Completeness=100** for 1.250 seconds.
The earlier public experiment also gave both Groq Whisper models perfect
transcriptions on two phrases (WER=0), but transcription is not pronunciation.

**Critical open product question:** Will Azure avoid rewarding a confidently
spoken but **wrong** Polish phrase? We should test that before treating 100 as
evidence of learner mastery, or spending time on an elaborate feedback UI.

## Exactly one negative-reference experiment (not a simulated phoneme mistake)

- WAV: immutable *Dzień dobry* by Julo from Wikimedia Commons, exactly the
  **same 1.250-second bytes and SHA-256** as the already scored positive control.
- Baseline (already run, do not rerun): Azure reference **Dzień dobry**, raw
  scores 100/100/100, private `azure-only-diagnostic-01.jsonl`.
- New negative: same WAV but expected Azure text **Dobry wieczór**.
- Exactly **one** new Azure Speech `pl-PL` scripted call (or zero by default).
  **No Groq calls**, no re-download, no new account, no hidden cost/retries.
- Paired report gives actual Azure raw score difference for Accuracy, Fluency,
  Completeness, or `inconclusive` without inventing a score. The report never
  labels this a human-calibrated grade or certified phoneme detection.

Microsoft documents `ReferenceText` as the text against which scripted
pronunciation is evaluated, and `EnableMiscue` as a reference comparison
that can report word omission/insertion. These are NOT guarantees the entire
wrong phrase will be scored low. Provider documentation:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment

### Owner Mac commands (from repo root)

The existing private public audio directory is retained untouched.
Use current corrected Azure F0 key in shell; do NOT reprint or commit it.
The regional token-issuer check has already returned 200, but a fresh shell
may have reloaded the old key from `~/.zshrc`. If that happens, redo the
ZERO-AUDIO `python3 v2/benchmarks/azure_auth_probe.py` before any inference.

```bash
git switch main && git pull --ff-only origin main

PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_native_reference_contrast.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --positive-result PathToPolish-Private-AI/public-polish-live-01/azure-only-diagnostic-01.jsonl
```

The above is an **offline preview, no provider inference**. It verifies
the original Ogg SHA-256, audio sample characteristics, normalized WAV hash,
the existing Azure positive response tied to the SAME WAV hash, canonical
prompt and actual three score fields. If a file has changed, it stops.

**Only if still on existing Azure F0 free quota, with no paid billing or
auto-top-up, and you approve sending the public recording again**:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_native_reference_contrast.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --positive-result PathToPolish-Private-AI/public-polish-live-01/azure-only-diagnostic-01.jsonl \
  --send --approve-public-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/public-polish-live-01/azure-wrong-reference-01.jsonl
```

Expected output fields: `network_requests_performed=1`, `groq_requests_performed=0`,
`comparison.same_audio_confirmed=true`,
`comparison.positive_raw_scores_uncalibrated`,
`comparison.wrong_target_raw_scores_uncalibrated` and
`comparison.positive_minus_wrong_target`. A result of inconclusive or
similar high scores is valid research evidence and must **not** be hidden.
No threshold, provider pass/fail rating, or score-gated XP is created.

Do not rerun the previous successful positive request, first six Groq/Azure
requests, or overwrite `results-01.jsonl` or `azure-only-diagnostic-01.jsonl`.

Review the saved result **without network** at any point:

```bash
python3 v2/benchmarks/azure_native_reference_contrast.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --positive-result PathToPolish-Private-AI/public-polish-live-01/azure-only-diagnostic-01.jsonl \
  --review-result PathToPolish-Private-AI/public-polish-live-01/azure-wrong-reference-01.jsonl
```

Paste the printed **comparison summary only**; do not send keys, private
raw provider JSON, saved voice files or unrelated personal files.

## What comes AFTER (not implemented, not a prerequisite to MVP Speak)

A wrong full phrase tests coarse **content/prompt mismatch**. It cannot
show whether Azure catches an English-speaking adult saying Polish
`s` instead of `ś`, `c` instead of `cz`, or `sz` instead of `ś`.
Those require **real deliberately imperfect adult learner pronunciations**
and independent Polish-native listening labels.

The existing **Speak → Record → Replay → Save 16 kHz WAV** is enough to gather
a small consenting-adult set without a new login form, recorder, data
pipeline, leaderboard requirement, or AI cost per take. Sample two or three
short common target words across these contrasts, with:
- A deliberate correct attempt and deliberately imperfect attempt on the
  **same target**, plus an accidental failure or noisy audio if available;
- A bilingual/Polish-proficient independent listener annotating
  `heard_without_reference`, `target_correct`, `capture_quality`, and
  which sounds (if any) differed, **before** seeing Azure feedback;
- Matched Azure outputs for each take, compared on false-positive acceptance
  of bad pronunciation and false-negative criticism of correct speech.

The existing `v2/benchmarks/pilot_labels.py`,
`v2/benchmarks/model_fit_review.py`, and `learner_three_model_pilot.py`
can support that offline exploratory review. Never synthesize labels or fake
phoneme corrections to give learners an unwarranted grade. The end-user
product should remain listen / record / replay / optional assessment /
retry or next, with no additional work required to obtain basic value.
