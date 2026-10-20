# One overall score + Whisper colour hints — Świętokrzyska UX preview

**Experimental, offline, existing adult evidence only — 2026-10-20.**

The owner prefers the arithmetic mean of the original Azure word accuracy and the earlier Whisper text-similarity proxy, with **Whisper's colour-coded Polish syllables but NO numeric syllable ratings**. The prototype is intentionally **NOT** a general pronunciation grade or deployed learner flow. It uses no new model/paid calls and no new recordings.

## Physically observed values, identical existing WAV

- Azure scripted Polish accuracy: **84/100** on all three earlier owner-authorized SDK requests; the original two saved `azure-compare-01.jsonl` rows both report 84.
- Whisper v3 and v3-turbo guessed `Sweczo Seska` and `Sveczo Seska`. Our existing weighted Polish sound-grapheme alignment normalizes W/V and produces the same **50/100 text-similarity proxy** from both.
- Trial **combined overall: (84 + 50) / 2 = 67/100**. This is an **arbitrary equal-weight blend of different metrics**, not a calibrated phonetic accuracy percentage. The fact that 67 better matches the owner's personal impression for this recording is a reason to try the UX, **not evidence the average is more accurate than Azure**.
- **Four colour-only hints:** `Świę` amber (review), `to` amber (review), `krzy` red (possible mismatch), `ska` green (closer transcript match). No per-syllable numbers, no missing phoneme invented from Azure, no diagnostic claim that red definitely indicates mispronunciation. Existing English guide is OFF by default, toggled ON under the same coloured syllables.

## Try the real historical example locally — no external calls

From the Path to Polish clone **after pulling GitHub main**:

```bash
git switch main && git pull --ff-only
python3 v2/benchmarks/blended_pronunciation_preview.py --existing-sample
open PathToPolish-Private-AI/swietokrzyska-01/blended-preview-01.html
```

The CLI verifies that the existing original WAV, Azure and Whisper files still have **matching SHA-256/source IDs** and private permissions. It uses the stable historical original path and the **two prior Azure baseline rows**; the newer third Azure phoneme result is not needed and must remain untouched. It writes one new, owner-only `0600` HTML file in the ignored `PathToPolish-Private-AI/swietokrzyska-01/` directory. No voice files, transcripts, provider keys or personal data go to GitHub; **HTML has no network calls, scripts or embedded audio**. The page does not show raw Whisper guesses by default or per-syllable percentages. If the output already exists, simply `open` the existing HTML; never overwrite or automatically rerun any provider.

Manual alternative for another existing self-consistent authorized research evidence file set:

```bash
python3 v2/benchmarks/blended_pronunciation_preview.py \
  --wav <private-original.wav> \
  --azure-result <prior-azure-compare.jsonl> \
  --whisper-result <prior-whisper.jsonl> \
  --html-output <new-private-output.html>
```

This initial renderer intentionally handles only the authored `Świę | to | krzy | ska` case and one exact matching research evidence trio. If the Whisper models disagree about the proxy, Azure baseline accuracy differs between prior attempts, a sound segment doesn't align, files don't share the same source recording or provider evidence is incomplete, it **refuses to compute an apparently precise blended score**.

## Live learner workflow — still NOT integrated

The live Speak UI continues to show **Azure only**, with explicit opt-in consent and no Speech requests from public Render Free. The prototype does **not** silently send recordings to Whisper, Azure, or both. To implement automatic *per-new-take* blended scoring after the owner accepts the appearance, a separate authenticated dual-provider endpoint would be required with transparent informed consent for both uploads, strict rate limits/Free-tier policy and reliable failure handling. In practice two provider calls may increase latency/cost. Missing either source must **not** masquerade as a valid 50/50 blended score; fallback Azure-only can be labelled separately. The English guide and optional Sound Lab remain available; do not let the experimental combined score affect XP, leaderboards or lesson progression.

**Decision criterion:** Does a word-level combined estimate accompanied by categorical colour-only Whisper hints make practice feel clearer on the real sample? If yes, test on several independently human-rated Polish samples before introducing automatic live dual-provider grading. Keep it simple, fast, optional.
