# Świętokrzyska — single-call Azure phoneme feasibility test

## PHYSICAL TEST COMPLETE — 2026-10-20 (do not rerun)

The owner completed the preview and **exactly one additional real** Azure Speech F0 request on the same original 3.12s adult voice (SHA-256 `0f4ff4b3d01165dc5e27fd9c10336f19aedf4aefdca430798c2b1777e5df1626`). Existing result `PathToPolish-Private-AI/swietokrzyska-01/azure-phoneme-01.jsonl` is authoritative **and must not be overwritten or resubmitted simply for an alternate grouping**.

| Physical observation | Result |
|---|---|
| Actual provider requests this tranche | **1 Azure; 0 Groq/TTS** |
| Overall accuracy / word accuracy | **84.0 / 84.0** |
| Fluency / completeness | **100.0 / 100.0** |
| SDK total time | **11,250.9 ms** |
| Valid, time-ordered phoneme scores | **10** |
| Named Polish phones | **0** |
| Authored grouping hypothesis `Świę/to/krzy/ska` | **5/2/3/3 = 13**, not matched |
| Four-group diagnostic | **None** (`null`) |
| Legitimate learner syllable grades | **Not available** |

`status=phoneme_evidence_only`; `reason=phone_count_differs_from_authored_hypothesis`; `can_publish_learner_syllable_grades=false`. The instrument behaved correctly: it **did not** partition 10 anonymous phoneme scores according to an invented alternative grouping. A different 10-phone partition would merely hide the mismatch; word estimate **84** is uncalibrated and **cannot** be distributed over the four printed syllables.

Latency is also a product risk: this run took **11.25s**, versus 1.92s and 2.46s previously on the same source. Three observations are not a reliable p95 or benchmark, so avoid claiming either the worst or best is typical.

**Agreed simplest viable path:** discontinue automatic syllable-grade research for this iteration; show the legitimate single-call Azure **word pronunciation estimate** (with accurate caveat), retain retry/Next and optional English guide and KRZY Sound Lab. Do not add forced alignment, manual syllable slicing or another AI model. No more provider calls without new owner authorization/free-tier check. This private evidence remains on the owner's Mac.



**2026-10-20. One original adult recording, one Azure request, no Whisper, no manual clipping or forced alignment.** The owner wants a fast word score and four syllable ratings *only if reliable*.

## Already observed — on this exact 3.120s original recording

- Azure scripted Polish assessment, ordinary: **accuracy 84, fluency 100, completeness 100**, SDK total **2459.7 ms**.
- Azure preconnected run: **84, 100, 100**, SDK total **1923.3 ms**.
- Both attempts processed the same WAV SHA-256 `0f4ff4b3d01165dc5e27fd9c10336f19aedf4aefdca430798c2b1777e5df1626`.
- These are real scores from the owner's earlier two Azure calls; the two completed rows in `azure-compare-01.jsonl` **do not contain word/phoneme breakdowns**. There is no way to derive a valid syllable breakdown from the previously saved aggregate 84 without examining new information. Do NOT run the previous two-call latency test again.

## Minimal experiment added in this tranche

`v2/benchmarks/swietokrzyska_one_azure.py` is preview-only unless explicitly consented and `--send` is used. It uses the existing Azure Speech SDK adapter with **Phoneme granularity**, same reference `Świętokrzyska` and same original, source-hash-locked adult WAV. There is **one** Azure request, not two; no Groq/TTS/Whisper calls, no additional inference per syllable, no automatic retry.

It inspects *only* a single matched word and its ordered numerical phoneme scores. Polish doesn't provide Azure native syllable groups or named phoneme identity. A narrow experimental hypothesis for this one word is:

| Written syllable | Approx. expected sound units | Hypothesized score count |
|---|---|---:|
| Świę | ś + devoiced w + j + ɛ + n | 5 |
| to | t + o | 2 |
| krzy | k + devoiced rz + y | 3 |
| ska | s + k + a | 3 |

