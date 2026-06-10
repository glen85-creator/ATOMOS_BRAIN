#!/usr/bin/env bash
# M2 — payloads/<SLOT>.json 을 Paperclip 에이전트에 PATCH (로스터 정합)
# VPS 호스트에서 실행. 기본 dry-run — 실제 적용은 --apply
# 사전조건: fetch-vps-bundles.sh 실행 (특히 ATOMOS_HERMES promptTemplate 확보 — README 참조)
set -euo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env

PC="${PC:-paperclip-sab7-paperclip-1}"
MODE="${1:---dry-run}"

declare -A SLOTS=(
  [ATOMOS_CEO]=$ATOMOS_CEO [ATOMOS_CTO]=$ATOMOS_CTO [ATOMOS_HERMES]=$ATOMOS_HERMES
  [ATOMOS_ANALYST]=$ATOMOS_ANALYST [ATOMOS_MARKETING]=$ATOMOS_MARKETING
  [ATOMOS_RESEARCHER]=$ATOMOS_RESEARCHER
)

# board 로그인 (세션 쿠키 → 컨테이너 /tmp)
login() {
  docker exec -u node "$PC" bash -lc '
    curl -s -c /tmp/pc.cookies -o /dev/null -w "%{http_code}" \
      -X POST http://localhost:3100/api/auth/sign-in/email \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"'
}

if [ "$MODE" = "--apply" ]; then
  CODE=$(login)
  [ "$CODE" = "200" ] || { echo "ERROR: board 로그인 실패 (HTTP $CODE)" >&2; exit 1; }
  echo "board 로그인 OK"
fi

for SLOT in "${!SLOTS[@]}"; do
  UUID="${SLOTS[$SLOT]}"
  PAYLOAD="payloads/$SLOT.json"
  [ -f "$PAYLOAD" ] || { echo "SKIP: $PAYLOAD 없음"; continue; }

  # 안전 가드: 플레이스홀더 잔존 시 적용 거부
  if grep -q "KEEP-EXISTING" "$PAYLOAD"; then
    echo "BLOCK: $SLOT — payload 에 <KEEP-EXISTING> 플레이스홀더가 남아있습니다." >&2
    echo "       fetch 결과(agents-snapshot.json)에서 현행 값을 채운 뒤 재실행하세요." >&2
    [ "$MODE" = "--apply" ] && exit 1 || continue
  fi

  if [ "$MODE" = "--apply" ]; then
    RESP=$(docker exec -i -u node "$PC" bash -lc \
      "curl -s -b /tmp/pc.cookies -X PATCH 'http://localhost:3100/api/agents/$UUID' \
        -H 'Content-Type: application/json' -H 'Origin: http://localhost:3100' \
        --data-binary @-" < "$PAYLOAD")
    echo "APPLIED: $SLOT ($UUID)"
    echo "  → $(echo "$RESP" | head -c 300)"
  else
    echo "DRY-RUN: $SLOT ($UUID) ← $PAYLOAD"
    sed 's/^/    /' "$PAYLOAD"
  fi
done

[ "$MODE" = "--apply" ] || echo $'\n실제 적용: ./sync-roster.sh --apply'
