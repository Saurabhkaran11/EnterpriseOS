#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -x .venv/bin/python ] || [ ! -d node_modules ]; then "$ROOT/scripts/setup.sh"; fi
export ENTERPRISEOS_MODE="${ENTERPRISEOS_MODE:-DEMO}"
BACKEND_PID=""
cleanup() { if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi; }
trap cleanup EXIT INT TERM
(cd backend && ../.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!
echo "EnterpriseOS ${ENTERPRISEOS_MODE} mode"
echo "Dashboard: http://localhost:3000"
echo "API:       http://localhost:8000"
npm run dev
