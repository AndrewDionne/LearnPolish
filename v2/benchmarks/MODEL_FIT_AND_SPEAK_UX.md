# Path to Polish V2 — End-to-end Speak UX and three-model fit study

## Product decision (provisional, NOT a winning model claim)

Use **Azure Speech pl-PL scripted pronunciation assessment** for *reference-aware pronunciation* and compare its native Accuracy, Fluency and Completeness feedback against independent Polish listeners before assigning learner grades or phonetic drills. Its numeric scores are currently raw, not calibrated. Polish named-phoneme diagnostics/prosody should NOT be invented.

Use **Whisper large-v3** for accuracy-oriented *what words were actually said?* checks; compare it with **Whisper large-v3-turbo** for faster/cheaper recognition. **Neither Whisper model grades pronunciation.** ASR transcript disagreement is a prompt for replay/review, NOT evidence that a Polish sound was wrong. Do not send all three to every production learner by default; the three-engine route is a **one-take owner-triggered experiment**.

Manufacturer docs:
- [Azure scripted pronunciation assessment](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-pronunciation-assessment)
- [Azure supported features by locale](https://learn.microsoft.com/azure/ai-services/speech-service/language-support)
- [Groq V3/Turbo speech-to-text comparison](https://console.groq.com/docs/speech-to-text)

## E2E UX acceptance (GitHub synthetic evidence vs physical review)

The browser flow is **Home → Library → Speak → native example → record → local capture checks → replay → optional Azure request after explicit button press → feedback / inconclusive / quota limit → retry or next phrase → XP based on completed usable take, never on raw AI score**. The standalone/offline experience must continue without Azure. Rerecording clears stale feedback; next phrase clears playback and previous scores; no automatic provider upload.

CI's isolated connected-browser lane sets the opt-in frontend feature for tests only; routes Azure HTTP to a mock and uses synthetic local WAV/microphone. Real provider inference is never run from CI. The private family server is **not deployed**; the legacy production app is not switched. Native iPhone Safari/microphone, latency, cross-device account use, model calibration and guardian/privacy release gates remain open.

## Real model bake-off: a small useful start, not a perfect study first

Existing real results: both Groq Whisper variants transcribed Polish FLEURS originals, and Azure F0 returned one successful pl-PL assessment (93/93/92) on an original 5.64-second FLEURS clip. This proves basic provider integration; public/native FLEURS is *not* actual adult learner pronunciation and does not select a winner. Do not rerun those successfully completed requests.

**First new experiment:** one or two short **adult** Speak utterances from the real V2 interface, preferably one normal lesson phrase and one longer natural sentence. Avoid artificial silence padding, altered speed, noncatalog text, minors and private identifiers. The purpose is to expose short-utterance ASR failure/inconclusive and assessability in the **actual app audio format**. Later, collect a balanced 12+ set of adult learner errors, independent blind Polish listener labels and a separate fluent-native control. Keep a mix of sound contrasts and normal-speech lengths. Record the same original take for each provider, not successive different takes. The runner reports the bounded 3-call same-SHA experiment and measures each provider's actual elapsed response milliseconds; *no automatic retries or grades*.

### Private Mac operation, no provider request by default

Keep all previously saved FLEURS and Groq/Azure outputs exactly where they are. Put newly **exported** adult V2 Speak WAVs in a new restricted child folder, e.g. `PathToPolish-Private-AI/adult-speak-01/`. Nothing in `PathToPolish-Private-AI/` is added to Git.

From repository root:

```bash
git switch main && git pull --ff-only origin main
cd v2/frontend && npm run content && cd ../..
chmod 700 PathToPolish-Private-AI PathToPolish-Private-AI/adult-speak-01
python3 v2/benchmarks/corpus.py \
  --audio-dir PathToPolish-Private-AI/adult-speak-01 \
  --catalog v2/frontend/public/generated/lessons.json
python3 -c 'import json; from pathlib import Path; p=Path("PathToPolish-Private-AI/adult-speak-01/manifest.json"); print("Available recording IDs:", [r["id"] for r in json.loads(p.read_text())])'
python3 v2/benchmarks/learner_three_model_pilot.py \
  --manifest PathToPolish-Private-AI/adult-speak-01/manifest.json \
  --sample-id 'PASTE_ONE_LISTED_SAMPLE_ID'
```

The last command is a safe **PREVIEW_ONLY**, zero external inference, with three planned provider requests and same audio hash. Original private data stays in place. Never paste keys, recordings, raw transcripts or JSONL in chat.

**Only after** verifying original WAV belongs to a consenting adult, is suitable for both providers, existing Groq Free/Azure Speech F0 quotas remain available and both accounts are configured without paid charges or auto-top-up: invoke the same command with the three existing environment credentials loaded privately and flags:

```bash
python3 v2/benchmarks/learner_three_model_pilot.py \
  --manifest PathToPolish-Private-AI/adult-speak-01/manifest.json \
  --sample-id 'SAME_SAMPLE_ID' \
  --send --approve-adult-audio-upload \
  --confirm-groq-free --confirm-azure-f0 --confirm-no-paid-billing \
  --output PathToPolish-Private-AI/adult-speak-01/adult-three-model-01.jsonl
```

Single original WAV × Whisper V3 × Turbo × Azure = **three provider requests**. Existing keys stay on the Mac, NEVER in GitHub. Any failure stops without retry and preserves partial private evidence. Choose a NEW output filename every time. No paid use is authorized.

Offline evidence (even existing two-FLEURS saved JSONL can be assessed) is:

```bash
python3 v2/benchmarks/model_fit_review.py \
  --results PathToPolish-Private-AI/adult-speak-01/adult-three-model-01.jsonl
```

Optional **independent** blind Polish listener labels can be prepared using `v2/benchmarks/pilot_labels.py init --manifest ... --labels ...`, filled in privately by an adult fluent reviewer (heard words before seeing reference, then sound errors/target correctness) and passed as `--human-labels`. Review verifies label IDs and exact SHA against every provider row. Outputs **aggregate metrics only**, never recordings, verbatim human text or raw provider transcripts.

### What selects a production provider?

| Question | Evidence | Decision rule |
| --- | --- | --- |
| Did the learner say the intended words? | Whisper v3 vs Turbo WER against blind listener text, nonnative mistakes, failure rate | Choose fast Turbo only if it performs acceptably relative to v3 for *our Polish short phrases*. Global published WER cannot settle it. |
| Did they pronounce Polish sounds well? | Azure raw metrics vs human Polish judgments for clear good, intelligible-with-errors and poor speech; sound contrast examples | Use native Azure scoring only where it tracks human ratings. Never reinterpret ASR WER as phonetics or guess missing Polish phoneme names. |
| Is feedback genuinely helpful? | Same learner before/after targeted practice, blinded listener feedback and learner comprehension | Ship specific coaching only when it improves real outcomes and does not invent deficits. |
| Will the UX work on real phones? | Per-engine elapsed milliseconds from the three-model runner, plus real iPhone/Android mic, mobile Safari recording, unclear/silent recordings, no-match/quota/offline and abort on navigation | Prefer a model with reliable answers at acceptable response time. Preserve replay and progress when assessment fails. |
| Can we afford it? | Actual owner plan quota, measured service response time, per-request cost | Never silently upload to both Whisper models and Azure for normal learner activity. |

A passing synthetic/CI suite verifies orchestration, not pronunciation correctness, native Polish performance or legal consent. **No automatic winner should be published until we have labelled adult errors.**
