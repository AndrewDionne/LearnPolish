# First actual three-engine Polish speech trial — exploratory

## 2026-10-18 — Local Azure key misconfiguration discovered

Owner ran the post-PR #38 zero-audio regional authentication probe
and received a Python `latin-1` header encoding error on Unicode
character `U+2026` (ellipsis). This failure occurs **on the Mac
before any Azure HTTP authentication**. The Mac environment variable
`AZURE_SPEECH_KEY` was marked AVAILABLE only because it was nonempty,
not because it was valid. Existing Render has a working, separately
configured Azure key; its token probe does NOT validate the Mac's key.
Both Whisper engines worked, Groq Keychain credential is fine.

The probe now rejects non-ASCII values/placeholders before attempting
HTTP and returns `invalid_local_credentials` rather than misleading
`config_missing`. Safe one-line check, NO key printed:

```bash
python3 -c 'import os; k=os.environ.get("AZURE_SPEECH_KEY",""); print("Present:",bool(k),"ASCII:",k.isascii(),"Contains ellipsis:",chr(0x2026) in k)'
```

If non-ASCII/placeholder, recheck the **EXISTING** Azure Speech F0
resource under Azure Portal > Keys and Endpoint; do not create a new
resource or paid tier. The local `~/.zshrc` previously contained two
assignments to `AZURE_SPEECH_KEY`, so ensure no later placeholder
overrides the correct key. **Never post/commit/print secrets**.
After repairing and exporting the existing credential, rerun
`python3 v2/benchmarks/azure_auth_probe.py` (zero audio).
Only `token_issuer_authorized` justifies the next single Azure-only
5.64-second diagnostic `azure-sdk-diagnostic-02.jsonl` under user
F0/free quota, permission and no-paid gating. The old `-01` and
initial six model result files remain immutable.


## 2026-10-18 — Azure Canceled/Error/Unknown: verified SDK property fix

**Physical result:** One Azure-only SDK call on public FLEURS 00003 (5.64 seconds)
returned Canceled/Error/Unknown, no scores. Zero Groq. The result is
preserved at PathToPolish-Private-AI/azure-sdk-diagnostic-01.jsonl.
**Do not rerun/overwrite it.**

**Actual code defect:** Python SDK CancellationDetails uses the field
`code`, NOT the `error_code` attribute mistakenly read in our
diagnostic. The old report could not disclose the actual Azure category;
do not infer authentication failure or bad microphones. New code reads
`code` with a legacy fallback; only allowlisted enum labels are ever
printed, never free-text SDK error details or keys.

**Before any additional voice inference**, sync latest merged main and run
this zero-audio regional token authorization check:

```bash
git switch main
git pull --ff-only origin main
python3 v2/benchmarks/azure_auth_probe.py
```

This performs just one regional STS issueToken POST via the existing
AZURE_SPEECH_KEY and AZURE_SPEECH_REGION shell variables. It never
reads or prints the returned bearer token; does not make speech
inference requests. `token_issuer_authorized` only proves that the
regional token issuer accepts the key, not that Speech SDK works.
If `token_issuer_rejected` or `connection_failed`, **STOP**,
report the status and do not repeat any speech inference.

After `token_issuer_authorized` and confirming existing Azure Speech
F0 resource, remaining free quota, zero paid billing and public dataset
audio processing rights, run exactly one new Azure-only request using
the PRIVATE already-installed SDK. This uses a NEW filename; never
overwrites diagnostic 01 or the first three-model results.

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_retest.py \
  --manifest PathToPolish-Private-AI/sentences-source.json \
  --sample-id fleurs-pl-val-00003 \
  --max-requests 1 --max-audio-seconds 10 \
  --send --approve-public-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/azure-sdk-diagnostic-02.jsonl
```

Report sanitized `sdk_error_code` (or successful Azure score), then
STOP before further sends. No Groq requests. No files moved. This
diagnoses the SDK error; it does not promise resolution or that any
particular paid usage is impossible.


## 2026-10-18: Azure-only diagnostic after first real three-model run

The owner actually ran all six calls: Groq Whisper V3 and Turbo returned
Polish transcripts, but **Azure returned inconclusive on both** 00003
and 00009. Offline inspection of first result JSONL found
`Azure did not recognize complete speech` and no Azure raw JSON for
either. Earlier code collapsed SDK `NoMatch` and `Canceled` into
one generic reason; no definite Azure root cause is yet known.

NEW `azure_retest.py`: exactly **one Azure-only request** on the
existing original unmodified FLEURS clip `fleurs-pl-val-00003` (5.64s).
No new Groq calls, no audio downloads, source edits or old result
overwrites. Prints allowlisted SDK result reason, no-match/cancellation
reasons and error codes (never free-text SDK error_details or secrets).
The old strict production Azure benchmark native-human gate remains
intact; this is an exploratory public-audio integration diagnostic.

Mac commands, from repo root, using existing Azure SDK virtual environment:

```bash
git switch main
git pull --ff-only origin main
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_retest.py \
  --manifest PathToPolish-Private-AI/sentences-source.json \
  --sample-id fleurs-pl-val-00003
```

The above is **offline preview only**. After checking existing Azure
resource F0, remaining free quota, zero paid billing and public
FLEURS rights for third-party processing, run **one** diagnostic request:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_retest.py \
  --manifest PathToPolish-Private-AI/sentences-source.json \
  --sample-id fleurs-pl-val-00003 \
  --max-requests 1 --max-audio-seconds 10 \
  --send --approve-public-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/azure-sdk-diagnostic-01.jsonl
```

Only Azure environment key and `AZURE_SPEECH_REGION=germanywestcentral`
needed; Groq Keychain key is not used. The result is saved as a new
Git-ignored 0600 private JSONL with original SHA; output is sanitized
to standard SDK codes. **Stop after one call and report the exact
`sdk_result_reason`, `sdk_no_match_reason`,
`sdk_cancellation_reason`, `sdk_error_code`** (or success).
Potential authentication, connection or silence categories are only
hypotheses until this result. If the old and new SDK both return no
scores, do not repeat without analyzing the new category.


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
