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
3. Export **one consenting adult** 16-kHz WAV from V2 Speak, place it in a
   private folder outside Git, and generate a catalog-based manifest using
   `corpus.py` above. Example folder: `$HOME/PathToPolish-Private-AI`
   with `chmod 700 "$HOME/PathToPolish-Private-AI"`.
4. **Preview both model requests without upload** from the repository root:

       python3 v2/benchmarks/groq_pilot.py \
         --manifest "$HOME/PathToPolish-Private-AI/manifest.json" \
         --max-requests 2 --max-billed-seconds 20

5. Only **after** checking the console's free plan, adult recording consent
   and preview cap, explicitly approve the two uploads:

       python3 v2/benchmarks/groq_pilot.py \
         --manifest "$HOME/PathToPolish-Private-AI/manifest.json" \
         --max-requests 2 --max-billed-seconds 20 \
         --send --approve-voice-upload --confirm-free-plan \
         --output "$HOME/PathToPolish-Private-AI/groq-two-models-001.jsonl"

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
