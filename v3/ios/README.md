# Path to Polish V3 — native iPhone app

**First-run principle:** Open the app and start studying. No app login, email, phone number, registration or iCloud prompt. Native local study runs offline; no remote assessment or implicit network upload.

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

- Real catalog-backed home, library and lesson playback; first lesson selected from V2 ordered curriculum.
- Native Learn, Listen, Read, Speak; no fake speech results or remote microphone upload.
- App Support JSON store with atomic writes and stable `lesson:item:mode` identities; independent Learn/Listen/Read/Speak progress.
- Native audio playback and local record/replay. No Azure/Groq credentials bundled.
- No login, no CloudKit or Neon calls in this tranche. Former group identities and database are untouched.

## Not yet certified

A GitHub commit is not proof of Xcode compilation, iPhone microphone functionality, parental compliance, CloudKit conflict handling, or V2 scoring/XP parity. Complete simulator compile, physical testing and longitudinal learner parity before merging to `main`. These are tracked in `../DECISIONS.md` and the draft PR.
