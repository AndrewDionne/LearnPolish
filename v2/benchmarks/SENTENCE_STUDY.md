# V2 Polish sentence, tempo and Azure pilot — owner setup

STATUS (2026-10-17): 10 REAL FLEURS long-sentence WAV candidates were downloaded into the owner's private folder; 3–4 sound preliminarily clear, the rest poor-mic, including two notably quiet. F0 Azure Speech was owner-confirmed and the Render token probe succeeded. No real Azure pronunciation assessment yet. Earlier one-word Commons originals remain unchanged and are not model-quality evidence.

## 2026-10-17 — Microphone-quality triage after physically reviewing first ten FLEURS clips

**Owner's actual listening findings:** 3–4 of the ten downloaded recordings
*sounded clear*. The rest had poor microphone sound and **two were
especially quiet**. This is a preliminary, recording-quality judgement,
not transcript verification or a fluent native-speaker's certification.
**Do not run Azure or Groq on quiet/distorted source recordings.** Do not
loudness-normalize bad microphone audio and call it gold-standard. Even
an attractive RMS/peak number does not establish native Polish,
transcript alignment or lack of distortion.

Pull latest main, then get an **offline acoustic report** of original,
unaltered WAVs. It reports RMS level, peak, near-full-scale clipping and
long low-level sections. These are advisory, not pronunciation scores:

```bash
git switch main
git pull --ff-only origin main
python3 v2/benchmarks/audio_quality_review.py \
  --manifest PathToPolish-Private-AI/sentences-source.json
```

To **replay and record microphone-quality labels interactively** directly
from the macOS Terminal (standalone Python script, no heredoc/EOFError):

```bash
python3 v2/benchmarks/audio_quality_review.py \
  --manifest PathToPolish-Private-AI/sentences-source.json \
  --review \
  --output PathToPolish-Private-AI/audio-quality-review-01.json
```

For each recording, the script plays the original using `afplay`;
enter **c** = clear, **q** = too quiet, **d** = noisy/distorted,
**u** = uncertain, or **r** = replay. It saves a **NEW, private**
SHA-indexed review JSON; it **never edits, replaces or deletes** the
original WAV or source manifest. Labels only describe recording quality:
`native_pronunciation_verified=false`, `provider_upload_approved=false`
remain unchanged and no Azure/Groq call is made. Do not mark the
three or four subjectively clear clips as verified Polish without an
independent Polish-fluent listener.

**Additional candidates without overwriting batch 01** (only if needed,
after examining the first review). New recordings are stored in a **new
child directory of exactly the same owner-selected research root**,
not a relocated folder:

```bash
python3 v2/benchmarks/fleurs_candidates.py \
  --source-dir PathToPolish-Private-AI \
  --offset 80 --count 10 --batch-name fleurs-batch-02
```

The above is **metadata preview only**. To authorize ten new public
dataset audio downloads, explicitly append `--download`:

```bash
python3 v2/benchmarks/fleurs_candidates.py \
  --source-dir PathToPolish-Private-AI \
  --offset 80 --count 10 --batch-name fleurs-batch-02 --download
```

This creates only `PathToPolish-Private-AI/fleurs-batch-02/` with
new `sentences-source.json` and unverified WAVs. If the new child
already exists, it **refuses overwrite**. A future 03 uses a new name
and non-overlapping offset. Avoid repeated bulk sampling of poor-mic
source audio indefinitely: after two candidate batches, reassess the
quality of FLEURS for this purpose and consider a higher-fidelity licensed
native Polish corpus or recorded professional speaker with authorized
evaluation reuse.

**Native review still required:** an independent fluent Polish speaker
must verify the actual transcript, natural and accurate articulation,
recording completeness, no clipping, source consent/rights for Azure,
and distinct speaker identities. Only then construct a *separate reviewed
subset* for `sentence_study.py`. Do not falsify review flags on rejected
samples. Azure receives exactly one original 1× WAV under F0 budget and
explicit consent; no sound-level claims from the quality report.

## First live Azure test: VERIFIED native Polish, not learner speech

