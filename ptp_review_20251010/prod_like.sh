#!/usr/bin/env bash
set -euo pipefail

if [[ -f "venv/bin/activate" ]]; then
  source venv/bin/activate
fi

export FRONTEND_BASE_URL="https://andrewdionne.github.io/LearnPolish"
export FLASK_APP=run.py

python -m flask run
