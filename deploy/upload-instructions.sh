#!/usr/bin/env bash
# M2 — org/agents/<SLOT>/{SOUL,AGENTS,TOOLS,HEARTBEAT}.md 를 VPS 에이전트 instructions 로 배포
# VPS 호스트에서 실행. 리포 정본 → VPS 단방향 (조직 헌장 §4-1)
# 사전조건: fetch-vps-bundles.sh 로 현행 백업 확보
set -euo pipefail
cd "$(dirname "$0")"
source ./uuid-map.env

PC="${PC:-paperclip-sab7-paperclip-1}"
BASE="/paperclip/instances/default/companies/$COMPANY_ID/agents"
SRC="../org/agents"
TS=$(date +%Y%m%d-%H%M%S)

declare -A SLOTS=(
  [ATOMOS_CEO]=$ATOMOS_CEO [ATOMOS_CTO]=$ATOMOS_CTO [ATOMOS_HERMES]=$ATOMOS_HERMES
  [ATOMOS_ANALYST]=$ATOMOS_ANALYST [ATOMOS_MARKETING]=$ATOMOS_MARKETING
  [ATOMOS_RESEARCHER]=$ATOMOS_RESEARCHER
)

for SLOT in "${!SLOTS[@]}"; do
  UUID="${SLOTS[$SLOT]}"
  DIR="$BASE/$UUID/instructions"
  if [ ! -d "$SRC/$SLOT" ]; then echo "SKIP: $SRC/$SLOT 없음" >&2; continue; fi

  # 컨테이너 내 백업 (instructions.bak-<ts>)
  docker exec -u node "$PC" sh -lc \
    "[ -d '$DIR' ] && cp -r '$DIR' '$DIR.bak-$TS' || mkdir -p '$DIR'"

  for F in SOUL.md AGENTS.md TOOLS.md HEARTBEAT.md; do
    [ -f "$SRC/$SLOT/$F" ] && docker cp "$SRC/$SLOT/$F" "$PC:$DIR/$F"
  done
  docker exec "$PC" sh -lc "chown -R node:node '$DIR'" 2>/dev/null || true
  echo "uploaded: $SLOT → $DIR (백업: instructions.bak-$TS)"
done

echo
echo "완료. 에이전트는 다음 wake 시 새 instructions 를 읽습니다 (서버 재시작 불필요)."
