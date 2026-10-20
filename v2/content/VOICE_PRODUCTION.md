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

## Candidate voices

- Zofia: `pl-PL-ZofiaNeural` — female primary candidate.
- Marek: `pl-PL-MarekNeural` — male alternate candidate.
- Agnieszka: `pl-PL-AgnieszkaNeural` — second female comparison.

**No voice has been selected as the instructional standard yet.** Verify voice availability for the owner's actual Azure region, then compare the actual speech for greetings, numerals, `c/cz/ć` and `s/sz/ś` listening exercises. Polish accent, timing, natural stress, soft palatal consonants and difficult clusters need native-speaker spot checks. Current Microsoft locale catalog lists these voices: https://learn.microsoft.com/pl-pl/azure/ai-services/speech-service/language-support?tabs=tts . Billing eligibility and terms are separate.

## Very small, explicit Azure voice audition — no automatic spend

The separate runner is **offline-only unless a user explicitly adds ALL guarded switches**. Its input comes from the same generated V2 catalog, not from manually retyped text. It writes only to a new `PathToPolish-Private-AI/voice-audition-01/` directory ignored by Git. Never copy private provider keys or raw recordings to GitHub.

**Safe preview, zero network:**

```bash
# From repository root, after npm run content above
python3 v2/benchmarks/azure_voice_audition.py
```

Default preview estimates **three requests for the SAME first greeting in Zofia, Marek, and Agnieszka**, to compare voice quality fairly. `--limit 24` previews the complete bounded eight-expression × three-voice list. No files or folders are written in preview mode.

**Only if the account owner independently verifies the Microsoft Speech F0 resource, zero-paid configuration, local voice availability and explicitly approves these provider requests**, the manually triggered *optional* three-clip command is:

```bash
# PRIVATE terminal environment only; do not paste key into GitHub or chat.
# Export AZURE_SPEECH_KEY and AZURE_SPEECH_REGION using your own approved secret setup.
python3 v2/benchmarks/azure_voice_audition.py \
  --limit 3 --send \
  --approve-generation \
  --confirm-speech-f0 \
  --confirm-no-paid-billing
```

**WARNING:** It sends 3 independent synthesis requests to Microsoft. Flags express the owner's confirmation; code cannot verify the account's free-credit balance or prevent external billing. The tool **never automatically sends**, retries, changes provider or silently falls back to gTTS. A missing private folder or previous `voice-audition-01` aborts; it never overwrites clips. Successful generated audio is saved with source-text and MP3 SHA-256, voice name and an **unreviewed** status in a local JSON manifest, rather than adding audio directly to app/production. A failed run may leave partial private files requiring review before a new attempt.

## Human quality and future release gates

1. Resolve the two fixed reference problems, after matching the actual audio or explicitly authoring new reference speech. Do NOT quietly change the displayed word while retaining the old MP3.
2. Review the first 58 target groups, Polish stress, existing English-friendly cues, and difficult letter combinations. Do not infer actual phoneme acoustics from syllable spelling partitions.
3. Compare the same audition prompt across all candidate voices, check naturalness with a native Polish speaker, then select a standard and one alternate.
4. Add a source-versioned audio variant manifest and a V2 primary/alternate voice selector **only when reviewed MP3s exist**. Preserve current default audio and offline playback until then.
5. Integrate future E2 dialogues as individually replayable turns with consistent speakers, followed by whole-dialogue listening. Do not expose a multi-speaker option based on invented audio.

**Scope in this tranche:** source-aligned inventory, failure-closed review exceptions, approved-voice candidate plan and gated test runner; no produced voice clips, no live pronunciation provider use, no replacements, and no voice picker shown prematurely.
