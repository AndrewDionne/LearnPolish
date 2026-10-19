# Świętokrzyska — pronunciation and latency test

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
