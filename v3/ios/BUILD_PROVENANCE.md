# Path to Polish — verify what is installed

```bash
xcrun devicectl list devices
bash v3/ios/scripts/Install-PathToPolish-Verified.command <physical-iPhone-UDID>
```

Run from the root of this exact PR checkout on an Apple Developer-signed Mac. It builds the native PathToPolish target with `AppGitCommit` set to the **full Git SHA** and `CFBundleVersion` set to a numeric SHA-derived fingerprint, verifies the built app, installs it on one explicitly chosen physical iPhone without uninstalling existing progress, checks installed bundleVersion through devicectl, then launches. The script fails rather than claiming physical acceptance on mismatch. In the app, **Home → About** displays the full installed SHA.

The installed version fingerprint encodes only the first six Git SHA hex characters; compare the full ID in About to the source SHA. A manual Xcode Run without an injected stamp displays UNSTAMPED and is not eligible for physical testing. GitHub merge ≠ exact-head CI certification ≠ verified device install; no server, CloudKit or family data is changed by this command.
