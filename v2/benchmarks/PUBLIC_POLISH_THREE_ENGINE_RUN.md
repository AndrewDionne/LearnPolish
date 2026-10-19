# Live public-Polish six-request comparison — ready to execute on owner Mac

## Azure real short-phrase assessment SUCCESS — owner Mac, 2026-10-19

**Actual provider call (not mock / not CI):** Following local key repair and regional STS authorization HTTP 200, the owner ran **exactly ONE Azure-only inference** through `v2/benchmarks/public_three_model_pilot.py --azure-only --sample-id greeting-day --send` on the *same pinned public* `Dzień dobry` source (WAV 1.250 seconds; from original `greeting-day` fixture). Result: `status=AZURE_ONLY_COMPLETED`, `network_calls_performed=1`, `groq_calls=0`, `azure_status=ok`, `azure_diagnostic=null` (no cancellation), **Azure's raw uncalibrated AccuracyScore=100.0, FluencyScore=100.0, CompletenessScore=100.0**; private report saved at `PathToPolish-Private-AI/public-polish-live-01/azure-only-diagnostic-01.jsonl`. The previous six-call result file `results-01.jsonl` remains untouched, as do the earlier public/learner WAVs, FLEURS results and credentials. This proves real SDK scripted Polish pronunciation scoring CAN succeed on a short (1.25-second) Polish phrase with correct local Azure key and Speech region. The earlier cancellations predate key correction; they are consistent with auth trouble but the omitted historic SDK error enums prevent a definitive retroactive root-cause attribution.

**Practical recommendation:** No additional infrastructure or admin work. Provisional components: Azure as reference-aware pronunciation-feedback *candidate*, Whisper Turbo as fast transcription/word-check *candidate* (both Whisper models recognized two native phrases perfectly; only two samples, latency varied). **Do not treat Azure 100/100/100 as externally validated correctness, give child XP/grades, or declare phoneme-level Polish feedback proven.** Next high-value E2E test is a small independently judged *adult* set of correct and deliberately imperfect Polish words/phrases, with actual same-audio learner mistakes, checking Azure false-positive/false-negative rates, miscue handling, concise actionable feedback, provider latency and retry/next UI. Preserve voice privacy and confirm resource quotas/consent before any further calls. No need to rerun the finished native-control requests.


## Actual first live results — owner Mac, 2026-10-19 (COMPLETE)

The first exact six-request comparison was **actually run** against the two pinned
public-domain native Polish original recordings using the owner's existing
Groq Free/Azure F0 credential setup. It returned
`PUBLIC_NATIVE_SIX_CALLS_COMPLETED` and `network_calls_performed=6`.
This output was pasted by the owner; do not repeat Whisper or overwrite
`PathToPolish-Private-AI/public-polish-live-01/results-01.jsonl`.

| Original native phrase | Whisper large-v3 | Whisper large-v3 Turbo | Azure Speech pl-PL scripted |
| --- | --- | --- | --- |
| Dzień dobry, 1.250s | `Dzień dobry.`, WER 0, **5750.7ms** | `Dzień dobry.`, WER 0, **1508.6ms** | **Canceled**, no grade, **1328.3ms** |
| Dobry wieczór, 1.579s | `Dobry wieczór.`, WER 0, **1804.3ms** | `Dobry wieczór.`, WER 0, **4470.8ms** | **Canceled**, no grade, **1966.3ms** |

Observed mean latency: v3 **3777.5 ms**, Turbo **2989.7 ms**,
Azure **1647.3 ms to cancellation** (NOT completed assessment). Both Whisper
variants 2/2 successful exact word transcriptions; both Azure results
`inconclusive`. Native references only, not a nonnative pronunciation study.
Turbo faster on average of TWO but was **slower on the second phrase**, so don't
declare a latency winner. Original Ogg hashes remained pinned; Mac normalized
WAV SHA values were
`563a1594105bb13a973ea855fcd869832acda44cde04dc64139e8f4cdfbaf29a`
and `2e2b463760b6b99919de31c8e9c4a528a01832e742495166c094fef51409c876`
respectively. Normalized hashes can vary across FFmpeg platforms; within
each Mac sample all three engines received the SAME WAV bytes. The earlier
5.64-second public FLEURS clip DID return Azure scores 93/93/92. This suggests
a short-utterance problem is worth investigating, but **does NOT prove**
duration caused the cancellations.

**Important defect identified and fixed in the runner:** the underlying
`azure_scripted_assess` already sanitized and returned
`azure_result_reason`, `azure_cancellation_reason`,
`azure_no_match_reason`, and `azure_error_code` when applicable. The original
six-call runner discarded those enum fields, collapsing both cancellations
into the unhelpful generic text `Azure canceled speech recognition`.
We cannot infer or recover the discarded codes from the original printed
report or existing JSONL. No credentials, audio, raw JSON or human data
were exposed. The updated code now saves only ALLOWLISTED diagnostic enum
names and displays them in `--summarize`; never the SDK's free-text
`error_details`.

### What to do before another single Azure request (zero inference first)

There is **no reason to rerun Whisper**; both outputs remain valid.
First, refresh latest main. Without consuming an Azure recognition request,
check whether the SAME current Azure key/region passes token authorization:

```bash
git switch main && git pull --ff-only origin main
python3 v2/benchmarks/azure_auth_probe.py
```

This uses a regional authentication request, **no uploaded audio or Speech SDK
recognition**, and the existing environment key, which is never printed.
If the token issuer rejects or the network fails, STOP: investigate that
before any audio inference. Success does NOT guarantee WebSocket SDK
recognition; it only narrows the diagnosis.

After successful auth and checking the existing Azure F0, remaining free
quota/no paid billing again, this **preview-only** command validates the
exact same already-downloaded WAV, without Whisper/Groq or Azure inference:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/public_three_model_pilot.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --azure-only --sample-id greeting-day
```

If one further Speech inference is warranted and approved, use a NEW filename
(no overwrite of prior six results), **ONE Azure call only, ZERO Groq**:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/public_three_model_pilot.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --azure-only --sample-id greeting-day \
  --send --approve-public-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/public-polish-live-01/azure-only-diagnostic-01.jsonl
```

This reuses the **same** original for diagnosis, not to obtain a better
score. It reports the Azure SDK cancellation reason and allowlisted error
code if available. If `azure_error_code=AuthenticationFailure/Forbidden`,
investigate resource/key or policy; if `ConnectionFailure/ServiceTimeout`,
investigate SDK network/transport; if `ServiceError/BadRequest`, investigate
service request/short-audio format; `NoMatch` is recognizer uncertainty.
These are **diagnostic suggestions**, not definitive root-cause statements.
Stop after one attempt and inspect the code; do not buy additional services,
create an Azure resource, pad/speed-alter audio, or rerun all six requests.
We must still test *actual nonnative adult* pronunciations before grading.


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
