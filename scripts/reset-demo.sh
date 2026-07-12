#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
  curl -fsS -X POST http://127.0.0.1:8000/api/workflows/demo >/dev/null
  echo "Running EnterpriseOS demo reset: IDLE"
else
  (cd backend && ../.venv/bin/python manage_demo.py reset)
fi
