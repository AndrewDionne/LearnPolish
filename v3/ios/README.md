# Path to Polish V3 — native iPhone app

**First-run principle:** Open the app and start studying. No app login, email, phone number, registration or iCloud prompt. Native local study runs offline; no remote assessment or implicit network upload.

## Owner Xcode build deferred until complete

The owner requested continued development and no partial-version phone installs. Run GitHub native iOS compilation and automated simulator tests during development, but **do not request a local Xcode build or physical acceptance until the full agreed feature set is implemented**. The steps below are retained for final integration and release testing.

## Build with Xcode on macOS

Requires Xcode with the iOS 17+ SDK, Node.js 22+, XcodeGen (`brew install xcodegen`). From the repository root:

```bash
git switch ai/v3/swiftui-local-first
git pull --ff-only
bash v3/ios/scripts/open-ios.sh
```

Select your iPhone or simulator and run the **PathToPolish** scheme. The script regenerates **actual** `v2/frontend/public/generated/lessons.json` and reference MP3s, verifies original IDs/audio and places them under an ignored native resource folder. No generated copies are committed or authored independently. XcodeGen creates an ignored `.xcodeproj` from version-controlled `project.yml`.

Without running the preparation script, the Xcode project cannot include the current curriculum/audio; this is deliberate rather than showing dummy content.

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
- Native audio playback at 0.75× / 1× and local record/replay; no Azure/Groq credentials bundled.
- Native interactive sixteen-voivodeship Poland map with original V2 geometry, region selection and personal XP ledger, daily deduplication and repeat taper. This ledger is **not** family leaderboard data.
- No login, no CloudKit or Neon calls in this tranche. Former group identities and database are untouched.

## Not yet certified

GitHub CI exercises native simulator compilation and focused XCTest suites. This is **not** proof of real iPhone microphone functionality, complete V2 content-teaching/pronunciation parity, family integration, parental compliance or CloudKit conflict handling. Do not merge to `main` or ask owner for local Xcode testing until the full agreed feature set and integration tests are ready. The durable gap list is [`../BUILD_PROGRESS.md`](../BUILD_PROGRESS.md), and the PR remains draft.
