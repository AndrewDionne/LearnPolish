#!/usr/bin/env bash
# Canonical Path to Polish publishing is automated by GitHub Actions after green
# V2 CI on main; never rebuild/commit/push V1 docs from this script.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root/v2/frontend"
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund
fi
npm run check
cat <<'MESSAGE'

Local V2 checks/build passed.
To publish, commit your changes via a PR and merge to GitHub main.
After V2 checks pass on main, .github/workflows/deploy-v2-pages.yml
publishes v2/frontend/dist directly to GitHub Pages.

One-time repository setting: Settings > Pages > Build and deployment >
Source: GitHub Actions. This local command does not publish or alter Git.
Legacy docs/ files are retained only as migration/reference inputs.
MESSAGE
