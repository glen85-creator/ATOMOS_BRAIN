#!/usr/bin/env bash
# Phase 1 — Phase A 러너: 지식 시드 + 로컬 MCP 스모크 (VPS 불필요).
# 전제: 마이그레이션 007 적용 완료(atomos_knowledge / atomos_mcp_call_log / atomos_knowledge_search).
#       ~/FastAPI/.env 에 SUPABASE_URL / SUPABASE_SERVICE_KEY. ~/FastAPI/venv 존재.
# 사용: bash ~/ATOMOS_BRAIN/scripts/phase1_phase_a.sh
# 주의: 이 러너는 Phase A(007만, BRAIN 008/009 적용 前)용. main 체크아웃의 seed/smoke(원본)를 사용.
set -euo pipefail

FASTAPI=/home/glen_85/FastAPI
BRAIN=/home/glen_85/ATOMOS_BRAIN

cd "$FASTAPI"
# .env 의 SUPABASE_* 등을 환경으로 export (uvicorn·smoke 가 상속)
set -a; source "$FASTAPI/.env"; set +a

# MCP 토큰/시크릿: .env 에 없으면 Phase A 용 임시 생성(엔진·스모크가 같은 값 공유해야 함)
export ATOMOS_MCP_TOKEN="${ATOMOS_MCP_TOKEN:-phaseA-smoke-token}"
export ATOMOS_MCP_SESSION_SECRET="${ATOMOS_MCP_SESSION_SECRET:-$("$FASTAPI/venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')}"

echo "=== [1/3] 지식 시드 (atomos_knowledge) ==="
"$FASTAPI/venv/bin/python" "$BRAIN/scripts/seed_atomos_knowledge.py"

echo "=== [2/3] 로컬 엔진 기동 (uvicorn main:app :8099) ==="
"$FASTAPI/venv/bin/uvicorn" main:app --port 8099 --log-level warning &
UVPID=$!
trap 'kill "$UVPID" 2>/dev/null || true' EXIT
sleep 6

echo "=== [3/3] MCP 스모크 (무인증 401 + scope 지식조회 + call_log) ==="
"$FASTAPI/venv/bin/python" "$BRAIN/scripts/phase1_mcp_smoke.py"

echo
echo "=== Phase A 끝 — 위 출력에 'SMOKE PASS' 가 있으면 MCP 경계 검증 완료 ==="
echo "    (러너 set -e 는 스모크의 논리 실패를 못 잡을 수 있음 — PASS 문자열 직접 확인)"
