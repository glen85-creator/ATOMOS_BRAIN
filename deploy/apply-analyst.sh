#!/usr/bin/env bash
# E층 Track A — ANALYST 슬롯만 타깃 활성화 PATCH
# (sync-roster.sh 는 6슬롯 전체 적용 + HERMES KEEP-EXISTING 에서 abort 하므로, 단일 슬롯만 안전 적용)
# VPS 호스트에서 실행. 사전: git pull (payloads/ATOMOS_ANALYST.json 최신 — hermes_local·deepseek·budget 1000·promptTemplate)
set -euo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env

PC="${PC:-paperclip-sab7-paperclip-1}"
PAYLOAD="payloads/ATOMOS_ANALYST.json"
[ -f "$PAYLOAD" ] || { echo "ERROR: $PAYLOAD 없음 (git pull 했나요?)"; exit 1; }
grep -q "KEEP-EXISTING" "$PAYLOAD" && { echo "BLOCK: $PAYLOAD 에 KEEP-EXISTING 잔존"; exit 1; }

echo "== 1) board 로그인 =="
CODE=$(docker exec -u node "$PC" bash -lc 'curl -s -c /tmp/pc.cookies -o /dev/null -w "%{http_code}" -X POST http://localhost:3100/api/auth/sign-in/email -H "Content-Type: application/json" -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"')
[ "$CODE" = "200" ] || { echo "ERROR: board 로그인 실패 (HTTP $CODE)"; exit 1; }
echo "   로그인 OK"

echo "== 2) ANALYST PATCH ($ATOMOS_ANALYST) =="
RESP=$(docker exec -i -u node "$PC" bash -lc "curl -s -b /tmp/pc.cookies -X PATCH 'http://localhost:3100/api/agents/$ATOMOS_ANALYST' -H 'Content-Type: application/json' -H 'Origin: http://localhost:3100' --data-binary @-" < "$PAYLOAD")
echo "   응답: $(echo "$RESP" | head -c 500)"

echo "== 3) 검증 (adapter/model/budget/promptTemplate) =="
docker exec -u node "$PC" bash -lc "curl -s -b /tmp/pc.cookies http://localhost:3100/api/companies/$COMPANY_ID/agents" \
  | python3 -c "import json,sys; ags=json.load(sys.stdin); ags=ags if isinstance(ags,list) else ags.get('agents',[]); a=[x for x in ags if x.get('id')=='$ATOMOS_ANALYST'][0]; ac=a.get('adapterConfig',{}); print('   adapter=%s model=%s budget=%s promptTemplate=%s' % (a.get('adapterType'), ac.get('model'), a.get('budgetMonthlyCents'), bool(ac.get('promptTemplate'))))"

echo "== done. 기대: adapter=hermes_local model=deepseek/deepseek-v4-flash budget=1000 promptTemplate=True =="
