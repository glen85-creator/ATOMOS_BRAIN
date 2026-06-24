# ATOMOS Phase 2 — 매출 수직 슬라이스 설계 (전략 A)

> 상태: **설계 승인** — writing-plans 대기.
> 작성: 2026-06-25. 부모 설계: `2026-06-20-pipeline-redesign-design.md`(코어 설계 완성)의 §10 Phase 2 구현 슬라이스.
> 전략: **A — 얇은 end-to-end 신경로**(플래그 뒤). 옛 CEO/슬롯/Paperclip 스택은 손대지 않음(제거는 Phase 3).

## 0. 목적 / 합격선
- **목적**: 매출 이상 **1건**이 **CEO·슬롯·Paperclip 없이** 6단계(감지→분석→승인→실행→측정→보고게이트)를 **새 단일역할 경로**로 관통함을 입증.
- **합격선(e2e)**: 실 매출 안건 1건이 플래그 ON 상태에서 — 감지 evidence(sigma·n·dow·confidence 보존)→Hermes 단일역할 분석(팬아웃 0)+검증게이트 통과→도구액션 승인→안전도구 레지스트리 실행(record_decision·create_task)→측정(before/after)→보고 신뢰게이트 통과 draft — 까지 도달. 옛 경로(플래그 OFF)는 동작 불변.
- 이 슬라이스는 **CEO 없는 새 모델 전체를 가장 얇게 1회 관통**하는 것이 목표다. 깊이(타 도메인·외부발송·측정 고도화)는 후속.

## 1. 현 코드 실태 (origin/main 전수 매핑, 2026-06-24 ca4d287)
6단계 설계 대비 "절반 골격, 절반 미구현". 핵심: **새 Hermes 경로는 이미 빌드돼 있으나 `ELAYER_HERMES_DIAGNOSE_ENABLED=False`로 꺼져 있고, 라이브는 §7 제거대상(Paperclip 팬아웃+CEO 게이트/합성/트리아지+600초 폴링)으로 돈다.**

| 단계 | 상태 | 요지 (앵커) |
|---|---|---|
| ① 감지 | 부분 | 통계 코어 견고·우리 것 (`2026-06-10-sales-anomaly-rpc.sql:13-110` robust-z·MAD·defect-day·confidence). 안건 영속 시 sigma/n/dow/confidence 드롭(`detection_tasks.py:18-58`), confidence=0.7 하드코딩(`:38·:71`), `atomos_bridge.py:155-165` None 하드코딩. L1 게이트·L4 라벨 없음 |
| ② 분석 | 부분 | Hermes 경로·7필드 스키마·검증게이트(lite)·재시도 실재하나 **기본 OFF** (`hermes_runner.py:138-167`, `hermes_prompt.py:6-18` _SCHEMA, `analysis_gate.py:22-61`, `config.py:58`). MCP 도구 2개뿐(`server.py:26-38`) |
| ③ 승인 | 부분 | 승인/반려/감사 게이트 강함(`strategy.py:937·753·701·64-94`). 단 승인 단위가 슬롯(`ApproveIn` selected_kinds, `:380-393`). FE 클릭이 전이 없이 invalidate만(`AtomicConsole.tsx:147`) |
| ④ 실행 | **없음** | §3d 레지스트리(executor) 0건(grep 확인). 현 실행=Paperclip 팬아웃(`elayer_dispatch.py:113-217·240-327`) = §7 제거대상 |
| ⑤ 측정 | 부분 | before→after 골격 있음(`atomic_engine.py:625-700·707-815` comparison_data·verdict). 진단품질·적시성 지표 없음, 단순 월 delta |
| ⑥ 보고 | 부분 | 발송 동작(`elayer_send.py:11-72`, `strategy.py:611-651`). 신뢰게이트 없음(substance/grounding/schema 0건), `_fallback` 무검증 발송, 수신자 SANDBOX 하드코딩 |

> **감지 데이터 신뢰성**: 이상치 감지 통계 자체는 우리 RPC 산물이며 견고하다. "옛 개념(고칠 것)"은 그 뒤의 CEO/슬롯 오케스트레이션 + evidence 충실도 버그(0.7 하드코딩·필드 드롭)이지, 감지 수치가 아니다.

## 2. 슬라이스 범위 (S0–S7)

### S0 · 라우팅 / 플래그 / 공존
- 신규 플래그 `ELAYER_PIPELINE_V2_SALES_ENABLED`(기본 OFF). ON이면 sales 도메인 execution을 **v2 단일경로**로 라우팅(CEO 게이트/트리아지/팬아웃/합성 전부 스킵). OFF면 기존 경로 그대로 → **무중립 배포**.
- 결정성 위해 수동 트리거 EP `POST /api/strategy/executions/{id}/run-v2` — 한 건을 v2로 동기 관통(테스트·시연용). 멱등(이미 v2 처리된 건 재실행 가드).
- env 재사용: `HERMES_VPS_*`·`ATOMOS_MCP_*`(이미 Railway 설정됨). 신규 env 없음(플래그 1개만).
- **옛 dispatch/CEO 코드 미삭제**(공존). 제거는 Phase 3.

