# V3 UX-04A — iPhone UI/UX and pronunciation acceptance

**Owner priority (2026-11-11):** Validate all five navigation-tab responsibilities and the source-matched coloured-word + single overall-score experience **before** another curriculum tranche. This is an owner/device acceptance guide, not proof that a physical test has happened.

**Source state:** UX-04A implementation commit `b3cb989dfd105db3b58e2cb7e694fd629e6f05b1` passed native Simulator compilation, curriculum/media checks and XCTest in [Actions #43044266104](https://github.com/AndrewDionne/LearnPolish/actions/runs/43044266104). Draft [PR #169](https://github.com/AndrewDionne/LearnPolish/pull/169) stays open; physical test is unverified. Use the current branch head for the device build, not this historical SHA.

## Run the actual SwiftUI app

Use the existing isolated iPhone-build setup described in [IOS_DEVICE_SMOKE.md](IOS_DEVICE_SMOKE.md) so the production checkout remains undisturbed. Run `git status --short` and `git worktree list` before creating/reusing a worktree; do **not** overwrite a dirty device-test worktree. The existing `v3/ios/scripts/open-ios.sh` prepares the original source-locked content/audio, generates the Xcode project and opens it. Choose the **PathToPolish** scheme and physical iPhone in Xcode. This is the full V3 native SwiftUI app, not the legacy browser or an audio-only spike.

## UX acceptance — work through in this order

- [ ] **First open:** Home appears without forced sign-in, onboarding account, CloudKit prompt or network requirement. Today XP and attempts start at genuine local values; a new learner has no invented history or family score. One primary Continue opens Practice.
- [ ] **Library:** Journey 1 opens its eight source-backed chapters and 35 activities. Search for a chapter and for an existing lesson title. Selecting an activity changes the bottom tab to **Practice**. Extras (Sound Lab, scenarios) launch in Practice too; Library itself does not duplicate the exercise.
- [ ] **Practice:** Start a short guided lesson and one core lesson, record/replay, use Next/Skip, then visit Home/Library/Expedition and return. Check each lesson resumes from its own saved item, while only a genuinely submitted attempt earns XP. Force-quit/relaunch and repeat. Check scheduled review and optional previously introduced reinforcement.
- [ ] **Home:** After real attempts, recent activity displays the actual Polish phrase, activity mode and timestamp. Local today's XP/attempt counts change only for saved learning events. The Continue route chooses the next incomplete unified Journey 1 activity, not the last merely opened lesson. If an adult voluntarily connects a verified family account, family weekly XP must match the *server response*, not local personal XP.
- [ ] **Expedition:** Open the existing Poland regional map, inspect unlocked versus locked status, choose a permitted region and confirm local XP is consistent. Do not mistake family weekly XP for personal exploration XP.
- [ ] **Progress:** Inspect per-chapter attempted counts, actual answer-based matching accuracy, local practice/XP and regions. Open **Data and account** one level deeper and confirm archive/restore/account options are accessible without displacing the learning statistics or silently signing in.

## Pronunciation acceptance — real take only

- [ ] Open the Speak card for an **original source item with actual pronunciation segments** (for example, **Dzień dobry**, when available in the existing course). Hear the authentic Polish MP3 and see the original English meaning in the same exercise; no Learn/Listen/Speak mode selector is required.
- [ ] With **no family connection**, record, stop and replay locally. The word must remain ordinary unscored text, with no invented percentage/colours. The optional *Enable pronunciation checking* path must not block learning.
- [ ] For the **adult-only speech pilot**, voluntarily connect an existing verified family account to the configured HTTPS service. Nothing is uploaded merely by signing in. Record a fresh take, separately approve **Azure Speech** and **Groq Whisper**, then select *Check my pronunciation*. Do not use or paste activation credentials into a bug report.
- [ ] On a real, source-matched successful response, confirm the **original Polish word** is segmented as coloured **text** (green/orange/red/neutral hints, thin separation); **one overall experimental /100 score** is directly below. No coloured rectangles, per-segment percentages, second full word, duplicate score or explanatory colour legend. Hint colours are Whisper transcript-alignment proxies, **not calibrated syllable acoustic grades**.
- [ ] If either provider is unavailable, the response is inconclusive, the item/source mismatches or permission is refused, there must be **no numeric score or fabricated coloured feedback**. Record a new take: both permissions should reset off, and the old feedback should clear.
- [ ] Test with wired/Bluetooth/phone speaker as available. The existing DEBUG-only Home audio-channel probe tests left/right/both output; include whether the previously observed right-earphone problem recurs. Test mic recording separately from speaker/channel output.

## Report back for the next UI/UX iteration

Record **device model / iOS**, **fresh or existing learner**, and for each of the five tabs **pass/fail + first visible defect**. For pronunciation record **connected vs offline**, whether two approvals were given, **score shown yes/no**, **segments coloured yes/no**, and **record/replay + left/right earphone behaviour**. Add screenshots only of public/lesson UI, not personal credentials, identifiers, recorded audio or speech-provider payloads.

**Acceptance gate:** User physically verifies the five navigation roles, saved-position transitions and at least one real consented coloured-score result (or explicitly reports scoring service blocked). Keep PR #169 draft until recorded device findings are addressed. Do not merge to main, rework the curriculum, assert acoustic calibration, or change the production Neon/Render family service in this handoff.
