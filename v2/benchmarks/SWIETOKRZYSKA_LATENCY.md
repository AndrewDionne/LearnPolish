# Świętokrzyska — pronunciation and latency test

## PHYSICAL RESULT — Whisper v3/Turbo comparison COMPLETED (2026-10-19)

**Actual owner Mac result; no synthetic/provider-mocked numbers:** the
owner successfully installed `PathToPolish-Private-AI/.env.groq`,
verified the model-list endpoint (Groq auth accepted, both models listed,
zero uploaded audio), and then expressly authorized exactly TWO Groq
Whisper transcriptions on the previously tested adult original 3.12s
`Świętokrzyska` WAV. Report `WHISPER_PAIRED_RESULT`, same audio
SHA `0f4ff4b3d01165dc5e27fd9c10336f19aedf4aefdca430798c2b1777e5df1626`,
**2 Groq attempts saved, 0 new Azure requests**. Original private
result `PathToPolish-Private-AI/swietokrzyska-01/whisper-01.jsonl`
MUST NOT be overwritten or submitted again.

| Provider/mode | Total elapsed measured | Raw output on original WAV |
| --- | ---: | --- |
| Azure SDK ordinary | 2459.7 ms | Pronunciation raw 84 / 100 / 100 |
| Azure SDK explicitly preconnected | 1923.3 ms | Pronunciation raw 84 / 100 / 100 |
| Groq Whisper large-v3 (curl HTTP) | **1034.9 ms** | `Sweczo Seska` — NOT the target |
| Groq Whisper large-v3-turbo (curl HTTP) | **470.8 ms** | `Sveczo Seska` — NOT the target |

**Both Whisper engines returned an incorrect two-token transcription**
instead of `Świętokrzyska`. Exact target word match FALSE for both.
One-word-reference WER **2.0** for both, which is **200% transcription
word error**, valid because 1 substitution + 1 insertion divided by
1 reference word = 2.0. Contrary to the original note, single-word WER
is **not restricted to 0 or 1**: extra hypothesized words can produce
WER greater than 1.0. This is NOT pronunciation accuracy, confidence
or a phoneme metric. The transcription difference is not proof that
the adult learner pronounced the target incorrectly, nor evidence
that Azure's 84/100/100 was correct: there is no independently labeled
Polish human assessment or native reference comparator for THIS word.

**Latency observation:** Turbo's 470.8ms was ~4.1x shorter than
preconnected Azure's 1923.3ms and ~5.2x shorter than Azure ordinary's
2459.7ms. This is on single isolated requests with different
instrumentation (Groq HTTP vs Azure Python SDK) and order/warming
confounders; NO production p95 or causal ranking. Both engines were
within the desired <5s bound on this instance; the older 20s Azure
outlier still matters. Do not replace Azure pronunciation assessment
with Whisper exact-text recognition in the live family learning app
based on these results. Neither Groq call provided usable
`Świętokrzyska` recognition for this recording.

**Decision:** Preserve the existing private WAV, Azure JSONL and Groq
JSONL. No more repeat calls on the same WAV just to check credentials,
and NO new scores/XP gates. Next research must distinguish speech
content/learner articulation from ASR language-model familiarity using
an independently verified native Polish `Świętokrzyska` reference and
separately a few consented adult takes, with human-reviewed pronunciation
quality, before investing in blended model UX. Any expanded study must
be explicitly added to the development plan rather than treated as
an automatic next test.


## SAVE GROQ KEY ONCE — permanent owner-private setup

Groq and Azure use different API keys. Both have now been installed by the owner;
these instructions are retained for future key rotations. Azure was already saved as
`PathToPolish-Private-AI/.env.azure-speech`; **do not replace that file**.
The matching permanent Groq asset is now:

`PathToPolish-Private-AI/.env.groq`

This directory is excluded from Git, is required to be owner-only
(mode 0700), and the Groq config file must be owner-only (mode 0600).
The new standard-library `v2/benchmarks/groq_env.py` never executes
configuration text, never writes a key to source control or browser
JavaScript, and never sends requests to Groq during key setup.

**If GROQ_API_KEY is already exported in this Terminal:** from the repo
root (once this PR is merged), install it **just once**:

```bash
git pull --ff-only origin main
python3 v2/benchmarks/groq_env.py --save-current
python3 v2/benchmarks/groq_env.py --status
```

**If the key is not in this Terminal**, use a private hidden input
instead:

```bash
python3 v2/benchmarks/groq_env.py --setup
```

