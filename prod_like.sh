#!/usr/bin/env bash
# Local production preview of the canonical V2 PWA; does not run legacy Flask.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root/v2/frontend"
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund
fi
npm run build
exec ./node_modules/.bin/vite preview --host 127.0.0.1 --port "${PTP_PREVIEW_PORT:-4186}" --strictPort
