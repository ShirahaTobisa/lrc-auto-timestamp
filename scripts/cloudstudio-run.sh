#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
FRONTEND_PORT="${PORT:-5173}"

if command -v apt-get >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg python3-venv
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.lrc-backend-installed" ]; then
  python -m pip install --upgrade pip
  python -m pip install -r backend/requirements-local.txt
  touch .venv/.lrc-backend-installed
fi

if [ ! -d "frontend/node_modules" ]; then
  (cd frontend && npm install)
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

(cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID="$!"

cd frontend
npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