After installation, future Terminal sessions and the Groq-only
`swietokrzyska_whisper.py` runner load the private file
automatically; no environment variable export or repeated key entry.
The installed file overrides any stale `GROQ_API_KEY` in your shell;
the environment variable remains a fallback ONLY when there is no
installed file. Invalid or insecure installed files fail closed.
`--setup --replace` intentionally rotates an existing key; no normal
setup can overwrite it. Do not paste the key into chat or expose it
through `cat`, `echo` or screen recordings. Gitignore is not encryption;
keep the owner-private directory out of shared/cloud folders.

Optional Groq credential-only authorization check (**GET model list**,
zero audio uploaded, no Whisper inference) after installing:

```bash
python3 v2/benchmarks/groq_pilot.py --check-access --transport curl
```

The same private Groq loader is used by the general `groq_pilot.py`,
public test harness, and adult learner three-engine harness. Groq
provider requests still require distinct `--send`, adult consent,
Free-plan and no-paid-billing approval. This is a research credential
asset only; it does not configure a browser key or production Render
secrets.


## Whisper v3 vs Whisper Turbo — same adult word, **no repeat Azure**

**Historical setup note:** The owner has now completed both the Azure and
Whisper tests on this exact `Świętokrzyska` WAV; see the physical result above. Earlier
Groq Whisper native-audio successes were for `Dzień dobry` and
`Dobry wieczór`, NOT this longer word. Treat results separately.

The Groq-only `v2/benchmarks/swietokrzyska_whisper.py` harness reuses the
same original private WAV and **reads the existing** `azure-compare-01.jsonl`
to verify the SHA-256 and reference `Świętokrzyska`. It requires both
Azure assessments to have actually succeeded. It never calls Azure,
regardless of `--send`, and makes **zero inference** by default.

From the repository root after pulling merged main, check local WAV:

```bash
WAV='PathToPolish-Private-AI/swietokrzyska-01/ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav'

PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_whisper.py \
  --wav "$WAV" \
  --azure-result PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl
```

This is a **PREVIEW** (zero network) and reports the previous Azure raw
scores, old timings, target SHA, and planned TWO Groq Whisper requests.
Do not touch or overwrite the original adult WAV or completed Azure
result file.

To perform the new comparison ONCE, the owner must separately review
and approve processing this consenting **adult's audio** by **Groq**,
verify their Groq account is still on the **Free plan** without paid
billing or auto-top-up, and privately have a valid `GROQ_API_KEY` in
the same Mac Terminal (no key in chat/screenshots). Check its presence
without printing its value:

```bash
echo "Groq key available: $([[ -n "$GROQ_API_KEY" ]] && echo yes || echo no)"
```

The available `v2/benchmarks/groq_pilot.py` can do a **zero-audio**
list-models access check if needed; do not confuse that with confirmed
model inference or billing status. If the key is absent, restore your
Groq key privately using hidden `read -rs`; never store it in tracked
frontend code.

With explicit informed Groq consent / confirmed free billing, execute
TWO requests (Groq large-v3 and Groq large-v3-turbo, sequential; **ZERO
Azure**) using a **NEW** private output filename:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_whisper.py \
  --wav "$WAV" \
  --azure-result PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl \
  --send --approve-adult-audio-upload \
  --confirm-groq-free --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/swietokrzyska-01/whisper-01.jsonl
```

Estimate about **20 seconds of Groq billable audio** in total due to
their minimum 10 seconds per 3.12-second recording, even though the
models process only the unchanged 3.12 seconds each. No implicit
retry; on provider failure save one sanitized error row and stop.

The script prints an offline-verified paired comparison with recognized
literal Polish text (diacritics preserved), **single-word WER** and
duration for each model, alongside already saved Azure scores/SDK
timings. Provider raw response, credentials and WAV are never copied
into the result file; private JSONL still contains **your recognized
transcript** and must remain private and chmod-600.

Review later WITHOUT any model calls:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_whisper.py \
  --wav "$WAV" \
  --azure-result PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl \
  --summarize PathToPolish-Private-AI/swietokrzyska-01/whisper-01.jsonl
```

**Decision boundaries:** Whisper large-v3 and Turbo give
transcriptions, not the Azure pronunciation metric. Even on a ONE-word
reference, WER may be **greater than 1.0** when the hypothesis has extra
words (as observed here, WER=2.0). A correct `Świętokrzyska`
transcription would not prove correct `ś`, `ę`, `rz`, etc. or
phoneme-grading quality. Azure's 84/100/100 is raw, uncalibrated. Two request times
cannot establish p95, and Groq curl HTTP turnaround and Azure SDK
recognize_once time are not identical instrumentation. This is
exploratory model-fit evidence, not a leader-board scoring policy.

