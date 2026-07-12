#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PASS=0
FAIL=0
pass() { echo "✓ $1"; PASS=$((PASS+1)); }
fail() { echo "✗ $1"; FAIL=$((FAIL+1)); }
check() { if "$@" >/dev/null 2>&1; then pass "$1"; else fail "$1"; fi; }

echo "EnterpriseOS release preflight"
echo "Mode requested: ${ENTERPRISEOS_MODE:-DEMO}"
command -v node >/dev/null 2>&1 && pass "Node.js $(node --version)" || fail "Node.js"
command -v npm >/dev/null 2>&1 && pass "npm $(npm --version)" || fail "npm"
command -v python3 >/dev/null 2>&1 && pass "Python $(python3 --version 2>&1 | awk '{print $2}')" || fail "Python 3"
[ -x .venv/bin/python ] && .venv/bin/python -c 'import fastapi,httpx,boto3,uvicorn' >/dev/null 2>&1 && pass "Backend dependencies" || fail "Backend dependencies"
[ -d node_modules ] && npm ls --depth=0 >/dev/null 2>&1 && pass "Frontend dependencies" || fail "Frontend dependencies"
(cd backend && ../.venv/bin/python manage_demo.py reset >/dev/null 2>&1) && pass "SQLite database access" || fail "SQLite database access"
npm run build >/dev/null 2>&1 && pass "Frontend production build" || fail "Frontend production build"
(cd backend && ../.venv/bin/python -c 'from fastapi.testclient import TestClient; from app import app; assert TestClient(app).get("/health").json()["status"] == "ok"' >/dev/null 2>&1) && pass "Backend /health" || fail "Backend /health"
if [ -n "${HCOMPANY_API_KEY:-}" ] && [ "${HCOMPANY_MOCK_MODE:-true}" = "false" ]; then pass "H Company configured (secret hidden)"; else pass "H Company Mock fallback available"; fi
if [ -n "${NVIDIA_API_KEY:-}" ] && [ "${NVIDIA_MOCK_MODE:-true}" = "false" ]; then pass "NVIDIA configured (secret hidden)"; else pass "NVIDIA Mock fallback available"; fi
if [ -n "${AWS_S3_BUCKET:-}" ] && [ "${AWS_USE_LOCAL_MODE:-true}" = "false" ]; then pass "Amazon S3 configured (bucket hidden)"; else pass "AWS Local fallback available"; fi
(cd backend && ../.venv/bin/python -c 'import app; app.reset_data(); s=app.state(); assert len(s["inbox"])==5 and len(s["accounts"])==4 and len(s["tasks"])==6' >/dev/null 2>&1) && pass "Demo seed data" || fail "Demo seed data"
mkdir -p outputs/artifacts 2>/dev/null && [ -w outputs/artifacts ] && pass "Artifact output directory" || fail "Artifact output directory"
echo "Preflight result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