### S1 · 감지 evidence 충실도 (최소)
- `build_sales_proposal_record`(`detection_tasks.py:18-58`) evidence에 RPC 산출 `sigma·n·dow·confidence`(+`below_baseline_pct`) **보존**.
- `confidence=0.7` 하드코딩(`:38·:71`) → **RPC 산출 confidence 기반 값으로 교체**(RPC 라벨 보존 + 하드코딩 제거; 구체 산식은 plan에서). 0.7 고정 금지.
- v2 경로는 안건 evidence를 **직접** Hermes 프롬프트로 빌드 — `atomos_bridge.execution_to_alert`/`build_issue_body`는 Paperclip 전용이므로 **우회**한다. 그 None 하드코딩(`:155-165`)은 옛 경로 산물로 **Phase 3 제거 대상**이며 이 슬라이스에선 손대지 않는다. 즉 evidence 작업은 (a) `build_sales_proposal_record`가 전 필드를 영속하고 (b) v2가 그 필드를 그대로 프롬프트에 싣는 것, 두 가지로 한정.
- **범위 한정**: sales 도메인만. L1 신선도 게이트·미신뢰 별도트랙·L4 정확도 라벨·cost/cogs/review evidence는 후속(Phase 2 후속/Phase 4).

### S2 · 분석 = 단일역할 Hermes + 검증게이트
- 엔진→`run_hermes_analysis`(`hermes_runner.py:138-167`) **직호출**, role/domain 파라미터화(현 ANALYST/sales 하드코딩 → 인자). 팬아웃·CEO 게이트 없음.
- 출력 = 기존 `_SCHEMA`(진단+제안액션[title·what·how·owner·eta·tool_tag·expected_effect]+confidence+risk).
- 검증게이트 = 기존 `validate_analysis`(`analysis_gate.py:22-61`): ①스키마·③그라운딩(evidence 수치 인용)·재시도(총3회)·실패→AnalysisFailed 표면화 사용 + **⑤trivial거부 강화**(무실질/일반론 판별 룰; 현 `len≥20`만).
- **fast-follow로 분리**(이 슬라이스 미포함): ②수치 재계산 정합·④환각 실값대조(call_log 실반환값 vs 인용수치). 사유 = 슬라이스를 얇게 유지.
- MCP: 기존 2도구(`knowledge_search`·`data_sales_history`)로 분석 충분. `context.*`(weather/trade_area/calendar)·`data.store_profile` 확장은 후속.

### S3 · 승인 = 도구 액션 단위
- 분석 제안액션 각각의 `tool_tag`를 승인 대상으로 노출.
- `ApproveIn`(`strategy.py:380-393`)에 신규 필드 `selected_actions`(제안액션 식별자 리스트 — `proposed_actions` 배열의 index/id; 각 항목이 자신의 `tool_tag` 보유) 추가. **기존 `selected_kinds`와 공존**(v2만 신규 필드 사용; 옛 경로 불변).
- 승인 게이트·감사(`_write_audit` `:64-94`)·진단중 409 가드 재사용.

### S4 · 실행 = 안전도구 레지스트리 (신축, 2도구)
- 신규 모듈 `app/services/safe_tools.py`: 도구 = `{id, params 스키마, 안전속성(가역·멱등·스코프), executor}` 레지스트리 + dispatch 함수(`run_tool(tool_tag, params, ctx)`).
- **1차 2도구**:
  - `record_decision(verdict, note, scope)` — 결정·노트 DB 기록.
  - `create_task(owner, action, due)` — 후속 액션 태스크 DB 기록.
  - 둘 다 **내부 DB write·가역·멱등(멱등키)·스코프(매장 한정)·외부발송 0** → 디퍼드 보안(실발송 인증) 미저촉.
  - 저장은 **기존 감사/결정 인프라 재사용 우선**(record_decision→`_write_audit` 계열 결정 기록 / create_task→태스크 저장소). 신규 테이블은 최소화하고 구체 스키마는 plan에서 확정.
- 승인된 액션 `tool_tag`→executor 실행, 멱등키·감사 기록. before-snapshot은 내부도구라 row-level 기록으로 충분(외부 자원 스냅샷 불필요).
- **후속**: `notify`(외부 알림)·`handoff_marketing`은 §3f 신뢰게이트 + 풀 사용자 인증 확립 후.

