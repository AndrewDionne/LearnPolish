#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
command -v node >/dev/null || { echo "Install Node.js 22+" >&2; exit 1; }
command -v xcodegen >/dev/null || { echo "Install XcodeGen: brew install xcodegen" >&2; exit 1; }
node "$SCRIPT_DIR/prepare-assets.mjs"
cd "$IOS_DIR"
xcodegen generate --spec project.yml
open PathToPolish.xcodeproj
