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

## Capture ONE real spoken attempt (no inference required)

From the owner's existing Mac repo after merging and syncing:

```bash
git switch main
git pull --ff-only origin main
cd v2/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

In a browser open `http://127.0.0.1:5173`, go to **Library**, search
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
