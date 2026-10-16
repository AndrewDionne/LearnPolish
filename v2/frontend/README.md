# Path to Polish V2 — Foundation and Library / Learn preview

This is a **new React + TypeScript + Vite application** built inside the existing LearnPolish repository. It does not replace the legacy GitHub Pages app yet.

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

The production bundle is written to \`v2/frontend/dist/\`, intentionally **not** to legacy \`docs/\`. This is a development preview only; it does not change the live site.

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
- **Speak/pronunciation scoring**: Whisper large-v3 and corrected Azure need a benchmark; automatic audio grading is not included.
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
