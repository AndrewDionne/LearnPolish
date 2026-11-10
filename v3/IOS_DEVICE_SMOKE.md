# V3 iPhone acceptance — first device build

**Status:** first physical test is recommended as soon as the exact-head native
Simulator CI is green. The app is functional and local-first; this is a
**functional beta / discovery test**, not a release candidate or editorial
approval. Do not wait for hosted family service, CloudKit or calibrated
remote pronunciation scores to test offline learning.

## Safe first build — isolated from the existing production checkout

From Terminal on the Mac with Xcode and Node.js installed:

```bash
cd "$HOME/MY CODE/repos/path-to-polish"
git fetch origin ai/v3/swiftui-local-first
git worktree add --detach ../path-to-polish-v3-device origin/ai/v3/swiftui-local-first
bash ../path-to-polish-v3-device/v3/ios/scripts/open-ios.sh
```

If `../path-to-polish-v3-device` already exists, **do not overwrite or
delete it**; inspect that worktree and refresh it safely first. If XcodeGen
is missing, install using `brew install xcodegen` and rerun the final
command. The launcher compiles real original V2 source + 481 bundled audio
references before generating and opening `PathToPolish.xcodeproj`.

Select **PathToPolish** scheme in Xcode, choose your **connected iPhone**
as the run destination, select your own Apple development Team in Signing &
Capabilities, enable automatic signing if prompted, then press Run.
Do not add CloudKit capabilities, backend credentials, tester accounts or
family entitlements to get this offline test working.

## Device smoke checklist

- [ ] Home screen shows the approved **white-square Path to Polish P and mint-dot**
  icon on the iPhone Home Screen; iOS rounds the square itself, with no
  pre-rounded corners or placeholder graphic
- [ ] On clean install, app opens directly to Home, with **one** primary
  Continue button showing **Yes and no**, no signup, login or iCloud prompt
- [ ] Switch to Airplane Mode: guided Polish words and full original audio
  play locally at **1×** and **0.75×**; no network needed
- [ ] Hear a word, reveal meaning, mark **Needs practice**; verify source
  count increments and review due while not inventing pronunciation feedback
- [ ] **Skip** a phrase: does **not** award XP or mark it practised; end
  of activity reports the honest `N of M` count and Revisit unpractised
- [ ] From a grammar lesson revisit an earlier prerequisite, return Home:
  primary Continue stays on the original current lesson; repeat after force-quit
- [ ] In Library, open original course lesson and Listen / Learn / Read as
  available; verify correct original phrase, translation and sound
- [ ] Speak: request microphone permission only on deliberate record,
  record/replay **locally**, check no fabricated Azure/Whisper score
- [ ] Complete a short source lesson; force-quit, relaunch, check local
  progress and daily review remained intact and accurate
- [ ] Open Practice, review a due word, confirm correct/incorrect feedback
  persists without duplicate XP and no loop in same 20-card batch
- [ ] Inspect small-screen navigation, back/skip behavior, progress tab and
  source-backed region selection for crashes, overlapping controls or latency
- [ ] Device offline first-run must not touch Neon/Render, automatically log
  in a family tester, enable CloudKit, or upload microphone audio

## Observations to return for fixing

Report the first visible defect and the screen/lesson/action that produced
it; a screenshot is useful for layout. Also note device/iOS version, whether
Airplane Mode was on, and whether the behavior persists after relaunch.
Do **not** send secrets or family tester activation files.

## Explicitly *not* yet accepted for release

- Independent Polish lexical, inflection, sound and grammar editorial approval:
  [first-use inventory](JOURNEY1_FIRST_USE.md) remains **Pending**
- Core Journey 1 + Guided Foundations full instructional integration: Home
  now supplies one Continue route, but the historical catalog has overlaps;
  original Learn records prevent copying identities or treating repetition
  as new source content. This is not a claim of certified prerequisite closure.
- Real acoustic syllable-scoring calibration, privacy/guardian approvals
- Private CloudKit entitlement, manual service acceptance, two-device
  concurrency or automatic sync; hosted family sign-in/leaderboard smoke
- Multi-device performance, battery, crash and store-distribution validation

**Exit criterion for the first device pass:** no crash, correct offline
audio/record/replay, understandable Home/Library/Practice flows, accurate
save/relaunch/review, no automatic account/cloud. Then iterate on real UI
findings; production merge remains gated independently.
