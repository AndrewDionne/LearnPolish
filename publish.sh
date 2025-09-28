#!/usr/bin/env bash
# publish.sh  (run from the repo root)
set -euo pipefail

# activate venv if present
if [[ -d "venv" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# pull latest
git pull --rebase

# rebuild static pages + catalogs
python rebuild_all.py

# make sure GitHub Pages doesn’t run Jekyll
touch docs/.nojekyll

# commit & push docs
git add -A docs
if git diff --cached --quiet; then
  echo "Nothing to commit."
else
  git commit -m "Rebuild site: $(date -u +'%Y-%m-%d %H:%M:%S') UTC"
  git push
fi

echo "Published."
