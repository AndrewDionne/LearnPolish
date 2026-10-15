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
- Basic reading and sound-example lessons; existing recorded audio plays through one controlled stream. Missing MP3s are explicitly marked unavailable.
- Deterministic content migration and inventory report, with sound-comparison content flagged for editorial review.
- Test coverage for content migration, schema, and progress arithmetic.

## Intentionally not built yet
- **Speak/pronunciation scoring**: Whisper large-v3 and corrected Azure need a benchmark; automatic audio grading is not included.
- Secure identity and cloud sync, offline download acknowledgements, comprehensive Read/Listen exercises, review algorithm, audio waveform analysis.
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
