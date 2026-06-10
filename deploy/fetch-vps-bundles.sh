#!/usr/bin/env bash
# M1 회수/대조 — VPS instructions 번들 + 에이전트 설정 스냅샷을 ./_fetched/ 로 회수
# VPS 호스트에서 실행 (또는 WSL에서: ssh paperclip-host 'bash -s' < fetch-vps-bundles.sh 후 scp)
set -euo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env

PC="${PC:-paperclip-sab7-paperclip-1}"
BASE="/paperclip/instances/default/companies/$COMPANY_ID/agents"
OUT="./_fetched"
mkdir -p "$OUT"

declare -A SLOTS=(
  [ATOMOS_CEO]=$ATOMOS_CEO [ATOMOS_CTO]=$ATOMOS_CTO [ATOMOS_HERMES]=$ATOMOS_HERMES
  [ATOMOS_ANALYST]=$ATOMOS_ANALYST [ATOMOS_MARKETING]=$ATOMOS_MARKETING
  [ATOMOS_RESEARCHER]=$ATOMOS_RESEARCHER
)

# 1) instructions 번들 회수
for SLOT in "${!SLOTS[@]}"; do
  UUID="${SLOTS[$SLOT]}"
  mkdir -p "$OUT/$SLOT"
  if docker exec "$PC" sh -lc "[ -d '$BASE/$UUID/instructions' ]"; then
    docker cp "$PC:$BASE/$UUID/instructions" "$OUT/$SLOT/"
    echo "fetched: $SLOT ($UUID)"
  else
    echo "WARN: $SLOT instructions 없음 ($UUID)" >&2
  fi
done

# 2) 에이전트 설정 스냅샷 (adapterConfig·promptTemplate·status·예산 — sync 전 필수 확보)
docker exec -u node "$PC" bash -lc '
  curl -s -c /tmp/pc.cookies -X POST http://localhost:3100/api/auth/sign-in/email \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" >/dev/null
  curl -s -b /tmp/pc.cookies http://localhost:3100/api/companies/'"$COMPANY_ID"'/agents
' > "$OUT/agents-snapshot.json"
echo "snapshot: $OUT/agents-snapshot.json ($(wc -c < "$OUT/agents-snapshot.json") bytes)"

echo
echo "다음 단계: _fetched/ 를 ATOMOS_BRAIN 리포에 가져와 org/agents/ 정본과 diff 대조 (M1)"
echo "⚠️ agents-snapshot.json 에 시크릿은 없지만 내부 식별자 포함 — 리포 커밋 시 검토"