**Crucial:** This count map is a *linguistic hypothesis*, not Azure model documentation. Different treatment of nasal `ę`, coarticulation, sound reductions or the provider's internal tokenization can yield a different number of phones. Even if Azure returns exactly thirteen ordered timed phones, count equality **cannot prove** each phone corresponds to our hypothesized unit. A private diagnostic might calculate the unweighted mean over the putative groups only to judge whether this avenue warrants further testing. Such numbers are labeled **`candidate_not_validated`**, never copied into `reviewed-acoustic-syllables-v1` or shown in the live Speak UI. A mismatch, missing timing/phoneme values or a different recognized word produces **no candidate syllable numbers**. All results say `can_publish_learner_syllable_grades=false`.

The output stores only a sanitized `0600` private JSONL containing actual Azure aggregate/word scores, phoneme count and **at most** four tentative means. No raw WAV, raw SDK response, recognized transcript, provider identifiers, keys or unbounded exception text is written or printed.

## One-time owner Mac command

From your local project root (where `PathToPolish-Private-AI` already exists):

```bash
git switch main && git pull --ff-only

WAV='PathToPolish-Private-AI/swietokrzyska-01/ptp-speech-v1--speak_swietokrzyska%3A0--20261019T123345890Z.wav'
PY='PathToPolish-Private-AI/.venv-speech-test/bin/python'

# Step 1: verify SAME original audio + saved credentials not read, ZERO calls
"$PY" v2/benchmarks/swietokrzyska_one_azure.py --wav "$WAV"
```

Review the initial **`PREVIEW_ONLY`**, `planned_azure_requests:1`, `azure_requests_sent:0` output. Stop if the WAV is missing, the original SHA doesn't match or you can't personally confirm the account is still on **Azure F0 with no paid billing/autotopup** and adult audio reuse is authorized.

Only after those independent conditions are verified, perform the **single** requested new assessment:

```bash
"$PY" v2/benchmarks/swietokrzyska_one_azure.py \
  --wav "$WAV" \
  --send --approve-adult-audio-upload \
  --confirm-azure-f0 --confirm-no-paid-billing \
  --output 'PathToPolish-Private-AI/swietokrzyska-01/azure-phoneme-01.jsonl'
```

The credential is automatically read from the existing private `PathToPolish-Private-AI/.env.azure-speech` by `speech_env.py`. **Do not paste or re-enter keys here**. Preserve old `azure-compare-01.jsonl` and `whisper-01.jsonl` unchanged. If the new output path already exists, the script will refuse to overwrite; use the offline report option first. No auto retries if the provider is inconclusive.

To review the single saved result again at **zero cost**:

```bash
"$PY" v2/benchmarks/swietokrzyska_one_azure.py \
  --wav "$WAV" \
  --report 'PathToPolish-Private-AI/swietokrzyska-01/azure-phoneme-01.jsonl'
```

The safe small diagnostic printout can be shared for interpretation (exclude any key, raw recording, voice transcript or contents of other private files). It will contain a word estimate plus a phoneme count, and either **unverified four-group means** or an explicit reason grouping was withheld.

## Acceptance decision

- **Pass to next short experimental review:** one exact-word Azure result with coherent 13 ordered timestamped phoneme scores; grouped means reasonably different for reliably difficult/accurate syllables on at least a small set of independently rated native and learner recordings.
- **Do not launch as real syllable grades:** a coincidental 13-phone count or uncalibrated score means only. Need some evidence that Azure's unnamed phone sequence and hypothesized boundaries agree, and human listener results correspond to these numbers. If not, avoid further complexity and ship the **word-level Azure score alone**, as the owner directed.
- **UX stays unchanged:** Listen → record → one Azure score → retry or Next; optional existing KRZY Sound Lab practice link. No manual waveform, MFA model, second engine, XP thresholds or phoneme-based correction text.
