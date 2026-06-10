#!/usr/bin/env bash
# hermes-paperclip-adapter ctx-path 패치 (멱등) — VPS 호스트에서 실행
# 사용: ./apply-ctx-path-patch.sh --check | --apply
set -euo pipefail

PC="${PC:-paperclip-sab7-paperclip-1}"
KEYS=(taskId taskTitle taskBody commentId wakeReason)
MODE="${1:---check}"

# execute.js 경로 탐색 (이미지 갱신으로 경로가 바뀌어도 동작)
TARGET=$(docker exec "$PC" sh -lc \
  'find / -path "*/hermes-paperclip-adapter/dist/server/execute.js" 2>/dev/null | head -1')
if [ -z "$TARGET" ]; then
  echo "ERROR: execute.js 를 찾을 수 없습니다 (컨테이너=$PC)" >&2; exit 1
fi
echo "TARGET: $TARGET"

patched=$(docker exec "$PC" sh -lc "grep -c '?? ctx.config?.' '$TARGET' || true")
unpatched=$(docker exec "$PC" sh -lc "grep -c 'cfgString(ctx\.config?\.' '$TARGET' || true")
echo "현재 상태: patched-patterns=$patched / unpatched-patterns=$unpatched"

if [ "$MODE" = "--check" ]; then
  if [ "${patched:-0}" -ge 5 ]; then echo "OK: 패치 적용됨"; exit 0
  else echo "WARN: 패치 미적용 또는 부분 적용 — --apply 필요"; exit 2; fi
fi

if [ "$MODE" != "--apply" ]; then
  echo "사용법: $0 --check | --apply" >&2; exit 1
fi

# 1) 백업 (없을 때만 — 원본 보존)
docker exec -u node "$PC" sh -lc \
  "[ -f '$TARGET.atomos.bak' ] || cp '$TARGET' '$TARGET.atomos.bak'"
echo "백업: $TARGET.atomos.bak"

# 2) 키별 치환 (이미 패치된 패턴은 매치되지 않음 → 멱등)
for KEY in "${KEYS[@]}"; do
  docker exec -u node "$PC" sh -lc \
    "sed -i 's/cfgString(ctx\.config?\.$KEY)/cfgString(ctx.$KEY ?? ctx.config?.$KEY)/g' '$TARGET'"
done

# 3) 검증
patched=$(docker exec "$PC" sh -lc "grep -c '?? ctx.config?.' '$TARGET' || true")
if [ "${patched:-0}" -lt 5 ]; then
  echo "ERROR: 패치 검증 실패 (patched=$patched < 5). 수동 확인 필요." >&2; exit 1
fi
echo "패치 완료 (patched-patterns=$patched)."
echo "⚠️ 어댑터는 서버 시작 시 캐시됩니다 — 반드시 실행: docker restart $PC"
