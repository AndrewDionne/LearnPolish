#!/bin/bash
# One-command build, install, launch and device-version verification.
# Requires an explicit physical iPhone ID. No uninstall or data deletion.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
DEVICE="$@"
if [[ $# -ne 1 || ! "$1" =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f-]+$ ]]; then
  echo "Usage: bash v3/ios/scripts/Install-PathToPolish-Verified.command <physical-iPhone-UDID>" >&2
  xcrun devicectl list devices || true
  exit 2
fi
DEVICE="$1"
for tool in xcodegen python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool" >&2; exit 2; }
done
if [[ ! -d "$DEVELOPER_DIR" ]]; then echo "Install full Xcode." >&2; exit 2; fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked source is modified. Commit changes before a traceable physical build." >&2
  exit 2
fi
SHA="$(git rev-parse --verify HEAD)"
VERSION="$(python3 - "$SHA" <<'PY'
import sys
value=int(sys.argv[1][:6],16)
print(f"{value//10000+1}.{value//100%100}.{value%100}")
PY
)"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
xcrun devicectl list devices --json-output "$TEMP/devices.json" >/dev/null
python3 - "$TEMP/devices.json" "$DEVICE" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1])).get("result",{}).get("devices",[])
matches=[r for r in rows if str(r.get("identifier","")).lower()==sys.argv[2].lower()]
if len(matches)!=1:
    sys.exit("Selected device is not available as one explicit physical device.")
r=matches[0]
props=r.get("hardwareProperties") or {}
name=str((r.get("deviceProperties") or {}).get("name",""))
model=str(props.get("productType",""))
if not (model.startswith("iPhone") or "iPhone" in name):
    sys.exit("Refusing a non-iPhone destination.")
PY
echo "Building Path to Polish commit $SHA for physical iPhone $DEVICE"
(cd v3/ios && xcodegen generate --spec project.yml)
DERIVED="$HOME/Library/Developer/Xcode/DerivedData/PathToPolish-Verified-Device"
LOG="$TEMP/build.log"
if ! xcodebuild -project v3/ios/PathToPolish.xcodeproj -scheme PathToPolish \
  -configuration Debug -destination "platform=iOS,id=$DEVICE" \
  -derivedDataPath "$DERIVED" -allowProvisioningUpdates \
  "APP_GIT_COMMIT=$SHA" "CURRENT_PROJECT_VERSION=$VERSION" build > "$LOG" 2>&1; then
  tail -n 90 "$LOG"; echo "Build FAILED; no installation attempted." >&2; exit 1
fi
APP="$DERIVED/Build/Products/Debug-iphoneos/PathToPolish.app"
[[ -f "$APP/Info.plist" ]] || { echo "Built app missing" >&2; exit 1; }
read_key() { /usr/libexec/PlistBuddy -c "Print :$1" "$APP/Info.plist"; }
[[ "$(read_key CFBundleIdentifier)" == "com.pathtopolish.learning" ]] || { echo "Wrong bundle ID." >&2; exit 1; }
[[ "$(read_key AppGitCommit)" == "$SHA" ]] || { echo "Git SHA not embedded; refusing install." >&2; exit 1; }
[[ "$(read_key CFBundleVersion)" == "$VERSION" ]] || { echo "Build fingerprint mismatch; refusing install." >&2; exit 1; }
xcrun devicectl device install app --device "$DEVICE" "$APP"
xcrun devicectl device info apps --device "$DEVICE" --bundle-id "com.pathtopolish.learning" \
  --json-output "$TEMP/installed.json" >/dev/null
python3 - "$TEMP/installed.json" "$VERSION" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1])).get("result",{}).get("apps",[])
matches=[a for a in rows if a.get("bundleIdentifier")=="com.pathtopolish.learning"]
if len(matches)!=1: sys.exit("INSTALL NOT VERIFIED: expected bundle missing/ambiguous.")
got=str(matches[0].get("bundleVersion",""))
if got!=sys.argv[2]:
    sys.exit(f"INSTALL NOT VERIFIED: expected version {sys.argv[2]}, device reports {got!r}.")
print("Device bundle-version fingerprint verified:",got)
PY
xcrun devicectl device process launch --device "$DEVICE" "com.pathtopolish.learning"
echo "INSTALLED-FINGERPRINT-VERIFIED $SHA build $VERSION device $DEVICE"
echo "Check Home → About → Git commit for the full $SHA before physical acceptance."
echo "Source merge, CI certification and device install remain three separate records."
