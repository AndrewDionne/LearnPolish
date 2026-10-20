# Path to Polish — canonical V2 frontend

**This React + TypeScript + Vite frontend is the canonical Path to Polish application.** GitHub Pages deployment is built from this folder after green V2 CI on `main`. Historical V1 HTML/Flask under `docs/` and `app/` are retained only for reference and current one-way lesson/audio migration, not as the application entry point. Public static hosting does not imply that the separate private family API or Azure assessment backend is deployed.

## Run locally

Requirements: Node 22+ and npm, installed at the repository root.

    cd v2/frontend
    npm install
    npm run dev

Open the local Vite URL (normally http://localhost:5173). The predev script reads the existing repository's 23 legacy lesson JSON files, migrates them to a versioned manifest, and copies any matching MP3 reference audio into ignored \`public/generated/\`. No AI service credentials or backend are required.

Run checks:

    npm run check

To prepare a distributable build:

    npm run build

The production bundle is written to \`v2/frontend/dist/\`, **not** to legacy \`docs/\`. The tested V2 bundle is the only intended GitHub Pages publication artifact. Enable **GitHub Actions** as the repository Pages source for the public URL to switch from V1.

## Implemented in this slice
- One design/navigation system for desktop and mobile: Home, Library, Practice, My progress.
- Search/filter all migrated lessons (23 sets; 488 items) and resume most recent.
- Flashcards with controlled reveal, previous/next, self-rated recall and browser-local progress.
- Personal vocabulary/reading/sound lesson authoring, rename/edit/delete, JSON import/export and browser-local lesson persistence; no Git write or server is involved.
- **Read:** Polish passages, translation reveal, progress and saved reading position across reloads.
- **Listen:** audio-first multiple-choice comprehension (and reveal/self-assessment fallback for tiny sets), transcript only after answering, 0.75×/1×/1.25× playback, and separate mode-specific progress. Listen is shown only when reference audio is available.
- Existing recorded audio plays through one controlled stream. Missing MP3s are explicitly marked unavailable; media load failures have explicit error feedback.
- Deterministic content migration and inventory report, with sound-comparison content flagged for editorial review.
- Test coverage for content migration, schema, and progress arithmetic.

## Intentionally not built yet
- **Automated pronunciation scoring**: Whisper large-v3 and corrected Azure need an evidence-backed benchmark. Speak capture and replay are now implemented, but **nothing is graded**.
- Secure identity and cloud sync, offline download acknowledgements, richer word-aligned reading annotations, authored listening questions, review scheduling, audio waveform analysis.
- Sound lessons are *preserved but unverified*. Some contain several comma-separated examples in one card; these must be reauthored into phoneme-by-phoneme exercises.
- User progress in this preview is **local browser storage only**, not cross-device and not permanent if site data is erased.
- No bundled third-party AI model, requests to paid endpoints, or credentials.

## Engineering notes
- \`scripts/prepare-content.mjs\` uses the old docs as a **one-time migration source**; future canonical content must live outside the legacy output tree. Current preview rebuilds from legacy files to keep all lessons accessible without duplicating hand-authored data.
- If reworking the content schema, migrate stable lesson/item IDs and persisted progress together.
- Audio controls never autoplay or advance on timers, and switching lessons stops the previous player.
- Refer to \`../../V2_REBUILD_PLAN.md\`, \`../../chat ai workflow.md\`, issues #1 and #2 for the durable roadmap.

## Personal lessons (second V2 increment)

From **Library → Create lesson**, write a lesson name, choose Vocabulary, Reading or Polish sounds, and enter Polish/English pairs. You can edit, export or delete it from within the lesson. **Library → Import lesson JSON** accepts the portable V2 single-lesson format; it assigns a fresh ID and deliberately strips all untrusted audio URLs. Local-browser storage is not cloud synchronization: export your lesson JSON files to back them up. Imported lessons have no reference audio until a future validated media workflow is added.


## Read / Listen implementation tranche

- Reading lessons begin in **Read**, remember their last passage by stable lesson ID, and provide translated passages with explicit progress controls. Word-level highlighting is intentionally not fabricated: the current MP3 collection has no verified word timings.
- Lessons with matching pre-existing reference MP3s offer **Listen**. This is **comprehension practice**, not a pronunciation score: the Polish text is hidden until the user chooses an English meaning; outcomes are stored under separate mode-qualified progress keys. Lessons containing no safe reference audio do not offer Listen, rather than pretending TTS works.
- All modes share one audio player. Mode changes, lesson changes and passage changes stop the previous recording; speed options are 0.75×, 1× and 1.25×. Audio file validation prevents arbitrary network URLs from an imported lesson.
- Pronunciation coaching/Speak, fully offline audio cache, real graded listening content and physical iPhone Safari certification are not implemented.


## Verified offline access (production build)

Use \`npm run build && npm run preview\` to test the offline-capable PWA (the Vite **dev** server intentionally does not register a service worker). On the first online visit, the service worker installs the core app HTML, bundled JS/CSS and lesson catalog. The lesson toolbar offers **Download for offline** when a built-in lesson has an existing MP3 reference recording.

Downloads show file-by-file progress. The UI says **Offline ready** only when every requested audio file has been verified in persistent Cache Storage. Failed downloads do not display as complete, and users may retry or remove saved lesson audio. Offline Read/Listen playback and locally saved progress do not call external AI services. Polish pronunciation scoring remains unavailable offline.

Limitations: Safari can evict browser storage; audio is downloaded to this device only, not synchronized to an account. Private user-created sets currently have no safe reference MP3 media and therefore no audio-pack download control. The page shell is cached for offline use after successful PWA installation; cold first loads require a connection. Native iPhone testing is still pending.


## Speak — recording foundation, NOT pronunciation scoring

In any vocabulary or Polish-sound lesson, select **Speak**. The learner can hear the pre-recorded example, request microphone permission on demand, capture up to 10 seconds, stop, replay, or discard a take by moving to another item. No audio is sent over the network or persisted, including when offline. The sample is revoked on navigation.

The browser chooses a supported MediaRecorder MIME type (MP4 on Safari where supported; WebM/Opus on Chromium). After capture, it attempts to decode the recording locally into **mono 16kHz PCM16 WAV**, with acoustic validity checks for very short, near-silent, and clipped recordings. Inconclusive captures show a reason and permit immediate retry; they are **never converted to a 0% pronunciation grade**. Unsupported codecs/permissions show an explicit message, while navigation remains functional. The normalized audio plus its validation metadata are future provider-adapter inputs, not a reason to select a scoring service.

The **recording is intentionally not stored** even as progress. The per-item Speak journey does not award recall/pronunciation points; scoring will only be introduced after human-labelled evidence supports a calibrated model. No automatic Azure/Groq/Whisper requests, provider account, API key or billing is required for this capability. Browser tests stub a microphone; native Safari microphone validation is still required before release.


## Spaced review (self-rated recall)

Learn mode now schedules each item after the learner selects **Got it** or **Needs practice**. Remembered items return after 1, 3, 7, 14, 30, 60 or 90 days (capped); missed items become eligible again immediately. Open **Practice → Scheduled review** to focus on only due cards in a particular lesson. Session identity is frozen when started so marking an item does not skip later cards; the schedule persists in this browser and survives page reloads.

Read/Listen success is distinct from Learn recall, and Speak **never** creates pronunciation scores or review grades. A review plan is not synchronized between devices yet and is not an adaptive AI estimate; it is a transparent first version to be tuned after real user experience.


## Sound lab — V2 individually playable contrast lessons

The three old letter-recognition sets contained several spoken words *inside one sound recording*. They are preserved in Git but **retired from V2's catalog**. Four hand-authored **comparison curricula** replace them, with 22 independently playable existing recordings for C/CZ/Ć, S/SZ/Ś, Z/Ż-RZ/Ź-ZI, and L/Ł.

The build process requires every chosen sound example to match an exact existing source lesson/card and already copied MP3; a mismatched source text or missing audio fails the build. Sound-group identity, IPA symbol, short articulation note, and audio provenance remain in versioned content schema rather than being inferred by LLMs. The sound lab displays groups side by side and allows selection or playback of one example without playing three unrelated words consecutively. Speak remains an ungraded local recording exercise.

**Editorial gate remains open:** The original MP3s, articulation descriptions and selected words have not yet undergone native-speaker quality validation. These are sound contrasts with whole-word examples, **not verified minimal pairs**. Dedicated isolated phoneme recordings and real minimal-pair lesson sets need a separate sound-quality and content review.


## Back up and restore ALL local learning data

**My progress → Export full backup** downloads a portable, human-readable Path to Polish V2 JSON with your personal lesson definitions, individual learning attempts, spaced review dates, reading positions and last-opened lesson ID. It does **not** contain microphone recordings, audio files, tokens or passwords.

**My progress → Restore from backup** validates the file schema, exact personal-lesson identities, data size and review history, then displays a confirmation **before** replacing the current browser's local learning state. An invalid backup or declined confirmation leaves existing data unchanged. Use it when switching browsers/devices until secure cross-device sync ships. Full backups are separate from single-lesson JSON exports.

Personal lessons cannot reference arbitrary external audio URLs. The restore process deliberately accepts text-only lesson items. Offline MP3s are packaged in the app and can be downloaded again; Cache Storage is not included in the exported JSON.


## Automated accessibility and responsive UX audit

The V2 UI includes an accessible skip-to-main link, main-content focus after route changes, active-nav state, correct Polish language spans for screen readers, keyboard-visible focus for inputs and authoring controls, and minimum touch target sizes for sound comparison and mode controls. Mobile bottom navigation respects the safe-area inset.

Playwright now audits Home, Library, Learn/Listen, Sound Lab, personal lesson authoring and Profile on desktop/mobile, including 320px compact layouts. Checks include serious/critical WCAG accessibility violations (axe), browser page errors, horizontal overflow, keyboard skip-link navigation and captured screenshots. Automated WCAG checks do **not** replace an actual expert accessibility or native VoiceOver review. Screenshots are CI artifacts for future inspection; do not equate screenshot capture with manual visual review.


## Read/Listen authored dialogue checks and learning pathway

The six legacy reading-dialogue sets remain intact (same stable IDs and audio files). Their V2 manifest now carries an explicit **six-step suggested practice sequence**: Foundations → Daily life → Getting around. These are **editorial navigation stages, not CEFR proficiency certifications**.

24 selected dialogue turns have author-written comprehension checks grounded in the exact Polish source line, with a question, three distinct answer options, one correct response and a brief feedback explanation. The migration rejects a source-text mismatch, duplicate answer or invalid choice; each graded item must have a reference MP3. The question data is versioned in \`v2/content/reading-checks.json\` (editorial status: awaiting native-Polish review).

**Read:** On an authored passage, answer a comprehension question before its English translation is shown. Optionally reveal translation without answering, then self-assess. Unauthored passages still support read/reveal/self-assess and saved passage position.

**Listen:** Authored dialogue turns use the source-grounded question without displaying the transcript beforehand; selecting an answer reveals the Polish, English, correctness and explanation. Unauthored dialogue turns offer **ungraded** reveal and self-assessment, not random distractors from unrelated dialogue lines. Vocabulary and Sound Lab lessons retain their simpler English translation-recognition exercises.

No grades imply validated Polish phonetics or official language level. Native review, richer contextual passages, variable difficulty within lessons and certified audio quality are not yet completed.


## Earned Gold — work-based rewards (V2 revival)

The original Path to Polish offered Gold, a 500-Gold weekly goal, total lifetime Gold, daily study streaks and a custom weekly-goal option. V2 restores those mechanics with a transparent **10 Gold per completed activity per unique item/mode/local day**. Learn, Read and Listen award on a completed learning response, independent of correctness; Speak awards **only when an actual recording passes the local capture-quality check** and the learner advances. Skipping earns none. Revisiting/restarting the same item/mode on the same day does not multiply Gold. A weekly-goal milestone is celebratory, not an extra spendable reward. Gold is intentionally not a pronunciation accuracy metric, paid currency, or server-validated competition.

Home shows Gold toward the goal. My progress shows total Gold, weekly Gold, current streak, and **Path goal (500)** or **self-directed** goal. Rewards are device-local and included in the full backup/restore JSON. Pre-reward backups remain importable with an empty ledger. Clearing practice also clears earned Gold with an explicit warning. The original selectable pierogi avatar family and further character-expression states are preserved as legacy assets, not yet rebuilt in V2.

## AI test capture (no model claim)

After successfully recording a Speak item, click **Save 16 kHz WAV for private AI test** to explicitly export the locally normalized mono PCM16 WAV. No audio automatically leaves the browser. See \`../benchmarks/README.md\` for a private, consent-based corpus manifest, offline Whisper large-v3 runner, corrected saved native Azure result comparison and human-labelled analysis. The comparison utility is tested with synthetic fixtures; **neither Whisper inference nor Azure requests have been executed**. The user must supply consented recordings and an available local model/private Azure raw data before empirical results can be reported.


## Mode-to-mode completion and Pierogi character revival

After finishing a Learn/Read/Listen/Speak session, the completion screen shows Gold newly earned in that session and direct handoff buttons to other available modes within the *same lesson*, without returning to the library. Choosing a mode resets that mode's card and playback state. No score is invented for Speak.

My progress again offers the original **four selectable Pierogi characters** (Hero, Chonky, Tall, Junior) using the original SVG artwork retained in this repository. Avatar identity is stored alongside Gold and included in full local backups. Weekly goal completion switches the portrait into its available original happy/winning expression; the avatar artwork is precached by the production PWA so this remains available offline. This is the base revival of the character system, not a complete animation/milestone economy; deeper mood changes and customizations remain future UX polish.


### Collect private empirical pronunciation samples

Speak now exports optional timestamped WAV filenames that preserve the exact exercise identifier. The local-only Python `../benchmarks/corpus.py` uses generated V2 lessons to create a reference-verified, checksum-locked manifest for actual model comparison without typing Polish references manually. Voice files stay outside Git and no hosted services are contacted. The deterministic tests verify capture and metadata integrity, not pronunciation accuracy.


## Private family group API (development integration)

V2 now contains an isolated private family API and an opt-in Family panel below the open Poland map. **It is not deployed by this repository change.** The panel is explicitly disabled when \`VITE_FAMILY_API_URL\` is absent. For provisioning, HTTPS, required persistent storage, invitation/account flows and security boundaries, read \`../server/README.md\`. Never configure it with an ephemeral database.

After signing in, family members can join using a one-use invitation, choose their group and **explicitly opt in** to contributing *future* eligible built-in lesson activity to a server-side shared map. Members can independently choose regions. The server ignores claimed client XP and validates known lesson IDs, modes, deduplication and region targets. Group boards show weekly XP, regularity and highest catalog tier; improvement recognition stays unavailable until verified evidence is available. Local offline XP and family XP remain separate; no automatic uploads of historical backup data, personal lessons, recordings, or voice scores.


### Friendly weekly family recognition

The family scoreboard now includes separate, evidence-grounded tabs for **Effort** (weekly eligible XP), **Consistency** (distinct practice days), **Trailblazer** (highest built-in difficulty *attempted*, not mastery), **Team contribution** (weekly expedition XP), and **Most improved** (an honest no-data state until independently verified comparable outcomes can be accepted). Ties share a rank; members with no activity receive no fictional first-place award. Tabs use existing server-calculated member metrics, not untrusted client-derived performance data. In a connected group the invitation/create-group forms are initially collapsed under **Manage groups and invitations**, making the team map and achievements the primary visual focus. No changes to the underlying XP economy and no model inference.


## Opt-in Speak pronunciation feedback (behind family account + deployment gate)

After an actual live Azure Polish scripted Pronunciation Assessment
proved provider connectivity (FLEURS test, raw Azure 93 accuracy,
93 fluency, 92 completeness, **not human-calibrated**), the V2
Speak journey now has an optional **Check my pronunciation** action.
It is visible ONLY when a trusted private family API is configured,
`VITE_SPEECH_ASSESSMENT_ENABLED=true` is intentionally set at
build time, and a verified family account is connected. Otherwise
the existing local-only mic capture/replay and optional WAV export
continue unchanged.

The button always requires a **second deliberate click after
recording**, with an explanation that this take will be processed
by Azure. It sends one WAV to the server over authenticated HTTPS;
the **server** holds the Azure key and determines the expected Polish
text from the built-in lesson catalog. No arbitrary personal content
or raw credential comes from the browser. On return, the UI displays
only raw Azure Accuracy/Fluency/Completeness with clear
uncalibrated disclosure and no false named-Polish-phoneme coaching;
inconclusive is NOT 0 points. New recording, card navigation or
unmount aborts an in-flight browser upload. Raw provider scores do
NOT feed XP/leaderboards or invent Most Improved evidence.

The underlying private family server is still UNDEPLOYED; this
is a development integration contract and unit/browser-mock-tested
UX, **not a working public production scoring service**. See
`../server/README.md` for explicit F0/no-paid gates, account
authorization, quotas and audio privacy. No automatic provider
requests or spending enabled in default builds.

