# E2E Speak with genuine public Polish speech (no provider credentials)

## Exact source fixtures

Two separately authored recordings are publicly described by Wikimedia Commons
as **public-domain** pronunciation examples. They match the **first two**
Conversation 1 built-in Polish Speak prompts:

1. `Dzień dobry` — recording by **Julo**, approximately 1.3 seconds:
   https://commons.wikimedia.org/wiki/File:Pl-dzie%C5%84_dobry-2.ogg
2. `Dobry wieczór` — recording by **SirPL0**, approximately 1.6 seconds:
   https://commons.wikimedia.org/wiki/File:Pl-dobry_wiecz%C3%B3r-2.ogg

The runner downloads original Ogg from Wikimedia Commons only after explicit
invocation, converts locally to 16 kHz mono PCM16 using ffmpeg, checks audio
structure/signal, and saves SHA-256 provenance for BOTH original and converted
voice. The browser's mocked MediaRecorder feeds those **real spoken sounds**
through the production audio decoder, local capture checks, replay, and
next-card lifecycle. No user data, browser mic or private speech is needed.

**This is not AI grading.** The browser uses no Azure/Groq key, uploads no voice
to AI services, and asserts no score appears when the private service is off.
The connected-browser mocked Azure path is separately tested in PR #43. Future
real provider testing can use these same clip WAVs *only after explicitly
reviewing upload rights and available free quotas*. Both clips are normal
Polish speech; neither simulates English-first mispronunciations, so a model
that passes this test may still be unsuitable for learner diagnosis.

### Execute locally with Internet access, ffmpeg and installed V2 frontend

From repo root:

```bash
python3 v2/benchmarks/public_polish_audio.py \
  --output-dir /tmp/ptp-public-polish
cd v2/frontend
npm run content
PTP_PUBLIC_POLISH_WAV_DIR=/tmp/ptp-public-polish \
  npx playwright test e2e/public-polish-speech.spec.ts
```

Use a **new empty** destination if rerunning; avoid overwriting original
fixtures and retain WAV hashes when comparing providers. Never add downloaded
audio, provider answers or audio transcripts to Git. The CI frontend lane
prepares these public fixtures in runner temp and exercises them in its
ordinary desktop/mobile browser E2E tests. A third-party Commons outage
is a fixture-acquisition failure, *not* evidence of a broken Polish mic
or AI model. No full Common Voice download or large FLEURS corpus is needed.

### What this actually tells us

- Authentic native Polish audio flows through the same normalizing browser
  capture path as a user recording, with valid duration, non-silence,
  pause/replay and deterministic phrase transition.
- The two speaking samples have independent public provenance, one by Julo
  and one by SirPL0.
- No hidden Azure/Groq calls happen for the offline/no-service default.
- Azure, Whisper v3 and Turbo **cannot** be ranked by this UX smoke test.
  The separately delivered offline adult three-engine runner can compare
  saved or explicitly authorized third-party results with matched WAV
  SHA and human labels. Measuring non-native learner mistakes still
  requires learner-like audio and independent Polish listening judgments.
