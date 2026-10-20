# V2 reference-audio production — first 58 Speak exercises

**Status: PREVIEW / owner audition pending (20 October 2026).** This procedure does not replace or remove existing audio. It does not authorize any paid Microsoft speech use, audio upload or automated grading. PR #76 fixed the teaching priority; issue #77 tracks the voice-choice and pronunciation-data tranche. The existing V2 deployed UI continues to use one bundled MP3 per item and does **not** yet show a voice selector.

## Grounded inventory

E1.01 `Conversation_1` 26, E1.02 `contrast_c_cz_cie` 6, E1.03 `contrast_s_sz_sie` 6, E1.04 `numbers_1-20` 20 = **58 real V2 items**. All 58 have existing imported reference MP3s. Their **actual legacy voice identity and recorded content are NOT proven by file existence**, nor are existing English respellings validated. Exactly two greeting targets must be corrected against recordings before automatic comparison:

- `Conversation_1:24` — `Jak ma pan/pani na imię?`: choose a fixed grammatical alternative, preferably separate cards if both are needed.
- `Conversation_1:25` — `Mam na imię…`: author a complete named response or retain ungraded.

The remaining **56** have fixed written prompts but still need an actual listening/native review. Their `pronunciationSegments` are exact-concatenating spelling annotations, **not** calibrated acoustic pronunciation labels. Of the 58, current override entries remain `editorial-draft-v1` and others `draft-orthographic-v1`; avoid calling them native certified. Sound contrast lessons intentionally reuse existing individually recorded source MP3s.

## Current code boundary and planned architecture

Existing `v2/frontend/scripts/prepare-content.mjs` copies `docs/static/<lesson>/audio/` MP3s and emits a single `item.audio` path. Existing V2 `useLessonAudio()` plays only bounded, same-origin `generated/audio/<lesson>/<index>.mp3` sources. **Neither exposes per-user voice selection today.** V1 had an Azure TTS helper with `pl-PL-ZofiaNeural` and `pl-PL-MarekNeural`, plus a gTTS fallback. Neither means an imported recording is certified to be from that voice.

V2's intended **versioned voice manifest** will maintain one verified canonical spoken reference, authoritative segmentation/optional English pronunciation guide, source audio and any separately approved voice variants with provider, voice ID, source-text hash, MP3 checksum and reviewer status. An alternative voice will be exposed in the learner UI only after its exact audio variant exists and has passed review. Playback remains static, offline-capable and instant; **never do network TTS on Play**. A natural full-word reference is the audio source, rather than disconnected artificial syllable clips. Sound-contrast teaching and two-person short dialogues can use reviewed native voices in the future. Keep learner speech scoring (Azure+Whisper) separate from synthetic voice production.

## Run the complete offline inventory

From the **repository root**:

```bash
git switch main && git pull --ff-only origin main
cd v2/frontend
npm run content
npm run audit:voice
npm run audit:voice -- --json
```

The last command prints all 58 exact Polish/English/source-audio entries; source MP3 SHA-256; pronunciation segments and provenance; the two blocked prompts; missing/non-aligned English guide status; three unapproved candidates and **24 potential audition clips**. `audit:voice` hashes the *existing* MP3 bytes but **does not** inspect their language, naturalness or identity. It does not modify data, create an audio file, call an external API or enable remote scoring. Changed target text, missing audio, unlisted blocker, wrong sound-contrast ID, duplicate voice or stale sample spelling fail closed. This audit is part of `npm run check`.

## Owner's ranked candidate voices (2026-10-20)

The owner compared Polish voices in Microsoft's browser demo and stated the following **preferred order**, now the authoritative *audition priority* in `voice-production.json`:

1. **Marek — `pl-PL-MarekNeural`: provisional primary voice**, male.
2. **Agnieszka — `pl-PL-AgnieszkaNeural`: provisional alternate voice**, female.
3. **Zofia — `pl-PL-ZofiaNeural`: third choice**, female.

**Specific qualitative observation:** Zofia sounded good overall, but a bit **clipped at the end**; Marek and Agnieszka both had **better follow-through**. This is the owner's real listening preference, not an objective acoustic measurement or native-speaker certification. Preserve the perceived phrase-ending quality as a release gate: compare the same source text at word/sentence ends for final vowel/syllable completion, consonant release, cadence and unwanted audio-truncation; don't prematurely blame the voice if an MP3 encoder or playback clip is cutting off its tail. Audition hard Polish consonants, normal stress and connected speech before bulk rendering. Short teaching prompts and multi-line dialogue turns can behave differently from demos.

**Decision boundary:** This approves **ranking for planned auditions**, *not* paid audio generation, replacing legacy audio, enabling speech assessment, or deployment. The old "Zofia as main teaching voice" proposal has been superseded by the owner's preference. The default current app still plays its original, unverified imported MP3. Wait for final reviewed, local MP3s before wiring Marek/Agnieszka as user-selectable production audio.

Current Microsoft locale catalog: https://learn.microsoft.com/pl-pl/azure/ai-services/speech-service/language-support?tabs=tts . Billing eligibility and terms are separate.

## Actually hearing the voices — corrected UX (2026-10-20)

The first `python3 v2/benchmarks/azure_voice_audition.py` **only printed a JSON preview**. It was never meant to play speech, but the absence of an audible comparison was understandably confusing. There are now **two clearly different ways to hear voices**:

**1. Hear available Azure voices immediately (without our own paid synthesis):**

```bash
# From the repo root; opens Microsoft's public online demonstration
python3 v2/benchmarks/azure_voice_audition.py --gallery
```

