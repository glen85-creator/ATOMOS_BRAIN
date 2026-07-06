---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: FINANCE/SCM 정식 슬롯 (cost→FINANCE·cogs→SCM, HERMES 폴백 교체) — 2026-06-17
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# FINANCE/SCM 정식 슬롯 (cost→FINANCE·cogs→SCM, HERMES 폴백 교체) — 2026-06-17

## 맥락
β-cost/β-cogs(2026-06-14)는 cost owner=FINANCE·cogs owner=SCM이 **미생성**(Paperclip 에이전트 전무)이라 헌장 §3-3 HERMES 폴백을 채택했었다. 빌더(`build_cost_issue`/`build_cogs_issue`)·라우팅·디스패처는 이미 존재. 이제 FINANCE/SCM 전담 에이전트를 활성화해 폴백을 정식 owner로 교체한다. roster엔 FINANCE_TEAM·SCM_TEAM이 paused 스텁으로 존재(2026-06-14 골격완성 PR#4).

## 결정 (브레인스토밍)
**스코프 = FINANCE·SCM 둘 다 활성화.** RESEARCHER/MARKETING 활성화 패턴 재사용: payload=RESEARCHER 미러(인라인 task-agnostic promptTemplate)·uuid 스왑, apply 스크립트 sed 미러. 빌더·디스패처·FE **무변경**(에이전트만 교체). 단일슬롯 도메인이라 throughput 우려 없음.

## 구현 (subagent-driven, 5태스크)
- **FastAPI PR#25**: config `ATOMOS_FINANCE_AGENT_ID`(`bc0e684a`)·`ATOMOS_SCM_AGENT_ID`(`cbc2768b`)·`MODEL`=deepseek-v4-flash; routing `cost-util`/`cost-contract`→FINANCE·`cogs-ig`→SCM `_Spec`(active·uuid/model_getter, coarse `cost`/`cogs` placeholder 라벨도 정합); bridge 이슈타이틀 `(HERMES)`→`(FINANCE)`/`(SCM)`; FEATURES owner 갱신.
- **ATOMOS_BRAIN#9**: `deploy/payloads/ATOMOS_FINANCE_TEAM.json`·`ATOMOS_SCM_TEAM.json`(RESEARCHER 미러)·`apply-finance.sh`·`apply-scm.sh`.
- **hbs-dashboard PR#23**: spec+plan+ROADMAP.
- **VPS 활성화(ssh paperclip-host+docker exec)**: FINANCE/SCM **budget 0→1000·promptTemplate False→True·hermes_local·deepseek** PATCH. Task2는 서브에이전트 socket-death로 컨트롤러 직접 수행. 2단계+최종 교차리뷰(READY).

## 핵심 실측 — status 모델
신규 슬롯 활성화 = **budget 0→1000 + promptTemplate 플립**이 진짜 활성화 신호. **status=paused가 정답** — 라이브 보드서 known-working ANALYST·RESEARCHER·HERMES 전부 `paused`가 휴지상태이고, 디스패치가 per-slot `idle`↔`paused`로 토글한다(MARKETING만 최근 활동으로 `idle`). 처음엔 paused가 미활성으로 보여 오해했으나, 실 에이전트 상태 비교로 확정.

## warm-up wake 실측
신규 슬롯 첫-spawn 레이스(PAPERCLIP_API_KEY 미주입) 회피: `PATCH status=idle`(러너 spawn) + `POST /api/agents/{id}/wakeup`. wakeup은 **idle여야 202**, paused면 **409 "Agent is not invokable"**. status=running 확인 후 PR+배포 지연이 cold-spawn 흡수. 디스패치 자체는 wakeup 없이 idle 전환+이슈할당만(에이전트 auto-pickup).

## 라이브 E2E (실 seed 2건)
- **cost-util**(국수나무 독산시티렉스점, 공과금 +68.2%) → approve → step_name "비용 진단·대응 **(FINANCE)**" 동적생성(`_steps_for_execution`+`resolve_dispatch`, **배포 자가검증**) → CEO 게이트 GO → FINANCE 에이전트 실 proposal(누진세 구간·냉방기 진단+actions 3) → `_poll_slot_output` 회수 → step completed·**agent_run worker_role=ATOMOS_FINANCE_TEAM success**.
- **cogs-ig**(신선식자재 ㈜프레시, 공급가 +23.5%) → 동일 흐름, step "공급가 진단·대응 **(SCM)**" → SCM 에이전트 실 proposal(초여름 수급 진단+actions 3) → **agent_run worker_role=ATOMOS_SCM_TEAM success**.
- 둘 다 정식 proposal schema(`diagnosis`+`actions`, raw/trivial 아님). seed/워크트리/브랜치 정리·FINANCE/SCM 재-pause 완료.

## 교훈
- **status≠활성화**: hermes_local 슬롯은 paused가 휴지상태의 정답. budget+promptTemplate이 활성화 신호. 라이브 비교 없이 payload만 보면 오판.
- **approve가 배포 자가검증**: `_steps_for_execution`이 `resolve_dispatch`서 step_name을 동적생성 → 승인 직후 step_name이 (FINANCE)/(SCM)이면 신규 routing 배포 확정, (HERMES)면 stale(삭제 후 재시드). 별도 버전 마커 불필요.
- **첫-run cold transient 재확인**: FINANCE가 이번 run에서 ~9분 소요(SCM은 정상). warm-up에도 간헐 cold가 남으나 inline 폴 윈도 내 회수 성공(또는 reconcile 안전망).

## 상태
FINANCE/SCM 정식 슬롯 라이브·머지·E2E 입증. ATOMOS 정식 owner 슬롯 = ANALYST(sales)·MARKETING(review+sales 4채널)·RESEARCHER(sales)·FINANCE(cost)·SCM(cogs); HERMES=on-demand 폴백; 미생성 owner=CRM만 남음. 다음=멀티슬롯 per-step reconcile·실발송·동일에이전트 throughput. ADR 연속 [[global/glen/decisions/2026-06-16-slot-reliability]].

## 관련

- [[global/glen/decisions/2026-06-16-slot-reliability]]
- [[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-finance-scm-slots-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-finance-scm-slots.md