### S5 · 측정 = 재사용
- 기존 `/kpi-baseline`(실행 전 멱등 캡처)·`/measure-kpi`(실행 후 comparison_data·verdict_suggested) 그대로 사용(`atomic_engine.py:625-815`).
- **후속**: 구별 윈도(differenced window)·외생 보정(weather_daily)·진단품질(approval/rejection rate)·적시성(detected_at→sent_at latency) 집계.

### S6 · 보고 = 단일 신뢰게이트 (신축)
- send 직전 신뢰게이트 함수 신설: **substance**(trivial/placeholder/과도단축 거부) + **grounding**(report 수치 vs trigger_context.evidence 대조) + **schema 완전성**(필수키) + **멱등**(이미 발송). 하나라도 실패 → 차단 + 사람 표면화.
- **`_fallback` 단독 의존 폐기**: fallback(bundle/direct) 리포트도 이 게이트를 통과해야 발송 가능.
- 발송 자체는 **SANDBOX 수신자·`ELAYER_SEND_ENABLED` OFF 유지**(실 점주 수신자=풀 사용자 인증 후). 슬라이스는 "신뢰게이트 통과한 draft"까지 입증. 발송 어댑터(`elayer_send.send_email`)·멱등 패턴 재사용.

### S7 · FE (최소 포함)
- v2 execution을 콘솔에서 **CEO/슬롯 카피 없이** 표시 + **도구액션 승인** UI + **승인 후 화면 전이/낙관 갱신**(현 "눌러도 안 변함" 해소).
- 재사용: `board/`(phase 레인이 6단계와 정합 — 카피 교정), `ActionModals`, detect 헬퍼.
- **후속(별도 슬라이스)**: 풀 콘솔 리디자인 + 이번 세션 미push FE 개편분(ExecutionDetail·감지근거·plain calc) 정리.

## 3. 재사용 자산 (구축 토대, file:line)
- 감지: `2026-06-10-sales-anomaly-rpc.sql:13-110`(robust-z·confidence), `detection_settings`+EP(`admin_settings.py:453-470`), `auto_detect_*` dedup/쿨다운(`detection_tasks.py`).
- 분석: `hermes_runner.py`(전체), `hermes_prompt.py:6-18`(_SCHEMA), `analysis_gate.py`(게이트 lite 토대), `app/mcp_server/*`(Bearer+HMAC·ScopeAuth·call_log 완성형).
- 승인/감사: `strategy.py:937·753·701·64-94`(approve/reject/audit), `:1160` rollback(`_SAFE_RESTORE`).
- 측정: `atomic_engine.py:625-815`(baseline/measure), `strategy.py:1014-1041`(finalize verdict).
- 보고: `elayer_send.py:11-72`(어댑터), `strategy.py:632-650`(멱등 발송).
- FE: `AtomicConsole.tsx` 셸, `board/*`, `ActionModals`, detect 헬퍼.

## 4. 제거 대상 (이 슬라이스 = 없음)
- 이 슬라이스에서 옛 스택은 **제거하지 않는다**(공존). §7 제거(CEO 게이트/합성/트리아지/propose, `_DOMAIN_SLOTS` 팬아웃, `dispatch_execution`+PaperclipClient/600초 폴링, bytes/3, FE CEO 카피)는 **Phase 3** — v2가 검증된 뒤.

## 5. 범위 외 (명시)
옛 스택 제거(Phase 3) · `context.*` MCP 확장 · cost/cogs/review 도메인 · L1 신선도 게이트 / L4 정확도 라벨 / 미신뢰 별도트랙 · 외부발송 도구(notify/handoff)·실 점주 수신자 · ②④ 게이트 강화(fast-follow) · 측정 고도화(구별 윈도·외생 보정·진단품질·적시성) · rollback 외부액션 보상.

## 6. 검증 / 테스트
- **단위(pytest)**: safe_tools 레지스트리(가역·멱등·스코프), 보고 신뢰게이트(substance/grounding/schema/멱등 각 통과·차단), v2 라우팅 플래그(ON=v2·OFF=레거시 불변), evidence 보존(sigma·n·dow·confidence 영속), 분석 게이트 ⑤trivial 강화.
- **회귀**: 기존 elayer/strategy/atomic_engine/mcp 테스트 전부 통과(옛 경로 불변 증명).
- **FE(vitest)**: v2 표시·도구액션 승인·전이 단위.
- **e2e(글렌 트리거)**: 실 매출 안건 1건 `run-v2`로 관통 → DB·콘솔에서 6단계 도달 + orphaned/CEO 흔적 0 확인.

## 7. 미결 / fast-follow
- ②수치정합·④환각 실값대조 게이트(슬라이스 직후 fast-follow).
- 풀 콘솔 리디자인 + 미push FE 개편분 정리.
- Phase 3(옛 스택 디커미션) 착수 조건 = 본 슬라이스 e2e 통과 + 며칠 라이브 안정.
