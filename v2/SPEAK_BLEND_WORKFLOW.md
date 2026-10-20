# Normal Speak — experimental combined Azure + Whisper feedback (2026-10-20)

## Current implementation in PR #73

The real V2 `Speak` component now supports the user's chosen minimal experimental feedback **on normal training lessons**: coloured, subtly spaced *Polish source text* plus one **overall combined number**. The arithmetic is
`round((Azure scripted word accuracy + Whisper transcript sound-unit similarity) / 2)`.
The owner Świętokrzyska test uses **Azure 84 + Whisper-proxy 50 = 67/100**, with amber/amber/red/green categorical text only. **Neither Whisper's percentages nor colours are verified phonetic measurements**; the combined 50/50 weighting is experimental and currently anchored to the owner's preference on one sample.

**Normal learner flow:** open built-in Lesson → Speak → hear existing example, optionally view pronunciation guide → record and replay → explicitly press *Check my pronunciation* with consent to **both** providers → same checked original WAV goes once to **Azure Speech pl-PL**, then once to **Groq Whisper large-v3-turbo** → server calculates categorical transcript-derived hints and overall composite → UI shows exactly the coloured Polish word, with a small CSS gap between parts, and one `NN/100` number. Retry clears old result. Next/XP remain independent of speech scores. No popup, colour legend, background chip, segment numbers or metric breakdown in the result area.

There are two distinct opt-in assessment routes:
- Existing `POST /api/v2/family/speech/assess` = **Azure only**, unchanged.
- New `POST /api/v2/family/speech/assess-blend` = **Azure + one Groq Whisper Turbo**, requiring an authenticated, verified session, authoritative built-in `item_id`, exact catalog segmentation, original bounded PCM WAV, both distinct form consents `approve_azure_audio_upload=yes` and `approve_groq_audio_upload=yes`, and shared durable daily usage caps (**12 per learner / 30 global per UTC day**). All failures are inconclusive and **never** synthesize 0 or a 50/50 blend from one provider. No automatic retries, history, audio/transcript storage, keys in browser or response, or raw model exceptions in logs/UI. The second provider is not contacted if the first returns an inconclusive result.

## Enable for an authorized local private test (NOT hosted Free yet)

The backend intentionally remains OFF by default. Set the following **only** in a private configured environment, once the account owner personally confirms the resource plans and no-paid billing, plus adult audio upload consent:

```text
PTP_SPEECH_ENABLED=1
PTP_SPEECH_F0_CONFIRMED=1
PTP_SPEECH_NO_PAID_BILLING=1
AZURE_SPEECH_REGION=germanywestcentral
AZURE_SPEECH_KEY=<PRIVATE_VALUE>
PTP_SPEECH_BLEND_ENABLED=1
PTP_GROQ_FREE_CONFIRMED=1
PTP_GROQ_NO_PAID_BILLING=1
GROQ_API_KEY=<PRIVATE_VALUE>
```

These are server-only. Never paste keys into GitHub/chat, never auto-set owner consent flags or invent free-tier verification. The React browser must connect to an authenticated private family API and build with `VITE_SPEECH_ASSESSMENT_ENABLED=true` plus `VITE_SPEECH_BLEND_ENABLED=true`. User's explicit *Check my pronunciation* button is the separate per-recording consent. If the frontend blended switch is unset, it remains Azure-only. The public Render Free service has `PTP_FAMILY_UI_MODE=offline` / family disabled / speech disabled: **this PR does not enable, deploy or pay for either service**. Family/minor guardian privacy and operational account checks are still pending.

## Training data backfill, exact source spellings preserved

The legacy lesson JSON remains the source until the separately planned content migration. `v2/frontend/scripts/pronunciation-segments.mjs` now attaches `pronunciationSegments` to the **generated** V2 catalog during `npm run content`/build. CI verified coverage:
- **482/482 existing items** have exact concatenating segments (`segments.join('') === polish`).
- **1 authored split**: the original Świętokrzyska guide `Świę | to | krzy | ska`.
- A subset now has editable, explicit source groupings in [`v2/content/pronunciation-segment-overrides.json`](content/pronunciation-segment-overrides.json), tagged `editorial-draft-v1` with `needs_native_speaker_review` provenance. The first 19 ordinary Polish vocabulary/phrase targets cover greetings, numbers and road terminology; reused exact phrases share one authoritative override. These are better-controlled spellings, **not** independent native-speaker or acoustic validation.
- Remaining automatically grouped content stays `draft-orthographic-v1`, consisting of conservative word and vowel/consonant heuristics preserving Unicode spelling, punctuation and spaces. For phrases, matching spans include inter-word whitespace in the preceding part.
- Draft boundaries are not verified Polish syllables and must not be described as genuine acoustic boundaries. If an item changes, V2 rebuilds its metadata reproducibly. Unsupported groups or invalid source fields fail closed rather than inventing scores.

**Next data pass:** triage high-frequency and high-difficulty words (particularly `cz/sz/ś`, `rz/ż`, soft consonants, nasal vowels and words with `i` palatalization) with native Polish reviewer and explicit per-item authored boundaries; review generated draft splits using lesson preview. Do not bulk certify 481 automatically produced groups or reuse English approximation as acoustic ground truth.

## Test scope

All GitHub tests use synthetic voices/mocks and make **zero real Azure/Groq requests**. Unit tests verify historical 84/50/67 math, W/V normalization, no per-segment numeric grades, incomplete-provider outcomes, rate/consent/auth privacy. Frontend tests reject malformed hints and unauthorized synthetic provider fields. A connected Playwright fixture checks normal Speak navigation, exactly one blended endpoint request containing both per-take approval fields, minimal highlighted text+single score, no leaked transcript, and reset on retry. CI is not real iOS audio/real model inference; owner's adult physical test is required before activating externally.

**Known concern:** Both external requests are sequential to avoid spending a Groq request when Azure has already failed; total response latency may exceed the earlier Azure-only 2–11s. Future improvement may use parallel providers if owner prioritizes latency after physical measurement, but never introduce hidden extra retries/paid calls.
