# Azure short Polish phrase — bounded real latency sample

## Why we are testing

The owner's last **real** Azure Speech SDK request (2026-10-19) scored a
genuine 1.250-second Polish `Dzień dobry` WAV against an intentionally
wrong `Dobry wieczór` reference. It returned actual Accuracy 50,
Completeness 50, Fluency 100 — but it took **20,411.3 ms** and macOS
logged `CFNetwork SSLHandshake failed (-9806)`. An interactive
pronunciation lesson cannot afford frequent 20-second waits.

**One 20-second observation is not a latency distribution.** It might
reflect the SDK/WebSocket setup, network/TLS, service delay, short
utterance/end-of-speech behavior, or another transient cause. We have
not isolated which; don't blame a specific component yet.

## Compact experiment: four live Azure requests, zero Groq

Uses the TWO previously downloaded, SHA-pinned and verified
public-domain Polish native audio recordings and their **correct**
references — no need to test a deliberate mismatch again.

| Order | Exact original WAV | Scripted Azure reference |
| --- | --- | --- |
| 1 | `greeting-day.wav`, about 1.250 s | `Dzień dobry` |
| 2 | `greeting-evening.wav`, about 1.579 s | `Dobry wieczór` |
| 3 | Same `greeting-day.wav` bytes | `Dzień dobry` |
| 4 | Same `greeting-evening.wav` bytes | `Dobry wieczór` |

Each request creates a recognizer using the SAME real app-compatible
`azure_pilot.azure_scripted_assess` adapter, so the measurement is
a **cold-per-request SDK recognize_once wall time** on the owner's Mac.
It includes the local SDK setup, file streaming, transport and Azure
processing; it is not just server inference latency and it is NOT a
browser end-to-end measurement.

The runner saves attempt number, clip SHA, duration, Azure response
status, SDK elapsed milliseconds, safe cancellation enums and
provider raw uncalibrated scores (only three numeric fields).
Raw provider JSON/transcripts, credentials, error strings and recorded
audio are never copied into the new results file. The existing public
WAVs, manifest and earlier private results stay intact.

## Owner Mac — exact commands

In Terminal at the existing `path-to-polish` repo root, first pull
merged GitHub main and confirm that the existing **Azure Speech F0**
account has quota remaining, no paid billing/auto-top-up, and permits
these public-domain audio uploads. The explicit confirmation flags
do NOT enforce account-side no-charge settings.

```bash
git switch main && git pull --ff-only origin main
python3 v2/benchmarks/azure_auth_probe.py
```

**Stop if the zero-audio regional token probe returns anything but
`token_issuer_authorized` with HTTP 200.** In a new Mac Terminal,
`~/.zshrc` may still override the previously repaired Speech key.
Do not print the key, upload it, or put it in GitHub.

Preview exactly FOUR selected WAV uploads but do **zero** provider calls:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_short_latency.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01
```

After manually confirming existing F0/free/no-paid and audio rights,
execute FOUR explicit Azure requests, sequentially, without retries,
and persist each result as it completes to a **NEW** mode-0600 JSONL:

```bash
PathToPolish-Private-AI/.venv-speech-test/bin/python \
  v2/benchmarks/azure_short_latency.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --count 4 --send --approve-public-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/public-polish-live-01/azure-latency-four-01.jsonl
```

If you prefer just TWO requests as an initial check, use `--count 2`
with a different output name, never the same file. No implicit Groq,
no hidden retries and no charge attempt outside these approved calls.
If an SDK exception occurs, the runner keeps the completed earlier
results, saves the failed attempt's elapsed time without printing
provider error details, and stops.

To review the saved file later with **zero** inference:

```bash
python3 v2/benchmarks/azure_short_latency.py \
  --fixture-dir PathToPolish-Private-AI/public-polish-live-01 \
  --summarize PathToPolish-Private-AI/public-polish-live-01/azure-latency-four-01.jsonl
```

Share the printed **summary**, not raw JSONL, credentials, screenshots
of portal keys or unrelated recordings. A console SSL warning may be
reported verbatim if one appears, but the runner intentionally does
not scrape system logs.

## What constitutes a concern?

Treat these as **provisional product experience targets**, not
statistically established Azure SLAs:

- A **typical ~2–5 seconds** after the user taps "Check" would be
  meaningfully more acceptable than a 20-second wait.
- **>=10 seconds** for any completed response is cause to investigate.
- **>=20 seconds** is **unacceptable for the intended UX** even if
  Azure returns a perfect score.
- Canceled, inconclusive or recognized-but-unscored requests count as
  failures to deliver useful feedback, not as lightning-fast successes.
- Report **all request times**, median and worst for all attempts,
  plus median and worst for successfully graded responses separately.
  A sample of four **CANNOT** establish p95, root cause or production
  reliability; do not claim that four fast results clear the issue.

A matching-reference sample helps separate normal recognition latency
from the previous deliberately mismatched reference but it doesn't
isolate transport, network, service processing or warm/cold connection
by itself. Microsoft exposes connection management/preconnection in
the Speech SDK; **don't prematurely implement app-wide preconnecting,
automatic paid retries or user-facing timers before this measurement**.
Reference: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-control-connections

**Next engineering decision:** If repeated >=10-second responses or
failures occur, prioritize an actual app-level latency/reliability fix,
possibly using connection reuse or a bounded request UX, and then
re-measure with the same documented public audio; don't introduce an
unproven pronounce-as-graded XP requirement. If all four are quick,
collect a larger, time-separated sample before calling the slow tail
resolved. We should not delay all other MVP work based on one outlier,
nor ship a workflow that repeatedly stalls for 20 seconds.
