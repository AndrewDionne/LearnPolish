# Polish speech/pronunciation benchmark — first increment

A **replayable, free-first benchmark harness**. **No service accounts are connected. No API calls, Whisper inference, or real learner recordings have been executed.** The smoke tests use synthetic WAV samples only. Benchmark outcomes must not be claimed before real recordings/human labels exist.

## Corpus manifest

A private JSON file with an array of recordings:

    [
      {
        "id": "contrast-cz-01",
        "audio": "recordings/contrast-cz-01.wav",
        "reference": "czekać",
        "azure_result": "azure-raw/contrast-cz-01.json"
      }
    ]

All files must be mono 16-kHz PCM16 WAV. Paths are **relative** to the manifest; absolute paths are rejected for portability. Never commit identifiable learner recordings, metadata or provider response files without explicit informed consent.

## Run deterministic dry checks

    python v2/benchmarks/benchmark.py --manifest path/to/private/manifest.json --engine dry-run

Checks WAV format, audio time budget, recording cap and missing speech. The default caps are **100 recordings and 600 seconds** per run.

## Whisper large-v3 baseline (local / no API calls)

Prepare a model directory separately (with documented local download and storage space requirements), install optional \`faster-whisper\`, and run:

    python v2/benchmarks/benchmark.py --manifest path/to/private/manifest.json \
      --engine whisper-local --model /path/to/pre-downloaded/faster-whisper-large-v3 \
      --output /path/to/private/whisper-v3-results.jsonl

The harness **requires an existing local model directory** and passes \`local_files_only=True\`, so it never silently downloads an AI model during the evaluation. It emits transcripts and exact-match comparisons only, **not pronunciation grades**. For a low-resource Mac, optional Groq free-API support can be added later behind an explicit quota guard and permission policy.

## Corrected Azure baseline

Capture **raw** \`pl-PL\` Azure Pronunciation Assessment JSON outside this repository, with identical audio and known reference text; then:

    python v2/benchmarks/benchmark.py --manifest path/to/private/manifest.json \
      --engine azure-raw --output /path/to/private/azure-results.jsonl

This mode performs **zero Azure API calls**, parses the supplied native scores/phoneme data and does **not** apply the old app's binary scoring or duration/energy penalties. It does not pretend offline JSON parsing constitutes a new Azure benchmark request. We still need to implement a properly configured Azure recorder/runner and obtain recordings with trusted reference labels.

## Future comparison gates

1. Same immutable audio for all engines; source recording identifiers and correct native Polish references.
2. Independent native-Polish ratings of intended-word accuracy, intelligibility, phonemes and stress.
3. Error consistency, repeated exact-audio results, short words/silence handling, non-native accents and false failures.
4. End-to-end latency, free API caps, privacy, and realistic production costs.
5. A separate **phonetic assessment** component (Whisper alone cannot grade articulation).

[See benchmark issue #1](https://github.com/AndrewDionne/LearnPolish/issues/1).


## Paired evidence comparison — no external calls

The new \`compare.py\` requires three **private, local** files: real saved \`whisper-local\` results JSONL, \`azure-raw\` results JSONL from **the same immutable audio**, and independent human labels such as:

    [{"id":"contrast-cz-01","intelligible":true}]

Run:

    python v2/benchmarks/compare.py \
       --whisper-results /private/whisper-results.jsonl \
       --azure-results /private/azure-results.jsonl \
       --human-labels /private/human-labels.json \
       --output /private/paired-comparison.json

It checks matching recording IDs, source references and durations. It reports ASR-recognition agreement with human intelligibility separately from Azure native phoneme data, and treats missing inference as **inconclusive**, not a failure or fake 0% grade. This is a comparison **tool**, not an actual completed model evaluation.

The V2 Speak UI can export one normalized 16-kHz WAV per chosen recording via a user-clicked local download, but keeps voice recordings ephemeral by default. **No data is uploaded or shared automatically.** Native-Polish human labels and actual model executions are still required. Avoid storing learner recordings in the public GitHub repository.


## V2 Speak: verified private research-corpus handoff

The fastest route from **consented real Speak recordings** to a reference-verified benchmark without copying audio into GitHub or requesting paid AI:

1. In V2 Speak, record a phrase and click **Save 16 kHz WAV for private AI test**. The exported filename includes its exact lesson-item ID and UTC timestamp, e.g. `ptp-speech-v1--Conversation_1%3A0--20261016T194218123Z.wav`. No learner name is embedded.
2. Put the exported WAVs in a **private folder outside the repository**. On a fresh clone, run `cd v2/frontend && npm run content` to build `public/generated/lessons.json`.
3. From the repository root, run:

       python v2/benchmarks/corpus.py --audio-dir /private/path/to/recordings --catalog v2/frontend/public/generated/lessons.json

   The script creates `manifest.json` in that private directory, with **no upload or inference**. It validates mono PCM16 16 kHz, 100-recording/600-second caps, signal usability, unique WAV hashes, and maps every recording ID to the exact Polish lesson reference. Unknown IDs or altered bytes fail closed. Personal lesson exports absent from the built-in catalog require a separate private reference procedure.
4. Validate: `python v2/benchmarks/benchmark.py --manifest /private/path/to/recordings/manifest.json --engine dry-run`.
5. For an actual evaluation, run Whisper large-v3 from a predownloaded local model and obtain correct Azure `pl-PL` native phoneme-assessment responses on the identical WAVs, using independently verified free/no-spend settings. Add independent native-human labels and run `compare.py`.

**Privacy:** Never commit or automatically upload learner recordings. Export is explicit on each usable take; normal recording is transient. The filename establishes the *intended phrase*, not that the learner pronounced it correctly. SHA-256 locks the local input bytes; provider execution provenance still needs real evidence, and no Azure request is claimed here.


## Active adult research pilot — 2026-10-17

See **[PILOT_PROTOCOL.md](PILOT_PROTOCOL.md)** for the immediate research
handoff. It supplies a compact Polish sound-contrast recording matrix,
explicit adult consent/privacy limits, blinded-first/target-aware-second human
review, native-speaker controls, the provider no-spend gates and evidence-based
acceptance criteria. The new standard-library `pilot_labels.py` generates
ungraded **private human evaluation sheets** from the SHA-256-locked manifest
and validates completed reviews without any provider calls. It refuses to
overwrite existing human ratings.

Example:

    python v2/benchmarks/pilot_labels.py init --manifest /private/polish-pilot/manifest.json --labels /private/polish-pilot/human-rater-a.json
    python v2/benchmarks/pilot_labels.py check --manifest /private/polish-pilot/manifest.json --labels /private/polish-pilot/human-rater-a.json

**Locale note:** Azure supports Polish (`pl-PL`) pronunciation assessment
but does not advertise Polish **phoneme names**, **spoken-phoneme alternatives**,
**syllable grouping**, or **prosody assessment** as offered for `en-US`.
An array of phoneme-level *scores* alone does not explain whether a learner
said `sz` instead of `ś`. Whisper large-v3 remains an ASR recognition
baseline, not a phonetic grader. No provider results or audio corpus exist yet.


## Groq Whisper Large v3 + Turbo — explicit free-tier research runner

`groq_pilot.py` tests **both Groq Whisper models** against the same consented adult
WAV bytes and stores model-specific recognition results, **never phonetic grades**.
It uses the standard Python library; no `pip install groq` required.
**Preview is the default and sends zero API requests.** All recordings remain
private unless you deliberately pass three upload/plan-confirmation flags.

1. In Groq Console, verify **Free Plan** on your real account and that no paid
   billing / auto-top-up is enabled. Free rate limits and paid model list differ;
   do not assume published free quotas apply to an upgraded account.
2. In a **Mac zsh Terminal session**, enter the secret without command history
   or printing it:

       printf "Paste Groq key: "
       read -rs GROQ_API_KEY
       echo
       export GROQ_API_KEY
       test -n "$GROQ_API_KEY" && echo "Groq API key loaded"

   Do not paste credentials in this chat, a GitHub issue, a shell command, or
   a file committed to the repository. This lasts only for that shell session.
3. Export **one consenting adult** 16-kHz WAV from V2 Speak into
   `PathToPolish-Private-AI/` (ignored by Git), and generate a catalog-based
   manifest using `corpus.py` above. Use `chmod 700 PathToPolish-Private-AI`.
4. **Preview both model requests without upload** from the repository root:

       python3 v2/benchmarks/groq_pilot.py \
         --manifest "PathToPolish-Private-AI/manifest.json" \
         --max-requests 2 --max-billed-seconds 20

5. Only **after** checking the console's free plan, adult recording consent
   and preview cap, explicitly approve the two uploads:

       python3 v2/benchmarks/groq_pilot.py \
         --manifest "PathToPolish-Private-AI/manifest.json" \
         --max-requests 2 --max-billed-seconds 20 \
         --send --approve-voice-upload --confirm-free-plan \
         --output "PathToPolish-Private-AI/groq-two-models-001.jsonl"

   This example intentionally allows only **one recording × two models**.
   Two or more WAVs fail closed under `--max-requests 2`. Choose another
   unique output filename on later runs; existing outputs are never overwritten.
   Only a user who has explicitly checked the provider account can claim that
   no paid billing is enabled: software cannot enforce cloud-account status.

The runner validates WAV type, usable level, duration, SHA-256, 25MB free-plan
file cap, hard API call count and *minimum ten billed seconds per request*.
It sends only audio, model, Polish language and decoding settings; it does
**not** prompt Whisper with target text. Results are written `0600` into
a private `0700` directory; the key is never written or echoed. It sends
**no automatic retries** on errors/rate limits and does not log provider
response bodies on HTTP failure. If an error occurs mid-run, the file may
contain partial successful results and must be reviewed before resuming.

Official documentation: https://console.groq.com/docs/speech-to-text ,
https://console.groq.com/docs/rate-limits .


## Curated, licensed **public native-Polish** recordings (no private speech needed)

Before collecting a learner's voice, we can run a **native-ASR sanity test**
with six human-recorded Polish pronunciations from Wikimedia Commons. These
are individual words—not news/podcasts—and each has an explicit **known word,
recording author, CC BY 2.5 or CC BY 4.0 licensing** and source-page citation.
The importer fetches the original Ogg audio and uses local `ffmpeg` to
convert it to 16-kHz mono PCM16 WAV, adding 250 ms leading and 500 ms trailing
silence to preserve very short clips. The byte fingerprint is computed *after*
conversion. **It never uses Groq/Azure/Whisper, and does not require any key.**

- `czapka` — Rogra — [recording](https://commons.wikimedia.org/wiki/File:Pl-czapka.ogg) — CC BY 2.5
- `ciasto` — Frizabela — [recording](https://commons.wikimedia.org/wiki/File:Pl-ciasto.ogg) — CC BY 2.5
- `źle` — Derbeth — [recording](https://commons.wikimedia.org/wiki/File:Pl-%C5%BAle.ogg) — CC BY 2.5
- `łyżka` — Derbeth — [recording](https://commons.wikimedia.org/wiki/File:Pl-%C5%82y%C5%BCka.ogg) — CC BY 2.5
- `szwedka` — Tsca — [recording](https://commons.wikimedia.org/wiki/File:Pl-szwedka.ogg) — CC BY 4.0
- `lato` — Derbeth — [recording](https://commons.wikimedia.org/wiki/File:Pl-lato.ogg) — CC BY 2.5

Use the **already downloaded** two contrast examples (one `cz`, one `ć/ci`), no API
charges. On a Mac, run these from the **LearnPolish repo root**:

    command -v ffmpeg >/dev/null || brew install ffmpeg
    chmod 700 PathToPolish-Private-AI
    python3 v2/benchmarks/public_native_samples.py \
      --source-dir PathToPolish-Private-AI \
      --output-dir PathToPolish-Private-AI/commons-native-01 --count 2

Creates `commons-native-01/manifest.json`, two `native-01.wav` /
`native-02.wav` files, and `ATTRIBUTION.txt`, all **Git-ignored within the repository**.
Files are *never overwritten*. To use all six, choose a new directory and
`--count 6` then increase your preview cap to 12 requests and 120 billed
seconds. Do not use the V2 Speak-specific `corpus.py` on public clips:
it expects distinct `ptp-speech-v1--...` lesson-export filenames. The
Commons importer already generates a valid benchmark manifest.

Validate **locally without connecting to any model**:

    python3 v2/benchmarks/groq_pilot.py \
      --manifest "PathToPolish-Private-AI/commons-native-01/manifest.json" \
      --models whisper-large-v3 whisper-large-v3-turbo \
      --max-requests 4 --max-billed-seconds 40

Only if your Groq **account really is Free Plan**, has no paid billing
enabled, and you agree to transmit these appropriately attributed
open-licensed samples to a third-party transcription service, use:

    python3 v2/benchmarks/groq_pilot.py \
      --manifest "PathToPolish-Private-AI/commons-native-01/manifest.json" \
      --models whisper-large-v3 whisper-large-v3-turbo \
      --max-requests 4 --max-billed-seconds 40 \
      --send --approve-voice-upload --confirm-free-plan \
      --output "PathToPolish-Private-AI/commons-native-01/groq-transcripts-01.jsonl"

This uses **your existing single `GROQ_API_KEY` for both models**. These
two sub-two-second public clips × 2 models are still subject to Groq's
**10-second minimum billed-audio usage each**, or at least 40 billed seconds
total. A small, free-tier-limited evaluation can still encounter rate limits,
and code cannot inspect your cloud billing settings. Do not claim any
pronunciation-grade result: these are **native speech recognition controls**
only. Their brevity makes them intentionally demanding ASR cases; follow
them with full sentences from a transcription-licensed corpus.

For longer, varied, transcript-aligned Polish speech, consider **Mozilla
Common Voice scripted Polish** (CC0, current version 27.0, but the full
4.49 GB download is large and dataset conditions prohibit rehosting or
speaker identification) and **Google FLEURS Polish `pl_pl`** (CC BY 4.0).
These have authentic spoken sentences and known text, unlike typical
YouTube news/podcasts, where reuse rights and word-level transcripts can
be uncertain. Respect provider terms and creator attribution; never assume
random web/news clips are public domain.


## Owner Mac HTTP transport: curl 200 / urllib 403 (2026-10-17)

Physical evidence from the same Terminal/key/account:
- Python `urllib`: **HTTP 403 on BOTH** GET `/models` and initial POST transcription.
- macOS `curl`: **HTTP 200 application/json on GET `/models`**.

This establishes a client/request-path difference, **not** the exact cause
(User-Agent, TLS fingerprint, intermediary filtering, etc. remain unproven).
It also does NOT prove that a curl *transcription* will be permitted.
Do not change keys, create new directories, bypass provider access policies,
or retry the rejected Python POST.

The benchmark now has an **explicit `--transport curl`** option, with the
same backend model allowlist, exact-WAV source checks, cap preflight, approval
flags, one-request-at-a-time/no retries, and 0600 non-overwriting results.
No third-party Python SDK installation required; macOS already has curl.
The implementation invokes curl without a shell, disables any user `.curlrc`,
and supplies the authorization header through **curl config on stdin rather
than process arguments**. Only allowlisted Groq URLs are reachable; keys and
full provider error bodies are not echoed or stored in result JSON.

**First step — read-only model access, no audio or model inference:**

    git switch main && git pull --ff-only origin main
    test -n "$GROQ_API_KEY" && echo "Groq key available in this Terminal"
    python3 v2/benchmarks/groq_pilot.py --check-access --transport curl

The response must list `whisper-large-v3` and
`whisper-large-v3-turbo` as `true` before attempting model comparison.
A listed model can still be restricted by your actual Groq account or project;
if the curl request is rejected, inspect your Console and contact Groq rather
than attempting to bypass provider controls. This GET does not upload WAVs
or consume transcription allowance.

**Optional later stage, ONLY after Free Plan and model permissions are checked
and you explicitly approve sending licensed Commons audio to Groq:**

    python3 v2/benchmarks/groq_pilot.py \
      --manifest PathToPolish-Private-AI/commons-native-01/manifest.json \
      --models whisper-large-v3 whisper-large-v3-turbo \
      --max-requests 4 --max-billed-seconds 40 \
      --transport curl \
      --send --approve-voice-upload --confirm-free-plan \
      --output PathToPolish-Private-AI/commons-native-01/groq-transcripts-curl-01.jsonl

The previous failed urllib POST may have left an empty
`groq-transcripts-01.jsonl`; use the **new, distinct results filename above**
rather than overwriting or deleting anything. Audio files **remain exactly
where the owner put them** in the ignored `PathToPolish-Private-AI/` directory.
This code is tested with mocked subprocess responses only; real curl
transcription results have NOT yet been observed.

## Mac first live Groq trial returned HTTP 403 — zero-upload diagnostic (2026-10-17)

**Observed on owner's Mac:** the two-source Polish Commons WAV conversion and
offline dry-run worked, with `planned_requests=4`, `estimated_billed_seconds=40`
and `network_requests_performed=0`. Their first explicitly approved live
Whisper request returned **HTTP 403**, before any transcript was returned.
Do not attribute this to WAV contents or Wikimedia's separate HTTP 429.

Official Groq error docs: `401` usually means missing/invalid credentials;
`403` means permission restrictions; `429` is rate limit.
Groq specifically returns **`model_permission_blocked_org`** or
**`model_permission_blocked_project`** for model access denied at the
organization or project level (org restrictions take precedence).
Docs:
- https://console.groq.com/docs/errors
- https://console.groq.com/docs/model-permissions

**First inspect the Console, without sending more voice:**
- https://console.groq.com/settings/limits — Organization → Limits,
  allow BOTH `whisper-large-v3` and `whisper-large-v3-turbo`.
- https://console.groq.com/settings/project/limits — Project → Limits
  for the project holding this API key, if applicable.
- Ensure the API key belongs to the correct active organization/project,
  and the account actually is on its intended Free Plan.

**Optional read-only terminal test** (no WAV, inference or billable
transcription; your original files never move). Make sure `GROQ_API_KEY` is
still loaded in your current shell. From the repo root:

    python3 v2/benchmarks/groq_pilot.py --check-access

This performs **one GET** to the Groq model list and prints only a safe
model-list summary, not your key. Even a successful model-list response does
**not** guarantee transcription rights: org/project limits can still block
a listed model. If the command itself reports HTTP 403, review the Console
or ask Groq support. There is no automatic retry.

**Output cleanup:** previous versions created an **empty** result file
(`PathToPolish-Private-AI/commons-native-01/groq-transcripts-01.jsonl`)
before the first refused request. Inspect safely:

    ls -lh PathToPolish-Private-AI/commons-native-01/groq-transcripts-01.jsonl
    wc -l PathToPolish-Private-AI/commons-native-01/groq-transcripts-01.jsonl

Do not overwrite, rename or relocate any Ogg/WAV/manifest. If that result
file is **zero bytes and contains zero lines**, the earlier failed call
produced no evidence. The updated runner now automatically removes **only
new empty result files on first failure**, while preserving partial successful
transcriptions. You may use a **new result filename** for the next expressly
approved attempt rather than deleting anything.

Once Console model permissions are verified, the exact four-call
Groq command in the authoritative-folder section may be retried with an
unused result filename only after confirming actual Free Plan and voice
upload approval. Successful native ASR recognition is not pronunciation
scoring. This investigation has made **no live provider requests** in CI.

## Authoritative research directory: `PathToPolish-Private-AI/` (owner-selected, FINAL)

**Do not move or rename existing recordings.** The owner already has the
original Commons files at the following exact, repository-relative paths:

    PathToPolish-Private-AI/Pl-czapka.ogg
    PathToPolish-Private-AI/Pl-ciasto.ogg

The root `.gitignore` ignores the entire `/PathToPolish-Private-AI/`
directory, and both benchmark scripts explicitly permit private WAV/JSONL
output there (while rejecting tracked `assets/` and `docs/`).
The previously suggested `repo/temp/` and home-directory paths are
**superseded** by this decision. Do not ask the owner to reorganize them.

Run from the repo root after syncing `main`:

    git switch main && git pull --ff-only origin main
    chmod 700 PathToPolish-Private-AI
    git check-ignore -v PathToPolish-Private-AI/Pl-czapka.ogg

Process **the original two downloaded Oggs in place** (never redownload):

    python3 v2/benchmarks/public_native_samples.py \
      --source-dir PathToPolish-Private-AI \
      --output-dir PathToPolish-Private-AI/commons-native-01 --count 2

The importer leaves both originals in their existing location, and creates
the `commons-native-01/` child with standardized WAV files, checksum-locked
`manifest.json`, and `ATTRIBUTION.txt`. It will not overwrite an existing
output folder: inspect it first and, only if empty, use `rmdir` on that child.

Preview both Whisper models **without Groq calls**:

    python3 v2/benchmarks/groq_pilot.py \
      --manifest PathToPolish-Private-AI/commons-native-01/manifest.json \
      --models whisper-large-v3 whisper-large-v3-turbo \
      --max-requests 4 --max-billed-seconds 40

Live inference is a **separate opt-in step**, only after checking the actual
Groq account Free Plan and approving sending these attributed Commons clips.
Use the same `GROQ_API_KEY` for both models:

    python3 v2/benchmarks/groq_pilot.py \
      --manifest PathToPolish-Private-AI/commons-native-01/manifest.json \
      --models whisper-large-v3 whisper-large-v3-turbo \
      --max-requests 4 --max-billed-seconds 40 \
      --send --approve-voice-upload --confirm-free-plan \
      --output PathToPolish-Private-AI/commons-native-01/groq-transcripts-01.jsonl

`git status` should never show ignored Ogg/WAV/JSONL; verify
`git check-ignore -v`. Gitignore does **not** provide encryption and can be
bypassed by `git add -f`, so never deliberately force-add private voices or
results. Neither conversion nor default Groq preview uploads recordings.

### Wikimedia HTTP 429 — safe recovery

Wikimedia sometimes returns HTTP 429 on direct audio downloads. The
downloader reports rate limits and honors `Retry-After` without automatic
retries or evasion. It publishes only complete manifests/converted WAVs and
cleans up failed temporary output.

**The owner has ALREADY downloaded the two Commons originals manually.**
Do **not** redownload them, create a second source folder or change their
location. Use the `--source-dir PathToPolish-Private-AI` command above.
The manual import does not contact Wikimedia. Neither conversion nor preview
contacts Groq.
