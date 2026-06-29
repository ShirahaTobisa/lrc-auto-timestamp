#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg python3-venv
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-local.txt

echo "Backend ready."
echo "Run:"
echo "  source .venv/bin/activate"
echo "  cd backend"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000"

