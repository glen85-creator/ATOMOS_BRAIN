# deploy — 리포 정본 → VPS(Paperclip) 배포 런북

> 이 디렉터리의 스크립트는 **VPS 호스트(paperclip-host)에서 실행**한다.
> (WSL에서: `scp -r deploy/ org/ paperclip-host:~/atomos-brain/` 후 ssh 접속 실행)
> 원격 실행 환경(Claude 클라우드 세션)에서는 VPS 네트워크가 차단되어 실행 불가 — 사람이 실행.

## 실행 순서 (M1 → M2)

### ① M1 — 회수/대조 (읽기 전용)
```bash
./fetch-vps-bundles.sh
```
- 각 에이전트 `instructions/` → `_fetched/<SLOT>/`
- 에이전트 설정 스냅샷 → `_fetched/agents-snapshot.json` (adapterConfig·promptTemplate·status)
- **대조**: `_fetched/`와 `org/agents/` 정본을 diff → 정본에 누락된 유효 내용이 있으면 정본에 반영 후 커밋

### ② M2-a — instructions 배포
```bash
./upload-instructions.sh
```
- `org/agents/<SLOT>/{SOUL,AGENTS,TOOLS,HEARTBEAT}.md` → 컨테이너 instructions/
- 컨테이너 내 자동 백업(`instructions.bak-<ts>`) 후 덮어씀. 서버 재시작 불필요

### ③ M2-b — 로스터 PATCH (어댑터/모델/예산/상태)
```bash
# 1. ATOMOS_HERMES promptTemplate 채우기 (필수!)
#    agents-snapshot.json 에서 현행 promptTemplate 값을 payloads/ATOMOS_HERMES.json 에 복사
#    (PATCH adapterConfig 가 merge 인지 replace 인지 미확인 → replace 가정하고 전체 필드 동봉)
# 2. 검토
./sync-roster.sh            # dry-run (기본)
# 3. 적용
./sync-roster.sh --apply
```
- codex_local 3슬롯(ANALYST/MARKETING/RESEARCHER) → hermes_local 전환 포함 (미결 #3 승인분)
- **전 슬롯 status=paused 유지** — 활성화는 브리지/승격 게이트가 관리. 이 스크립트는 절대 un-pause 하지 않는다

### ④ M2-c — 어댑터 패치 영구화
```bash
../patches/hermes-paperclip-adapter/apply-ctx-path-patch.sh --check
../patches/hermes-paperclip-adapter/apply-ctx-path-patch.sh --apply   # 필요 시
docker restart paperclip-sab7-paperclip-1
```

### ⑤ 검증
```bash
# 두뇌 생존 (활성화 예정 모델별 1회 — 신규 슬러그는 특히 필수)
docker exec -u node paperclip-sab7-paperclip-1 \
  /paperclip/.local/bin/hermes chat -q "ping" -Q --provider openrouter
# 패치 생존
../patches/hermes-paperclip-adapter/apply-ctx-path-patch.sh --check
# 로스터 상태
# (fetch-vps-bundles.sh 재실행 → agents-snapshot.json 에서 adapterType/model/status 확인)
```

## 안전 규칙
- **un-pause 금지** — 모든 활성화는 브리지(on-demand) 또는 사람의 명시 결정
- payload 에 `<KEEP-EXISTING>` 플레이스홀더가 남아 있으면 sync-roster.sh 가 적용을 차단
- 시크릿(ADMIN_PASSWORD 등)은 컨테이너 env 에서만 참조 — 이 리포에 값 저장 금지
- 모델 슬러그 변경 후 un-pause 전 반드시 ⑤의 hermes chat 실측 (잘못된 슬러그 = 런 실패 누적)

## 인증 메모
- board 로그인: 컨테이너 env `ADMIN_EMAIL`/`ADMIN_PASSWORD` (better-auth)
- **mutation(POST/PATCH/DELETE)은 `Origin: http://localhost:3100` 헤더 필수** (boardMutationGuard)
- `disableSignUp=true` — 신규 board 계정 생성 불가. 브리지용 전용 계정 분리는 후속 검토(미결 #4 잔여)
