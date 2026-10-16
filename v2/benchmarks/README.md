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