## PHYSICAL RESULT COMPLETE — 2026-10-19 (do not repeat)

Owner successfully submitted the **same original 3.120-second** adult
`Świętokrzyska` Speak WAV for exactly **two Azure Speech F0** requests.
Private evidence at `PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl`
MUST NOT be overwritten or used as a fresh output. Zero Groq calls.

| Phase | Ordinary | Preconnected |
| --- | ---: | ---: |
| Total measured SDK time | **2459.7 ms** | **1923.3 ms** |
| Preconnection wait | 0 ms | **423.9 ms** |
| Recognition call | 2457.4 ms | **1499.1 ms** |
| Connected event confirmed before recognition | No | **Yes** |
| Status | ok | ok |
| Accuracy / Fluency / Completeness (Azure raw, not calibrated) | **84 / 100 / 100** | **84 / 100 / 100** |

Observed total advantage = **536.4 milliseconds** (about **21.8%**)
for preconnected second call, **including the time spent connecting**.
Recognize-only phase decreased by 958.3ms but excludes 423.9ms of
preconnection wait; don't report that as full user-perceived savings.
Same audio SHA-256 confirmed by owner-run benchmark; no transcript,
credential, or recording committed to GitHub.

**Interpretation:** Both attempts scored identically; connection
readiness was actually confirmed. This is encouraging but NOT proof of
causal acceleration or true latency percentiles: the preconnected
attempt ran SECOND and could benefit from network/service warming. No
app-wide connection optimization is deployed by this experiment; it
remains an engineering candidate. The previous 20.4113-second historical
outlier is NOT invalidated by this two-call test.

## STABLE Azure key asset — setup ONCE, no more repeated shell exports

Owner request: credentials must persist across new Terminal sessions
without manually re-pasting or setting a region every time.

The single **permanent local** key file is:

`PathToPolish-Private-AI/.env.azure-speech`

The folder is already ignored from Git by `/PathToPolish-Private-AI/`.
The new standard-library-only helper `v2/benchmarks/speech_env.py`
never touches network, never sources `.env` as executable shell code,
and requires owner-only file **0600** and folder **0700**. Supported
fields are exactly `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`.
A valid installed file **takes precedence over stale `~/.zshrc`
environment exports**. If no file is installed, existing shell
variables still work. Bad/insecure installed files fail closed.

**From the repo root in a Terminal where the real Azure key and
`germanywestcentral` region just succeeded**, install once:

```bash
git pull --ff-only origin main
python3 v2/benchmarks/speech_env.py --save-current
python3 v2/benchmarks/speech_env.py --status
python3 v2/benchmarks/azure_auth_probe.py
```

The save operation uses the ALREADY configured key/region, prints
only success status, and performs **zero** Azure calls. The auth probe
sends a separate **zero-audio** Microsoft STS token-request, not speech
inference, to confirm credentials. No need to rerun the already
completed two-call audio comparison.

**If this Terminal does not have the valid key exported**, instead:

```bash
python3 v2/benchmarks/speech_env.py --setup
```

The Python helper prompts for the real Speech key with hidden input,
installs it under the correct resource region, and does not print it.
No key arguments, source code edits, output screenshots or chat sharing.

**When intentionally rotating the key**, use
`python3 v2/benchmarks/speech_env.py --setup --replace` and enter the
new real key through hidden input. An existing credential file is
NEVER overwritten by a normal setup. Do not store keys in tracked
`v2/frontend/.env`, browser JavaScript, a committed file, or macOS
shell startup files. Gitignore is protection against accidental
commit only, **not encryption**: avoid uploading the private folder
to cloud sync or sharing Mac accounts.

All owner-local Azure Speech CLI tools (STS auth probe, normal Azure
pilot, Świętokrzyska timing, historical short-latency and contrast
experiments, public and adult comparison runners) now load this
same file, but only for an explicitly selected live `--send`.
Offline previews/summaries never need the secret. This configuration
DOES NOT grant upload consent or turn on provider calls automatically.

**Next owner verification:** after saving, open a NEW Terminal,
run the zero-inference `python3 v2/benchmarks/speech_env.py --status`
and `python3 v2/benchmarks/azure_auth_probe.py` from the repository
root. Both should work without manually exporting the key or region.


## Why this word

The owner chose **Świętokrzyska** to replace the two short greetings as
the next test target. It contains Polish diacritics and consonant groups
that make it a more demanding real-world pronunciation test. It is a
Warsaw street / metro-station name, used here as ONE exact Polish word.
Do not silently substitute the similarly spelled adjective
`świętokrzyski`, split it into several words, or strip Polish marks.

