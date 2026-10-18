# Live public-Polish six-request comparison — ready to execute on owner Mac

**Status:** Code + offline mock tests. **No live Azure/Groq inference run by GitHub CI or ChatGPT**. This environment has neither of the owner's private keys. The owner previously completed the 3-model FLEURS test using Mac Keychain/Groq and Azure Speech F0; those results are immutable and must not be rerun or overwritten.

## Experiment

**SIX requests, no retries:** the pinned Wikimedia public-domain `Dzień dobry` (Julo, about 1.25 s) and `Dobry wieczór` (SirPL0, about 1.579 s) clips, each sent *unchanged* in 16 kHz mono PCM16 form to:

1. Groq `whisper-large-v3`: Polish transcription, reference word-error rate, observed HTTP latency.
2. Groq `whisper-large-v3-turbo`: same evidence. A transcription is NOT a phonetic grade.
3. Azure `pl-PL` scripted PA: native Accuracy/Fluency/Completeness when available, response latency and inconclusive status; not calibrated, no fake phoneme diagnosis.

Groq has a short-request billed-audio minimum; **four transcriptions total at least 40 billable input seconds if billed** despite only ~5.66 seconds total uploaded to Groq across four requests. Azure assesses ~2.829 seconds (two clips). Confirm the live provider account status and free quotas yourself. Script flags assert your manual verification; they **cannot guarantee** the bill is zero. These are exceptionally short phrases; Azure may return NoMatch/inconclusive, which is a valid finding, not zero pronunciation.

## Run from the repository root on your Mac

First sync GitHub, confirm ffmpeg and the private Python SDK environment:

```bash
git switch main && git pull --ff-only origin main
command -v ffmpeg
PathToPolish-Private-AI/.venv-speech-test/bin/python -c 'import azure.cognitiveservices.speech as sdk; print("Speech SDK installed")'
```

Download the two version-locked, public-domain original Oggs and normalize WAV (NEW directory; do not overwrite the previous FLEURS/audio research):

```bash
mkdir -m 700 PathToPolish-Private-AI/public-polish-live-01
python3 v2/benchmarks/public_polish_audio.py \
  --output-dir PathToPolish-Private-AI/public-polish-live-01
```

Run **safe preview**; this validates SHA-256 of original and normalized samples, references, elapsed duration and exact call budget but makes **zero** provider calls:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/public_three_model_pilot.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01
```

The previously saved Groq secret is in macOS Keychain service `PathToPolish-Groq-API-Key`. Load it only into this current Terminal's environment, **never print/paste it into chat**:

```bash
export GROQ_API_KEY="$(security find-generic-password -a "$USER" -s "PathToPolish-Groq-API-Key" -w)"
export AZURE_SPEECH_REGION=germanywestcentral
python3 -c 'import os; print("Groq key present:",bool(os.getenv("GROQ_API_KEY")),"Azure key present:",bool(os.getenv("AZURE_SPEECH_KEY")),"region:",os.getenv("AZURE_SPEECH_REGION"))'
```

If `AZURE_SPEECH_KEY` is missing or invalid in this shell, repair the **existing Azure F0** key environment locally first, without entering keys into chat or GitHub. Don't create a new resource or upgrade plans.

**Only after confirming existing Groq Free and Azure Speech F0 resources, remaining quota, no paid billing or auto-top-up, and permission to send these public-domain clips to both processors**, perform exactly six calls. No hidden retries:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/public_three_model_pilot.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --send --approve-public-audio-upload \
  --confirm-groq-free --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/public-polish-live-01/results-01.jsonl
```

The tool prints a **readable six-row result** with per-engine Polish transcript / WER or raw Azure reported scores, each request duration and an aggregate offline fit report. Full raw provider evidence stays in a new, mode-0600, ignored local JSONL file. No keys are written. If request 3 fails, the completed preceding rows remain; **do not rerun with the same output**. Prefer offline diagnosis.

Re-display existing results with zero inference at any time:

```bash
python3 v2/benchmarks/public_three_model_pilot.py \
  --summarize PathToPolish-Private-AI/public-polish-live-01/results-01.jsonl
```

The printed **summary** can be shared to discuss models (the recordings are public). Do not paste the raw provider JSONL, secrets or any private learner audio. Avoid writing a pronunciation-learning feature until we know how these engines treat short, human-approved audio and later actual imperfect learner speech.

## What the synthetic public test proves (and what it cannot)

The previously merged [PR #44](https://github.com/AndrewDionne/LearnPolish/pull/44) tested the very same genuine audio through desktop/mobile app Speak capture: **PASS**, no provider requests. A new preview gate and unit suite here certify that the exact audio, SHA, references, private output permissions and *six-call budget* are enforced without networking. Only the explicit owner-Mac live command establishes actual Groq and Azure responses. Passing native Polish recognition cannot predict learner mispronunciation grading, and raw PA scores are not ground truth; independent Polish-speaker labels are required before choosing the best production learning model.

Providers: [Groq speech to text](https://console.groq.com/docs/speech-to-text), [Microsoft Azure pronunciation assessment](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-pronunciation-assessment).
