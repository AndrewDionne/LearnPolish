# Path to Polish V2 — learner-first UX/UI standard

Owner directive: 2026-10-23. **Physical device, microphone, native-speaker, and human visual testing remain deferred.** GitHub source/PR/CI is the implementation authority.

## Product rule

The exercise **is** the interface. On repeat use, the learner should primarily see the current Polish expression, a listening/recording/reveal control, immediate honest feedback, and the next action. Do not erect a second workflow of detailed diagnosis, advice, explanations, or skill assessments. The learner is directing their own practice; the product is **not** a language expert.

1. **Minimal by repetition** — keep copy only if it is necessary for the current decision, missing/error/offline status, safety/consent, or irreversible local-data management. Remove motivational slogans, release/version badges, walkthroughs above every card, engineering diagnostics and duplicate progress descriptions. Keep explicit controls discoverable and keyboard accessible.
2. **Truthful feedback** — self-rated recall remains self-rated. Speak may show only the existing experimental overall 0–100 estimate and existing verified matching word-level colour hints (no legend or extra advice). Use **coloured text**, never score heatmap backgrounds, per-syllable grades or phoneme authority inferred from transcription. English pronunciation cues appear only when the learner turns on the guide, with slight syllable separation. A miss/timeout/inconclusive is **not** a zero.
3. **Consent and cost** — never auto-upload microphone audio or retry paid/provider calls in response to simplifying the UX. Preserve per-take affirmative user action and concise processing-party/storage disclosure when assessment is enabled. Public/offline practice does not advertise a grade. Mic errors, permission state, no-reference source limitations and quota errors remain honest and actionable. Existing raw-data non-persistence and explicit private export must remain.
4. **Polished, consistent graphics** — coherent hand-authored vector navigation/tool art, useful typography, a restrained accent palette, consistent small/medium/large hierarchy, predictable spacing and tap targets. Decorative UI must not masquerade as lesson content or earned achievements. This is a coherent interim visual treatment, **not** final approval of a unique Path to Polish brand identity.
5. **Intuitive progress** — Home Continue resumes the next unseen Learn card; Library opening remains deliberately predictable; at session completion the next authored lesson is optional, never forced. Modes are clearly labelled; no extra modal, advice page, completion gate or fabricated milestone.
6. **Preserve boundaries** — the 26 original sets/482 items and 455 original MP3s, 1–20 two approved batches, 0.75/0.85/1 audio speeds, 14 unapproved reference recordings, private family groups and independent local/group XP ledgers stay unchanged. No new storage schema, accounts, scoring weights or external API usage in a visual-cleanup slice.

## UX-01 first implementation (branch `feat/v2-ux-minimal-learning-surface`)

- Replace mismatched text/emoji-like nav and lesson artwork with one SVG icon family; present a simple typographic Polish home illustration rather than floating cartoon circles.
- Remove placeholder “local learner”, motivational, V2 preview and navigation-section microcopy. Show the **actual active lesson title** as the lesson heading; remove repeated instructions in Learn/Listen/Read and optional technical footnotes in main navigation screens.
- Preserve the visible control to play, reveal, rate recall, record, replay, explicitly request an assessment, switch mode, navigate and continue. No XP/review logic touched.
- In Speak, retain the existing source-linked blend colour hints and optional pronunciation guide, but suppress reserved acoustic per-syllable grading, background heatmap, caption, latency metrics, Azure's fluency/completeness drill-down and tutorial score text. Only a single experimental aggregate remains. Maintain explicit consent and collapsed private options.
- Add desktop/mobile synthetic tests asserting minimal chrome, actual lesson titles, intact actions, optional guide presentation, absence of the disallowed diagnostic grade UI and privacy-safe connected mock assessment.

**Required merge gate:** four final-head GitHub Actions CI jobs PASS; no screenshot, real-device, acoustic/linguistic or brand sign-off claimed. Correct any synthetic accessibility, 320px overflow, route, tab focus or regression failure before merge.

## Subsequent review queue (separate small, mergeable PRs)

1. **UX-02 — Library and Practice density:** keep author/backup controls accessible without placing import/export on the main learning path; simplify repeated counts/labels while preserving staged discovery and progress truth.
2. **UX-03 — family Profile, Groups, Expedition:** visually consolidate scoreboards, identity editing and open map into one typography/control system; explicit opt-in and team-vs-local XP boundaries must remain visible *where they matter*, not as repeated lengthy disclaimers.
3. **UX-04 — session action cadence:** verify small-screen focus, audio and recording state transitions, single-tap Next/Retry, consistent CTA order and immediate result placement. Do not initiate automatic upload or unvalidated pronunciation recommendations.
4. **UX-05 — brand acceptance:** review vector treatment, refined colour palette, font/spacing tokens and small/large screen screenshots with owner; final logo/brand artwork requires a separate deliberate choice.

## Manual testing deferred, not waived

Human review is still needed for real iPhone/Safari mic permission, acoustic usefulness of Azure/Whisper overall scores and colour hints, native spoken references, actual visual polish, and whether the UI feels intuitive after sustained use. Synthetic Playwright, Vitest and CI prove deterministic contracts only.
