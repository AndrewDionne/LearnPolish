# First actual three-engine Polish speech trial — exploratory

OWNER DIRECTION (2026-10-17): Run a preliminary comparison now, before spending more time chasing a perfect native corpus.

## Precisely what it tests

Two untouched, 5–15-second, publicly licensed FLEURS Polish `pl_pl`
validation WAVs from the **already downloaded** source folder. By
default the two best basic acoustic-level candidates are selected
automatically; loudness/clip heuristics cannot prove clear microphones,
authentic native accents, complete text or ideal pronunciation.
Use `--sample-id fleurs-pl-val-XXXXX fleurs-pl-val-YYYYY`
to override the automatic choice with specific best-sounding files.

On the SAME original WAVs, model by model:
- Groq Whisper `whisper-large-v3` — transcript + WER against FLEURS reference.
- Groq Whisper `whisper-large-v3-turbo` — transcript + WER against the same reference.
- Azure Speech `pl-PL` scripted pronunciation assessment — reported accuracy,
  fluency/completeness, available word/phoneme scores and raw provider JSON.

**IMPORTANT:** Whisper WER is only ASR recognition, NOT a pronunciation
grade. Azure scores are from **uncertified native dataset speech**, are
not human-calibrated, and may reflect bad microphone/audio. This tests
that three providers can run and surfaces comparable **different kinds
of evidence**; it cannot prove model superiority.

## Mac one-run instructions

From repo root, sync and install local Azure Python SDK if not installed:

```bash
git switch main
git pull --ff-only origin main
python3 -m pip install azure-cognitiveservices-speech
```

**Preview** first. Offline: does NOT contact Groq/Azure and does not
write files:

```bash
python3 v2/benchmarks/three_model_pilot.py \
  --manifest PathToPolish-Private-AI/sentences-source.json
```

The output gives exact selected WAV IDs, hashes, acoustic hints, 6
planned requests (4 Groq, 2 Azure), up to 60 Groq billed
audio seconds and up to 30 Azure audio seconds. You may set
`--sample-id` to your two preferred clear-sounding filenames from the
original playlist if auto-selection seems poor.

**Credentials remain PRIVATE on your Mac.** The existing Azure Speech
F0 resource lives in region `germanywestcentral`; Render passed STS
token diagnostic but cannot yield its private key through our connector.
Use Azure Portal -> existing Speech F0 resource -> Keys and Endpoint;
use Groq Console for your existing Free Plan key.

Only if the env variables are not already set in your shell, enter
them via masked keyboard prompts (don't print, commit or paste keys):

```bash
read -rs 'GROQ_API_KEY?Groq API key (hidden): '; echo
export GROQ_API_KEY
read -rs 'AZURE_SPEECH_KEY?Azure Speech F0 key (hidden): '; echo
export AZURE_SPEECH_KEY
export AZURE_SPEECH_REGION=germanywestcentral
```

Before real calls, verify actual Azure Speech resource still F0,
remaining free quota, Groq Free Plan, that neither has activated
paid/auto-top-up, and public FLEURS dataset third-party processing use
and attribution. **These are account checks**, not automatically
guaranteed by flags.

**RUN** the single preliminary comparison (up to six provider requests,
once only, no retries):

```bash
python3 v2/benchmarks/three_model_pilot.py \
  --manifest PathToPolish-Private-AI/sentences-source.json \
  --max-requests 6 --max-groq-billed-seconds 60 \
  --max-azure-audio-seconds 30 \
  --send --approve-public-audio-upload \
  --confirm-groq-free --confirm-azure-f0 \
  --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/preliminary-three-model-01.jsonl
```

It prints transcript WER and Azure reported metrics for all completed
samples. The ORIGINAL WAV files and source manifest do not change.
The file `preliminary-three-model-01.jsonl` is new, 0600 and
Git-ignored, storing raw Azure result and Groq transcripts. If any
request fails, the program stops and keeps previous successes; do not
rerun blindly or overwrite the file. To inspect partial results offline:

```bash
python3 v2/benchmarks/three_model_pilot.py \
  --summarize PathToPolish-Private-AI/preliminary-three-model-01.jsonl
```

The supported `pl-PL` speech locale and F0 status were checked
independently for the existing resource. Public reference:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment .
The source audio is public `google/fleurs`, published as CC BY 4.0,
but this is not a claim that a fluent reviewer certified these two
specific clips as the "correct" way to pronounce Polish. Do not use the
results as production grading thresholds.

No Azure/Groq model call is done by this GitHub patch or CI. The test
runs only from the owner's Mac, where the existing public dataset WAVs
and provider credentials reside.