**Binding owner instruction (2026-10-17):** The first physical
pronunciation-assessment test must be a **correctly pronounced, naturally
recorded Polish sentence by a fluent native speaker**, independently
listened to by a fluent Polish reviewer. Do NOT ask the owner to record a
beginner-level Polish phrase to establish the engine's positive baseline.
Do NOT use the two old truncated/ambiguous Commons word clips, assume that
dataset transcription proves good pronunciation, or treat TTS as the sole
gold reference.

1. Find licensed native Polish full-sentence recordings (~5–15 seconds,
   4+ words) with exact reference text. Candidate: FLEURS Polish
   `google/fleurs`, `pl_pl`, [CC BY 4.0 source](https://huggingface.co/datasets/google/fleurs).
   This is a **candidate**: individual clips must still pass independent
   native-human listening for natural articulation, completeness, speech
   clarity, no clipped starts/ends and precise transcript alignment.
   Document attribution, speaker anonymity/rights and service-upload
   permission.
2. Prepare the unchanged original WAVs and verified references under
   the existing Git-ignored `PathToPolish-Private-AI/`; do not move older
   recordings. `native_control` is already an accepted speaker role in
   `sentence_study.py` and `azure_pilot.py`.
3. First run offline source audit and 1× freeze; **first Azure test uses
   only one verified unmodified native original**. Azure's F0 pricing is
   owner-confirmed, but check actual quota/eligibility and use the explicit
   one-call consent and zero-paid gates. The Azure SDK result is uncalibrated
   evidence: examine whether genuinely good Polish gets sensible
   accuracy/fluency/completeness scores without assuming an answer.
4. After repeatable native controls, compare natural learner recordings
   with known human-labelled sound errors. Artificial 0.85×/0.75× slowed
   audio may be compared through Whisper transcription only; it does NOT
   substitute for naturally slow native or learner speech in a
   pronunciation-grade test.

**Current status:** Native source audio not yet imported/human certified;
no Azure speech-audio request yet. Do not imply the forthcoming FLEURS
dataset is already validated or downloaded.

## FLEURS Polish candidate importer (NEW; source material still needs human certification)

Google FLEURS is a real recorded multilingual speech dataset, including
`pl_pl`. The dataset card declares **CC BY 4.0**. We use the public
[Hugging Face Dataset Viewer rows API](https://huggingface.co/docs/dataset-viewer/en/rows)
to inspect bounded Polish validation rows, and their short-lived cached
audio links to fetch candidate WAVs **only upon explicit `--download`**.
No Hugging Face account/token, bulk Parquet shard, or Python dataset package
is required. Neither command uploads anything to Azure or Groq. If
Hugging Face denies requests, stop; do not bypass provider access controls.

**From Mac repo root**, leave the existing `Pl-czapka.ogg`,
`Pl-ciasto.ogg`, `commons-native-01/`, and their prior results untouched.

```bash
git switch main
git pull --ff-only origin main
chmod 700 PathToPolish-Private-AI
command -v ffmpeg
python3 v2/benchmarks/fleurs_candidates.py \
  --source-dir PathToPolish-Private-AI --count 10
```

The preview fetches **only one public dataset metadata page** (no media,
no voice upload, no inference). It considers recorded duration (5–15s,
from 16k FLEURS sample count) and requires at least four words in
`raw_transcription`, to skip old-style word fragments.

If the preview succeeds, **explicit candidate download**:

```bash
python3 v2/benchmarks/fleurs_candidates.py \
  --source-dir PathToPolish-Private-AI --count 10 --download
```

This fetches **at most 10 public dataset audio clips** from trusted
`datasets-server.huggingface.co` cached-assets, converts with FFmpeg
into 16k PCM16 WAV, validates signal and duration, and atomically
publishes only new `fleurs-pl-val-XXXXX.wav` files plus
`PathToPolish-Private-AI/sentences-source.json`. No overwrite, existing
file move, Azure/Groq inference or paid request. If a download fails, no
partly finished manifest is published. Every WAV has SHA-256 and a
traceable FLEURS row/split/reference/license entry. All new audio and
manifest remain Git-ignored and owner-private.

**CRITICAL: staged candidates are NOT yet verified correct native Polish.**
The generated manifest intentionally sets
`reference_verified_by_human=false`,
`audio_audited_unclipped=false`,
`provider_upload_approved=false`,
`speaker_id="REQUIRES_NATIVE_REVIEW"`, and
`review_status="UNVERIFIED_NEEDS_NATIVE_LISTENER"`. A dataset
transcription, gender field or audio file's existence alone is NOT proof
that a recording is by a native Polish speaker or pronounced accurately.
Do not run Azure or Groq against them yet.

Have an **independent fluent native Polish listener** listen to each
WAV, check that the full sentence is indeed spoken naturally and
correctly, transcript punctuation/words align, no clipped or repeated
words, clean microphone, and assign distinct anonymous real
`speaker_id` values based on actual distinguishable voices. If a clip
doesn't pass, exclude it rather than edit its expected text to make it
appear correct. Confirm FLEURS attribution/rights and third-party Azure
processing permission. Only for approved retained clips, manually
change the two review booleans to `true`, replace speaker ID, change
`review_status` to `NATIVE_HUMAN_VERIFIED`, and explicitly approve
provider upload **only when appropriate**. The JSON list must then
contain **8–12 passing distinct recordings from at least two confirmed
voices**; otherwise collect another verified set, using a different
`--offset` and a **fresh output/manifest name** rather than overwriting
any existing file.

Then run the current offline gate:

```bash
python3 v2/benchmarks/sentence_study.py \
  --manifest PathToPolish-Private-AI/sentences-source.json
```

After this passes, use existing `sentence_study.py --prepare` to freeze
the 1× positive-control WAVs and create 0.85× pitch-preserved Whisper
variants. The **first Azure sample must be ONE unmodified 1×
native-human-approved clip**, on the owner-confirmed Germany West Central
F0 Speech resource, using explicit consent/free allowance gates. None of
this native verification can be automated or faked with ASR/TTS.

## A. Required real sentence inputs

Use exactly the existing repo-root PathToPolish-Private-AI/ folder, never relocate source files. Add actual human-reviewed 16-kHz mono PCM16 WAV files (5–15 seconds, at least 4 reference words), plus a manually curated PathToPolish-Private-AI/sentences-source.json. The main trial needs 8–12 clean intact Polish utterances and at least 2 anonymous speakers. Include both naturally normal and naturally slow utterances from consenting adults. For each sample include:

    id: pl-sentence-01
    audio: your-real-sentence-01.wav
    reference: actual independently listened-to Polish sentence (4+ words)
    speaker_id: anonymous-native-a
    speaker_role: native_control OR adult_learner
    speaking_style: natural_normal OR natural_slow
    reference_verified_by_human: true ONLY after listening
    audio_audited_unclipped: true ONLY after listening for complete unclipped speech
    provider_upload_approved: true/false, explicitly permission checked
    source_license: documented rights (required native_control)
    source_page: https://actual-source-url OR local-consented:identifier (required native_control)
    adult_consent_confirmed: true (required adult_learner)

The above field descriptions are a schema, NOT valid JSON or fabricated sample data. For a real JSON example, add these keys as values in a list of 8-12 objects. You may investigate FLEURS Polish pl_pl, Common Voice Polish, or adult consenting speakers, but verify each transcript by listening, usage permission and attribution. No automated dataset download or invented text labels. Keep private voices/identifiers out of Git.

Audit only (no new files, no API):

    python3 v2/benchmarks/sentence_study.py --manifest PathToPolish-Private-AI/sentences-source.json

The strict 8–12 source gate can be relaxed to --min-samples 1 for an infrastructure-only smoke test; a tiny corpus is not a credible ASR benchmark.

Generate frozen original copies and pitch-preserving 0.85x versions (offline, in a NEW child of the same owner folder):

    command -v ffmpeg
    python3 v2/benchmarks/sentence_study.py --manifest PathToPolish-Private-AI/sentences-source.json --prepare --output-dir PathToPolish-Private-AI/sentence-study-01 --speeds 0.85

To include exploratory 0.75x use --speeds 0.85 0.75 on a new output folder. This NEVER moves, edits or deletes source audio. Each new manifest/WAV has a SHA256, original SHA, tempo flag and rights/human-review metadata. Output folder and files are private 0700/0600. Human-audition tempo derivatives before sending to any model; slower digital playback is not the same as naturally slow learner articulation.

## B. Groq recognition control (separate optional approved use)

The existing Groq pilot now permits WAV clips up to 25 seconds to accommodate 5–15-second source WAVs stretched at 0.75x. Each research group has its own private manifest: sentence-study-01/manifest.json = untouched original copies (1.0x), tempo-085-manifest.json = processed 0.85x copies. Compare v3 and Turbo on identical sources, using the established --transport curl. An exploratory dry-run for two models on original corpus is:

    python3 v2/benchmarks/groq_pilot.py --manifest PathToPolish-Private-AI/sentence-study-01/manifest.json --models whisper-large-v3 whisper-large-v3-turbo --transport curl --max-requests 24 --max-billed-seconds 400

These max numbers are preview-only ceilings, NOT approved consumption. Inspect actual planned requests/usage and the real Groq Free Plan status before any subsequent user-approved --send. We do not infer pronunciation from transcription.

## C. Azure pl-PL pronunciation assessment — one-sample gated pilot

Official supported Polish Speech locale and SDK:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment
https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.pronunciationassessmentconfig?view=azure-python

Only the user can inspect/create their Azure Speech resource. Before real calls: check actual resource is F0 (not chargeable S0), supported pl-PL Pronunciation Assessment, available free quota/current usage, region, and no paid billing or auto-upgrade. Published free Speech quotas alone cannot guarantee no charges. Never paste keys into GitHub/chat.

After compiling a HUMAN-VERIFIED real original manifest, a one-sample Azure preview requires no key, SDK, paid call, file write or voice upload:

    python3 v2/benchmarks/azure_pilot.py --manifest PathToPolish-Private-AI/sentence-study-01/manifest.json --sample-id pl-sentence-01 --max-requests 1 --max-audio-seconds 15

Selected sample must have provider_upload_approved true and be a 1.0x original with SHA-locked unchanged audio. Speed-stretched WAVs are never scored for pronunciation. Optional SDK for real Azure deployment:

    python3 -m pip install azure-cognitiveservices-speech

Local shell variables AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set privately to the actual Speech F0 resource. Example shell prompting (never print or commit key):

    printf "Paste Azure Speech key: "
    read -rs AZURE_SPEECH_KEY
    echo
    export AZURE_SPEECH_KEY
    export AZURE_SPEECH_REGION="YOUR-ACTUAL-RESOURCE-REGION"

Only after independently confirming F0 status, zero-paid-use safeguards, and speaker/provider upload permission, the user may explicitly authorize ONE raw assessment:

    python3 v2/benchmarks/azure_pilot.py --manifest PathToPolish-Private-AI/sentence-study-01/manifest.json --sample-id pl-sentence-01 --max-requests 1 --max-audio-seconds 15 --send --approve-voice-upload --confirm-resource-f0 --confirm-no-paid-billing --output PathToPolish-Private-AI/sentence-study-01/azure-pl-PL-01.json

The output is a new private 0600 JSON file of raw native provider evidence, no automatic retries, no synthesized sound diagnosis. Azure pl-PL may provide word/phoneme scores but phoneme NAMES are not supported the same way as en-US; prosody support is also limited by locale. Evaluate raw Azure scores against independent adult learner/native human reviews; never present them as calibrated automatically.

## Current gate

Software for offline auditable sentence corpus and tempo processing: implemented and CI-simulated, real corpus pending.
Azure F0: SDK driver implemented but NOT connected to an Azure resource or live tested.
Groq older one-word transport: already physically proven, retired as model-quality evidence.
No new paid inference/voice uploads approved. All private audio stays at the exact owner-selected PathToPolish-Private-AI/ directory; originals are never moved.
