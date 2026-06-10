# hermes-paperclip-adapter ctx-path 패치

## 무엇을 고치나
`hermes-paperclip-adapter` v0.2.1 버그 (S1 체크포인트에서 확정):
`dist/server/execute.js`가 런타임 값(taskId 등)을 **`ctx.config?.X`(정적 adapterConfig)** 에서 읽지만,
실제 런타임 데이터는 **`ctx.X`(최상위)** 에 있다 → `{{taskId}}`·`{{taskTitle}}`·`{{taskBody}}`·`{{commentId}}`·`{{wakeReason}}` 항상 빈값.

**`{{taskId}}` 주입은 terminal-native 루프의 필수 전제** — 패치 소실 시 에이전트가 자기 이슈를 fetch하지 못해 브리지 루프 전체가 멈춘다.

## 패치 내용 (5곳)
```js
// before
cfgString(ctx.config?.taskId)
// after
cfgString(ctx.taskId ?? ctx.config?.taskId)
```
대상 키: `taskId` / `taskTitle` / `taskBody` / `commentId` / `wakeReason`

## ⚠️ 휘발성
패치는 컨테이너 **파일시스템에만** 적용된다 → 컨테이너 **재생성(recreate) 시 소실**.
(재시작(restart)은 유지). 재생성 후 반드시 `apply-ctx-path-patch.sh` 재실행.
ATOMOS_CTO daily-health 점검 항목(`adapter_patch`)이 생존 여부를 감시한다.

## 사용 (VPS 호스트에서)
```bash
./apply-ctx-path-patch.sh --check    # 현재 상태만 확인 (변경 없음)
./apply-ctx-path-patch.sh --apply    # 백업 → 패치 → 검증 (이후 docker restart 필요)
```
적용 후: `docker restart paperclip-sab7-paperclip-1` (서버가 시작 시 어댑터를 캐시하므로 필수).

## 롤백
컨테이너 내 백업 `execute.js.atomos.bak`을 원위치 복사 후 restart.

## 후속 (미결 #5)
업스트림(Nous Research) PR 제출 검토 — 다른 어댑터(claude-local 등)는 이미 최상위 ctx를 읽음.
