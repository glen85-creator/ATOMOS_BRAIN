#!/usr/bin/env bash
# M4 — ATOMOS_ANALYST 승격: 모델 Claude Sonnet 4.6 + 월예산 $10 PATCH (로스터 §3-2 승격값)
# status 는 paused 유지 — wake 는 issue-driven (브리지/수동 wakeup 이 깨움, 작업 후 재-pause)
# VPS 호스트에서 실행. 기본 dry-run — 실제 적용은 --apply
# 사전조건: ① sync-roster.sh --apply 완료 (hermes_local 전환) ② Sonnet 슬러그 hermes chat 실측 (README ⑤)
set -euo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env

PC="${PC:-paperclip-sab7-paperclip-1}"
MODE="${1:---dry-run}"
PAYLOAD="payloads/promote/ATOMOS_ANALYST.json"

[ -f "$PAYLOAD" ] || { echo "ERROR: $PAYLOAD 없음" >&2; exit 1; }

if [ "$MODE" = "--apply" ]; then
  CODE=$(docker exec -u node "$PC" bash -lc '
    curl -s -c /tmp/pc.cookies -o /dev/null -w "%{http_code}" \
      -X POST http://localhost:3100/api/auth/sign-in/email \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"')
  [ "$CODE" = "200" ] || { echo "ERROR: board 로그인 실패 (HTTP $CODE)" >&2; exit 1; }
  echo "board 로그인 OK"

  RESP=$(docker exec -i -u node "$PC" bash -lc \
    "curl -s -b /tmp/pc.cookies -X PATCH 'http://localhost:3100/api/agents/$ATOMOS_ANALYST' \
      -H 'Content-Type: application/json' -H 'Origin: http://localhost:3100' \
      --data-binary @-" < "$PAYLOAD")
  echo "APPLIED: ATOMOS_ANALYST ($ATOMOS_ANALYST)"
  echo "  → $(echo "$RESP" | head -c 300)"
  echo
  echo "다음: 일감 연결 — Railway ATOMOS_AGENT_ID=$ATOMOS_ANALYST (브리지가 sales 이슈를 ANALYST 에 배정)"
else
  echo "DRY-RUN: ATOMOS_ANALYST ($ATOMOS_ANALYST) ← $PAYLOAD"
  sed 's/^/    /' "$PAYLOAD"
  echo
  echo "실제 적용: ./promote-analyst.sh --apply"
fi
