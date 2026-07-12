#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
command -v node >/dev/null || { echo "Node.js is required"; exit 1; }
command -v npm >/dev/null || { echo "npm is required"; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required"; exit 1; }
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
npm install
mkdir -p outputs/artifacts
echo "EnterpriseOS setup complete. No credentials are required for DEMO mode."
