#!/usr/bin/env bash
set -euo pipefail

# Auto-activate venv if present
if [[ -f "venv/bin/activate" ]]; then
  source venv/bin/activate
fi

export FRONTEND_BASE_URL="http://localhost:5000"
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Use python -m to avoid PATH issues
python -m flask run
