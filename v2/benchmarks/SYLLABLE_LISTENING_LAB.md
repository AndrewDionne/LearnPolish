# Private Polish syllable listening: original audio, not Whisper/TTS

**Research tool — no production scoring, no new AI use or costs.** This answers the owner’s question about hearing what they *actually said* by syllable instead of replaying the text that Whisper guessed. The existing `Świętokrzyska` reference breakdown is **Świę | to | krzy | ska**; native pronunciation-guide editorial review remains pending.

## What it means to replay Whisper’s "words"

Whisper ASR maps incoming voice features to a **written transcription**, not to newly synthesized speech. The hypothesis `Sweczo Seska` / `Sveczo Seska` does not contain a distinct stored recording of those guessed sounds. Running a Polish TTS rendering of that spelling through Azure would score **the TTS voice's pronunciation of an invented reference**, not the speaker's actual `Świętokrzyska` utterance. It is not a legitimate syllable-grade pipeline. Whisper's timestamp feature is word-level, not a trusted partition into Polish phonemes.

Instead: **one original WAV + known intended text → optional phonetic/forced alignment → verify timing by listening to the original syllable intervals → compare with native reference and sound-level evidence**. A forced aligner can locate audio phonemes even if a sound was mispronounced; its timestamps alone cannot grade pronunciation. Montreal Forced Aligner (MFA) has a Polish acoustic model and dictionary, but the official model card explicitly says it **cannot score goodness of pronunciation** and warns about training-data limitations on child speech. We have not downloaded or run MFA in this tranche; its use is optional pending local installation/licensing and verification.

References:
- https://github.com/openai/whisper/blob/main/whisper/transcribe.py (`word_timestamps`)
- https://montreal-forced-aligner.readthedocs.io/en/stable/user_guide/index.html (forced alignment)
- https://huggingface.co/MontrealCorpusTools/polish_mfa (model intended only for timing)
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment (`pl-PL` phoneme numeric scores; `en-US` syllable grouping/names)

## Usable today on Mac, **offline**

From the local LearnPolish clone after pulling `main`:

```bash
cd /path/to/LearnPolish
git pull --ff-only
open v2/benchmarks/syllable_listening_lab.html
```

The local webpage asks for **an existing original unaltered WAV** exported from V2 Speak (mono, uncompressed PCM16, 16 kHz, no more than 30 seconds/10 MB). It does not use the network, Groq, Whisper, Azure, or external JavaScript. The browser accepts an actual local file selected by the owner; the original stays on disk.

1. Click **Choose your original private WAV**. This is intentionally local file selection—no website upload.
2. Listen to the whole recording and drag the start/end markers to trim silence.
3. Drag the three syllable boundaries in the waveform or adjust the five keyboard-accessible sliders. Initial breaks are **evenly spaced and not automatically aligned**; listen carefully because consonants and vowels can overlap physically.
4. Use each **▶ Świę**, **▶ to**, **▶ krzy**, **▶ ska** button. You are hearing slices of **your original recorded signal**, not TTS or an approximation from Whisper.
5. If useful, click **Save timing JSON (no audio)** and move the downloaded file into the existing private `PathToPolish-Private-AI` directory. It contains a SHA-256 of the original WAV, segmentation times, and `scores:null`. Do **not** commit this metadata to GitHub, even though it contains no voice samples.

To produce actual separate WAV clips for private listening, put the **original WAV** and **downloaded timing JSON** directly under `PathToPolish-Private-AI/` (or a private 0700 child). Use `chmod 700` on their folder and `chmod 600` on the files:

```bash
chmod 700 PathToPolish-Private-AI
chmod 600 PathToPolish-Private-AI/my-original.wav \
  PathToPolish-Private-AI/ptp-private-syllable-timings.json

python3 v2/benchmarks/syllable_audio_clips.py \
  --audio PathToPolish-Private-AI/my-original.wav \
  --timings PathToPolish-Private-AI/ptp-private-syllable-timings.json \
  --output-dir PathToPolish-Private-AI/first-syllable-audition
```

The output directory **must not already exist**. The cutter verifies original WAV SHA, byte count, duration, reference, each continuous timestamp interval, and mono PCM16 format; outputs four private 0600 WAV files preserving the *exact original samples*, in new private 0700 folder. Fails closed on source mismatch/score fields and never overwrites output. The audio never leaves the machine and is not resampled or synthesized. The app's base WAV is untouched.

## How this advances legitimate by-syllable scoring

- The learner or native reviewer can *hear* how `Świę`, `to`, `krzy`, `ska` sound in the actual attempt, which may reveal the difficult cluster even without a grade.
- We can compare **human-reviewed timing** against a Polish forced aligner result and Azure's saved ordered phoneme score/timing data (if it exists on this reference).
- Audio snippets alone do not produce phoneme accuracy scores. Simply re-submitting cropped syllables independently to Azure may cause transcription/short-duration/context problems and consume calls. **We have not implemented such requests and do not recommend treating their results as comparable grades.**
- Native control recordings and human scores are still required. This lab is **private research-only**, not a new stage in the user's agreed minimalist Speak UX.

**Safety:** the code is statically stored in GitHub; no identifiable recordings, transcripts, provider keys or timing exports are pushed. There are **no added paid resources**. Separate validation is required before returning any `reviewed-acoustic-syllables-v1` percentages through the production API.
