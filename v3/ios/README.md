# Path to Polish V3 — native iPhone app

**First-run principle:** Open the app and start studying. No app login, email, phone number, registration or iCloud prompt. Native local study runs offline; no remote assessment or implicit network upload.

## Owner physical iPhone beta

The owner approved first on-device functional testing now that the offline SwiftUI experience
has passed native iPhone Simulator CI. This is **not** a production release or sign-off for
CloudKit, hosted family access, calibrated remote pronunciation, or editorial Polish accuracy.
See [the current device acceptance checklist](../IOS_DEVICE_SMOKE.md).
GitHub must pass the exact V3 branch-head build and XCTest before testing that head.

## Build with Xcode on macOS

Requires Xcode with the iOS 17+ SDK, Node.js 22+, XcodeGen (`brew install xcodegen`). From the repository root:

```bash
git switch ai/v3/swiftui-local-first
git pull --ff-only
bash v3/ios/scripts/open-ios.sh
```

Select your iPhone or simulator and run the **PathToPolish** scheme. The script regenerates **actual** `v2/frontend/public/generated/lessons.json` and reference MP3s, verifies original IDs/audio and places them under an ignored native resource folder. No generated copies are committed or authored independently. XcodeGen creates an ignored `.xcodeproj` from version-controlled `project.yml`.

Without running the preparation script, the Xcode project cannot include the current curriculum/audio; this is deliberate rather than showing dummy content.

The same script renders the approved **white-square geometric P and mint dot** icon
from the checked-in native brand geometry at `Brand/AppIcon.svg` into
`Resources/AppIcon.xcassets/AppIcon.appiconset/AppIcon.png`. The PNG is 1024×1024,
opaque RGB, with **no baked-in rounded corners**; iOS applies its own icon mask.
XcodeGen includes the `AppIcon` asset catalog, and CI checks the generated image's
format before building. The raster is generated/ignored, while the brand vector,
renderer, asset metadata and project configuration remain versioned.

To build from Terminal after preparing resources and generating the project:

```bash
xcodebuild -project v3/ios/PathToPolish.xcodeproj -scheme PathToPolish \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

## Current V3 tranche

- Real catalog-backed Home, Library, Practice, Expedition and Progress with the exact V2 21-step core journey plus five optional exploratory lessons. Home Continue and Library browsing have independent cursors.
- V2-parity Learn, Listen, Read, local Speak; original authored comprehension questions and two optional 10-number practice sections. No fake speech results or remote microphone upload.
- App Support JSON store with atomic writes and stable mode-qualified item IDs, 24h spaced review, frozen due-only sessions and anonymous profile. Records persist offline.
- Native audio playback at 0.75× / 1× and quality-gated local record/replay. The private assessment transport has no Azure/Groq keys bundled and is inaccessible without separate adult-pilot sign-in and dual per-take provider consent.
- Native interactive sixteen-voivodeship Poland map with original V2 geometry, region selection and personal XP ledger, daily deduplication and repeat taper. This ledger is **not** family leaderboard data.
- No mandatory login. Optional adult-only, voluntary existing V2 family session supports private leaderboard, regional map and explicit recent-activity sharing. Server remains group-XP authority; no automatic history upload.
- Optional source-bound Azure/Whisper pronunciation transport requires an authenticated verified adult pilot session and affirmative consent for each provider per take; real provider scoring is not enabled/certified.
- Native source-locked guided Foundations, recorded alphabet, sound lab, first-exposure Read/Listen, eight applied tourist scenarios and local tutorial-less progress flows.
- Progress can be exported to a versioned JSON file or explicitly erased on-device without affecting the private family server. A corrupt local learner file is preserved, not overwritten. JSON import/restore remains future work.
- CloudKit is still **OFF**: original aggregate counters and daily XP events need an event-journal migration and two-device conflict testing before any opt-in private sync. No live Neon/Render or family-account data is changed.

## Native CI witness

[GitHub Actions #42598104496](https://github.com/AndrewDionne/LearnPolish/actions/runs/42598104496): source/media integrity checks, iPhone Simulator BUILD SUCCEEDED, 68 native XCTest passed with zero failures (exact V3-06A code head). Documentation-only changes afterward do not imply new feature execution.

## Not yet certified

GitHub CI exercises native simulator compilation and focused XCTest suites. This is **not** proof of real iPhone microphone functionality, complete V2 content-teaching/pronunciation parity, family integration, parental compliance or CloudKit conflict handling. Keep V3 PR #169 draft until hardware observations and the separate release gates are accepted. The first owner iPhone functional-beta test is now explicitly approved once exact-head Simulator CI passes. The durable gap list is [`../BUILD_PROGRESS.md`](../BUILD_PROGRESS.md), and the PR remains draft.
