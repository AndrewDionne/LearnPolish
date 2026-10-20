#!/usr/bin/env bash
# Path to Polish: canonical V2 local development launcher.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root/v2/frontend"
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund
fi
exec npm run dev -- --host 127.0.0.1 --port "${PTP_DEV_PORT:-5186}" --strictPort