**Reference:** `Świętokrzyska`.
**Built-in V2 Speak ID:** `speak_swietokrzyska:0`.

This feature includes NO invented "native" recording and NO fabricated
Azure score. The word is now a searchable V2 Library lesson that supports
the existing microphone, replay, private WAV export, and (when the
private adult family API is configured) optional Azure assessment.
Without a verified native clip the Play Example button is absent.
Basic recording, replay and progression do not require Azure.

## Mac browser microphone troubleshooting

If the Speak card shows a microphone-access error **even after choosing
Allow**, two independent controls may be involved:

1. In **Chrome**, open the exact local app address
   `http://127.0.0.1:5194`; select the address-bar site information
   → Site settings → Microphone → Allow. A permission given to
   `localhost:5173` or another origin is not permission for
   `127.0.0.1:5194`.
2. macOS **System Settings → Privacy & Security → Microphone**:
   confirm Chrome (or the actual browser in use) is enabled.
3. macOS **System Settings → Sound → Input**: choose a functioning
   microphone. Try a macOS local audio-recording app if you need to
   distinguish OS input failure from the browser.
4. Quit Chrome entirely with **⌘Q**, reopen the exact app URL, and
   press **Start recording** again.

A `NotAllowedError` does not by itself identify which layer rejected
the request. The Speak recorder now **silently queries browser site
permission after an actual capture failure**: if it is `granted`,
the error advises checking macOS Privacy & Security and sound input;
if `denied`, it advises site permissions; if unknown, it mentions both.
The probe does not open a microphone, request fresh permission or
upload audio. `NotReadableError` and `NotFoundError` are distinguished
from permission denials. Basic lessons, XP and the next button work even
if no microphone is available. Azure is never called by a failed
recording or this diagnostic.

## Capture ONE real spoken attempt (no inference required)

From the owner's existing Mac repo root, after merging and syncing,
install the **frontend dependencies** if not yet present. This repository
currently has `package.json` but **no tracked package-lock.json**, so
use `npm install`, not `npm ci` (which requires a lockfile):

```bash
git switch main
git pull --ff-only origin main
cd v2/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5194
```

If Terminal already shows `frontend %`, you are **already** in
`v2/frontend`: omit `cd v2/frontend`, then run `npm install`
and `npm run dev -- --host 127.0.0.1 --port 5194` directly.
A successful `npm run content` does not mean Vite has been installed;
`vite: command not found` usually indicates missing local `node_modules`.
Node and npm should already be installed if the content generator ran.
To return to the repository root later, use `cd ../..`.

In a browser open `http://127.0.0.1:5194`, go to **Library**, search
`Świętokrzyska`, open the **Speak test** lesson and select **Speak**.
Record an **adult volunteer** saying the actual word, replay it, and
choose **Save 16 kHz WAV for private AI test**. The ordinary browser
microphone take and WAV export are local; no Azure call occurs unless
the separate explicit "Check my pronunciation" action is enabled and
selected. Neither the audio bytes nor an assumed pronunciation grade
are placed in source code or GitHub.

Use Finder to move ONE exported
`ptp-speech-v1--speak_swietokrzyska%3A0--<UTC timestamp>.wav` from
Downloads into an existing or new private directory, for example:

```bash
# Run once from repository root, in another Terminal:
mkdir -p PathToPolish-Private-AI/swietokrzyska-01
chmod 700 PathToPolish-Private-AI/swietokrzyska-01
```

Do not use a child recording for this experimental external provider
comparison; avoid audio from anyone who has not consented. Do not
rename the WAV filename: its encoded ID lets the offline runner fail
closed if the audio was captured for another Polish phrase.

## Offline preview, no speech uploaded

In zsh from the **repository root**, with exactly one exported WAV in
the study folder:

```bash
WAV=(PathToPolish-Private-AI/swietokrzyska-01/ptp-speech-v1--speak_swietokrzyska%3A0--*.wav)
echo "Matching recordings: ${#WAV[@]}"
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_latency.py \
  --wav "${WAV[1]}"
```

The preview checks the original **16 kHz mono PCM16 WAV**, 0.6–10 second
duration, exact test item ID and SHA-256 and displays the planned
**two** Azure requests. It makes zero provider connections/calls.

## Live runner preflight — keys and existing results (owner issue, 2026-10-19)