Or visit **https://speech.microsoft.com/audiocontentcreation** directly. Select **Polish (Poland)**, then audition **Zofia**, **Marek** and **Agnieszka** with exactly the same words: `Dzień dobry. Dziękuję. Przepraszam.`. Microsoft's lightweight online demo offers Play without connecting this project's private Azure credentials. This is a **Microsoft browser demonstration**, not our own local files and not a verified sample of all 24 planned expressions. The voice gallery may change UI/availability over time.

**2. Listen to our exact Polish sample recordings once you have consciously generated a private audition:**

```bash
# AFTER the owner has explicitly sent and received private Azure recordings,
# this opens the offline local audio comparison HTML; no provider inference:
python3 v2/benchmarks/azure_voice_audition.py --listen
```

Once the optional `--send` command below has completed, it writes a private `PathToPolish-Private-AI/voice-audition-01/listen.html` page containing native browser audio controls for each generated voice. It groups recordings by the same Polish phrase for side-by-side listening; missing clips show **Not generated** instead of fake Play controls. The player verifies the approved item ID, phrase, candidate voice, source-text hash, local audio file and SHA-256 against the manifest before opening. It uses only local MP3s, no remote fonts/scripts/APIs, and never overwrites old recordings or exposes them to the public app.

If `--listen` reports that no recordings exist, that's expected until the user has independently confirmed free-tier/no-paid usage and intentionally run the gated `--send`. **Do not interpret that as a failure of the app's existing audio**. This audition HTML is owner-private, not a public V2 voice switcher.

## Owner-preferred paired Marek/Agnieszka pilot — NO audio created automatically

Now that the owner has ranked **Marek first, Agnieszka second, Zofia third**, the useful test is **matched phrases in the two preferred voices**, not 24 clips from all three voices.

**From repo root after pulling current GitHub `main` and running `cd v2/frontend && npm run content && cd ../..`:**

```bash
# No API call, no files created: print the FIRST FOUR matched phrases × TWO voices
python3 v2/benchmarks/azure_voice_audition.py

# Also zero calls: preview all EIGHT matched phrases × TWO preferred voices
python3 v2/benchmarks/azure_voice_audition.py --pairs 8
```

**Default paired pilot** = **8 suggested MP3 clips, 4 exact vocabulary phrases**:

| Prompt | Why in the first test |
|---|---|
| `Dzień dobry` | End of a common two-word greeting, natural cadence |
| `Dziękuję` | Nasal spelling, natural ending vowel |
| `Przepraszam` | Consonant cluster and final `m` |
| `Sześć` | Difficulty: `sz` vs `ś` and a crisp final consonant |

The other four planned samples (`Pięć`, `Cztery`, `plac`, `Śródmieście`) are available by using `--pairs 8`. Zofia stays a *reserve*: the existing legacy `--limit 3` selector still previews the first phrase across all three voices if a full comparison is desirable, but she is **not generated in the default paired pilot**.

**No production generation or billing is authorized merely by reading this command.** Only after the owner *independently confirms* a valid Azure Speech F0/no-paid account, private credentials, and the intended request count, an optional, explicit real call would be:

```bash
# OPTIONAL, ONLY after personally verifying the zero-paid/f0 resource.
# Sends 8 TTS synthesis requests for 4 expressions (4 × 2 voices).
python3 v2/benchmarks/azure_voice_audition.py --pairs 4 --send \
  --approve-generation --confirm-speech-f0 --confirm-no-paid-billing
```

Then play only actual, source-hash verified local MP3s:

```bash
python3 v2/benchmarks/azure_voice_audition.py --listen
```

This gives a single private comparison page with two columns, Marek and Agnieszka, and no fake Zofia player. `--limit` and `--pairs` cannot be combined. The source/planning manifest still contains **24 potential 3-voice clips**, but the default sends/previews **only 8 potential 2-voice clips**. Generation stays strictly **no-overwrite** (even on partial failures), outputs privately into the existing Git-ignored folder, never alters lesson audio or does TTS on player clicks. The CLI preview prints the proposed request and character counts, while actual requests remain gated.

**Listening acceptance checklist:** play every paired phrase end-to-end on headphones; confirm final sounds are complete and not abruptly chopped; contrast final `m`, `ę`, final cluster `ść`; check stress, natural tempo, word spacing, rhythm and clarity of hard/soft sounds; compare any truncation across voices and check whether a player/encoder trims the tail. The result is a **human audition decision**, not acoustic ground truth. Independently native-review Polish text/segmentation and the two unresolved Greetings references before publishing.

## Human quality and future release gates

1. Resolve the two fixed reference problems, after matching the actual audio or explicitly authoring new reference speech. Do NOT quietly change the displayed word while retaining the old MP3.
2. Review the first 58 target groups, Polish stress, existing English-friendly cues, and difficult letter combinations. Do not infer actual phoneme acoustics from syllable spelling partitions.
3. Compare the same audition prompt across all candidate voices, check naturalness with a native Polish speaker, then select a standard and one alternate.
4. Add a source-versioned audio variant manifest and a V2 primary/alternate voice selector **only when reviewed MP3s exist**. Preserve current default audio and offline playback until then.
5. Integrate future E2 dialogues as individually replayable turns with consistent speakers, followed by whole-dialogue listening. Do not expose a multi-speaker option based on invented audio.

**Scope in this tranche:** source-aligned inventory, failure-closed review exceptions, approved-voice candidate plan and gated test runner; no produced voice clips, no live pronunciation provider use, no replacements, and no voice picker shown prematurely.
