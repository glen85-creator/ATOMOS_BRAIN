# bridge — ATOMOS 디스패치 브리지 (M3)

> **구현 위치: FastAPI 리포** `app/services/atomos_bridge.py` + `app/tasks/atomos_tasks.py` (Celery)
> 결정 근거: 미결 #4 승인 — 감지 캐시·detection_settings·기록 테이블·Redis/beat 인프라가 전부 FastAPI(Railway)에 있음.
> 이 디렉터리는 운영 런북만 보관. S1 수동 스크립트(`~/atomic-s1-exec/*.sh`, WSL)는 참고 원형으로 유지.

## 루프 — 2층 구조 (조직 헌장 §7-1/§7-3 + 2026-06-10 enrich 전환)

> FastAPI main의 **B층**(`tasks.auto_detect_sales` 05:30, detection_tasks.py — 감지 즉시 규칙 기반
> pending 제안 생성)과의 중복 충돌이 확인되어, 브리지는 **신규 생성이 아니라 B층 행을 보강(enrich)** 한다.
> 카드 1장이 점진적으로 진화: 05:30 즉시 카드(B층) → 06:00+ AI 분석 보강(브리지).

```
[B층 05:30]  감지 → strategy_executions(proposed·pending) 즉시 생성 (canned 액션, AI 없음)
[브리지 06:00] Celery beat
  → 보강 큐 조회: B층 sales 제안 (proposed·pending·paperclip_issue_id 없음·risk=high·최근 3일)
  → gross=0 카드 스킵 (휴무/미수집 의심 — AI 분석 부적합)
  → Paperclip 이슈 생성 (본문 = evidence + 월KPI + 출력 JSON 스키마)
  → ATOMOS_HERMES un-pause + wakeup → terminal-native 분석
  → 에이전트 JSON 코멘트 폴링 회수
  → 같은 행 UPDATE: ai_recommendation 교체(B층 원본 b_layer 보존) + paperclip_issue_id 링크
  → audit_log(enrich) + agent_run(비용 추정)
  → 에이전트 재-pause (finally — 실패해도 반드시)
  → 콘솔 pending_exception 카드가 AI 분석 포함 상태로 갱신 → 사람 승인 (v1: 자동실행 없음)
```

## Railway 환경변수 (전부 신규 — 기본값은 브리지 OFF)

| 변수 | 값 | 비고 |
|---|---|---|
| `ATOMOS_BRIDGE_ENABLED` | `true`/`false` | **기본 false** — 켜기 전에 아래 전부 설정 |
| `PAPERCLIP_BASE_URL` | `http://paperclip-sab7.srv1686595.hstgr.cloud` | Traefik 경유. ⚠️ sab7 Traefik 크래시루프 이력(T10) — 외부 도달성 선확인 |
| `PAPERCLIP_ORIGIN` | (기본 BASE_URL) | boardMutationGuard trusted origin |
| `PAPERCLIP_ADMIN_EMAIL` / `PAPERCLIP_ADMIN_PASSWORD` | board 자격 | v1 한정 — 전용 계정 분리 후속 |
| `ATOMOS_COMPANY_ID` | `88adce92-…` | 기본값 코드 내장 |
| `ATOMOS_AGENT_ID` | `6d44aa65-…` (ATOMOS_HERMES) | 기본값 코드 내장 |
| ~~`ATOMOS_BRIDGE_ORG_ID` / `BR_IDS`~~ | (enrich 모드 미사용) | 스캔 범위는 B층 auto_detect_sales 소관 (operation_status=operating 전 브랜드) |
| `ATOMOS_BRIDGE_MAX_DISPATCH` | `2` | 사이클당 보강(enrich) 상한 (비용 가드) |
| `ATOMOS_BRIDGE_SKIP_ZERO_SALES` | `true` | gross=0 카드 스킵 — 휴무/미수집/영업중단 의심은 운영 확인 대상 (AI 분석 부적합) |
| `ATOMOS_BRIDGE_POLL_INTERVAL_SEC` / `ATOMOS_BRIDGE_POLL_TIMEOUT_SEC` | `20` / `600` | 코멘트 회수 폴링 |

## 가동 절차
1. M2 완료 확인 (어댑터 패치 ✓, ATOMOS_HERMES promptTemplate ✓, 모델 실측 ✓)
2. Railway 환경변수 설정 (`ATOMOS_BRIDGE_ENABLED=false` 상태로 먼저 배포)
3. 수동 1회 실행으로 검증: `celery -A app.core.celery_app call tasks.atomos_bridge_cycle`
   (worker 로그에서 summary 확인 — disabled 스킵이 정상)
4. `ATOMOS_BRIDGE_ENABLED=true` → 다음 beat 사이클부터 자동
5. 콘솔(/dashboard/atomic) pending_exception 에 제안 카드 확인

## 안전 장치 (코드 내장)
- 기본 OFF + 스캔 범위 미설정 시 스킵 (이중 안전)
- 사이클당 디스패치 상한 / dedup 멱등 (제안 중복 방지) / 열린 이슈 중복 가드 (이슈 스팸 방지)
- 에이전트 작업 후 **무조건 재-pause** (try/finally)
- Paperclip 도달 불가 시 해당 사이클 스킵 (다음 beat 재시도) — 엔진 EP·DB에는 영향 없음