The owner's first REAL `--send` attempt did **not** print
`Azure 1/2:` and ended with the older generic
`Validation/provider failure. Check local private files, speech key, F0
and command flags.` The previous **no-network WAV preview PASSED**,
confirming the original V2 file is valid (3.12 seconds, correct
`Świętokrzyska` target). The failure therefore occurred after the
preview boundary; it is NOT proof that Azure processed any request.
Likely preflight causes include an unexported `AZURE_SPEECH_KEY` in a
new Terminal or a previously created output file. **Do not infer an
exact cause until the user checks; preserve the original evidence.**

Safe local diagnostics (from repo root), no audio upload or secret echo:

```bash
echo "Azure key configured: $([[ -n "$AZURE_SPEECH_KEY" ]] && echo yes || echo no)"
echo "Azure region: ${AZURE_SPEECH_REGION:-not-set}"

if [[ -e PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl ]]; then
  echo "Result file exists — preserve it; DO NOT repeat --send"
else
  echo "No result file created"
fi
```

If the key is not exported, restore it privately from the owner's
existing Azure Speech **F0** resource in the *same* Mac shell, without
printing or sharing it; set
`export AZURE_SPEECH_REGION=germanywestcentral`. The earlier Azure
token-issuer preflight can confirm STS access **without audio calls**:

```bash
python3 v2/benchmarks/azure_auth_probe.py
```

If an output file already exists, do not overwrite it. Run
`--summarize <existing private JSONL>` first to see how many requests
(if any) completed; if no rows, preserve for diagnosis and choose a new
filename only after checking the cause. The updated CLI reports
**safe allowlisted cause categories** (key missing/invalid shape,
region mismatch, output exists, and private folder problems).
It never prints raw Azure SDK errors, private file paths, keys, audio
bytes or transcripts. Repeating a failed command is NOT automatic.

## Optional one-shot Azure SDK connection comparison

First confirm the existing Speech **F0** resource still has free quota,
no paid billing/auto-top-up and the current Mac shell key passes the
zero-audio `python3 v2/benchmarks/azure_auth_probe.py` probe with
`token_issuer_authorized`. These account facts are NOT verified by
command flags.

If explicitly approved for TWO real external processing requests on
this consenting adult's SAME audio, run once:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_latency.py \
  --wav "${WAV[1]}" \
  --send --approve-adult-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl
```

**Exactly TWO requests maximum, sequentially, ZERO Groq:**

1. `ordinary`: match current Azure configuration, fresh recognizer,
   no explicit connection setup. Total SDK and recognition phases timed.
2. `preconnect`: fresh and isolated recognizer with the same exact
   WAV/reference. Call `Connection.from_recognizer`, subscribe to
   `connected`, `open(False)`, wait up to **3 seconds** for the
   actual connected event, then call `recognize_once()`. Report whether
   connection readiness was **confirmed before recognition**. The
   connection open is an extra network action (without separate speech
   inference); it moves some wait earlier but is not free of time/energy.

All recognized scores are raw Azure, uncalibrated and not teaching
grades. Failure on attempt 1 stops before attempt 2, preserving safe
partial output in a NEW chmod-600 private JSONL. Previous native public
audio/results are NOT changed and the experiment does not mutate app
recordings. Do not repeat requests casually or overwrite this output.

To re-review the existing result with **zero** network:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/swietokrzyska_latency.py \
  --wav "${WAV[1]}" \
  --summarize PathToPolish-Private-AI/swietokrzyska-01/azure-compare-01.jsonl
```

## What can actually be concluded?

The two calls are A/B **engineering diagnostics**, not a statistically
valid model comparison. Since preconnect runs SECOND, cloud warming,
network changes and time variation can account for apparent speed
improvement. The preconnect experiment is useful only when
`connected_before_recognition=true` and the full phases are observed;
even then, it does not demonstrate that preconnecting in production
improves HTTP round trips. If preconnect is slower, report that too.
No automatic retries or increased Azure F0 consumption in the app.

The real Speak API now exposes only `Server-Timing: speech-sdk;dur=N`
for the one authorized request. Its frontend displays browser-measured
response turnaround and SDK time (when readable via CORS). Timings
remain in memory for the displayed take; no voice, text, score,
identity or latency history is persisted. UI still allows immediate
next/record/replay, with no forced pronunciation gate.

If 20-second responses recur, investigate the transport before claiming
the issue fixed. Target an ordinary spoken-word feedback experience
under 5 seconds. Four earlier short-native matched tests were 4.05,
6.67, 4.02 and 1.47 seconds (median 4.04 seconds). The 20.41-second
wrong-reference observation remains evidence of tail risk.

Microsoft SDK documentation:
- https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.connection
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment
