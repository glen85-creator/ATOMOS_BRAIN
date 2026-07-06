---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Olympus Console
tags: [domain/b2b-saas, domain/ops-console, glen-wiki, type/concept]
---
# Olympus Console

## 정의

[[global/glen/concepts/ATOMOS]] 운영 사령탑 UI. 부제: "Atomos Operations Console". super_admin·brand_admin (brand_manager는 R 한정)이 [[global/glen/concepts/Hermes-Agent]] Skill 활동·[[global/glen/concepts/Atomic-Assistant]] 비서 대화·위기 경보·AI 비용을 한 화면에서 가시화. 경로: `/dashboard/olympus` (기존 `/dashboard/strategy-v2` redirect).

> 🔄 **구현 갱신 (2026-06-08)**: 실제 구현 시 **대외명 = "ATOMIC 콘솔", 경로 = `/dashboard/atomic`**(스펙의 `/dashboard/olympus` 아님; `strategy-v2`/`strategy-hub`/`gap` redirect). 7섹션 설계 → 헤더(활성팩 칩·자율성 다이얼·AI 비용 배지) + 3열 피드(자동완료/진행/예외승인) + 탭(feed/timeline/hq/learning)으로 압축, 감지 탭 신설(부진매장+COGS). 컴포넌트 `src/pages/atomic/*`. read EP `/feed`(RPC `get_atomic_feed`, was_auto EXISTS 판정)·`/active-packs`·`/ai-cost-summary`. 구현 상세: 2026-06-08-hbs-atomic-console-engine-impl.

> 🔄 **탭 구성 갱신 (2026-06-09)**: 탭이 **🎛상황실(overview, 기본)·🔔피드·🔍감지·📊회고**로 정착(레거시 timeline·hq 제거). 감지 탭은 4 도메인 슬라이스(S1 부진매장·D-COGS·D-REVIEW·D-COST) 추가 후 **요약 카드 그리드 + 드릴**로 UI 개편 — `StoreStatusPanel` → `DetectionPanel`(카드 4 + 선택 상세) + `UnderperformingPanel`. 상세: 2026-06-09-hbs-atomic-detect-ui-redesign · 감지 슬라이스 2026-06-09-hbs-atomic-s3-review-detection · 2026-06-09-hbs-atomic-s3-cost-detection. 상황실(S2): 2026-06-09-hbs-atomic-s2-situation-room · 자율성 규칙(S3-A): 2026-06-09-hbs-atomic-s3a-autonomy-rules.

## 핵심 아이디어

### 7 섹션 화면
1. **시스템 상태** — Pack 9/12, MCP 2/3, Hermes 정상, Atomic 4 활성, 당월 AI 비용 (API $ / OAuth 정액)
2. **위기 경보 타임라인** — `strategy_executions WHERE status IN ('proposed','running')`
3. **Hermes Skill 활동** — Watch 호출 수·anomaly, Analyst 건수·성공률, Generator 산출량
4. **Atomic 비서 활동** — 활성 비서 카드 (24h)
5. **AI 제안 큐** — `user_decision='pending'` 카드별 승인/수정/반려
6. **Pack 연결 현황** — `pack_registry`, `mcp_connection`
7. **학습 진척도** — `strategy_learning` + 익명 풀 통계, 시나리오 가중치 변화

### 권한별 시야
- super_admin: 7 섹션 / 조직 전체
- brand_admin: 7 섹션 / 본사 소속 매장
- brand_manager: 1·2·3·5·7 (R) / 본사 (집행 관점)
- sv·store_manager: 본인 비서 화면으로 redirect

### 신규 DB
- `pack_registry` — 데이터·에이전트·MCP Pack 등록
- `mcp_connection` — MCP 서버 연결 상태
- `assistant_session` — Atomic 세션 (persona·cost 누적)
- `get_olympus_overview(org_id)` RPC + `get_hermes_stats(window)` RPC

## 적용 예

- PoC Phase 1 (W4): Section 1·2·5 우선 구현

## 관련 개념

- [[global/glen/concepts/ATOMOS]] — 상위 시스템
- [[global/glen/concepts/Atomic-Assistant]] — Olympus가 가시화하는 대상 1
- [[global/glen/concepts/Hermes-Agent]] — Olympus가 가시화하는 대상 2

## 참고

- `ATOMIC_ASSISTANT_DESIGN.md` v1.1 (2026-05-17) §11

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Atomic-Assistant]]
- [[global/glen/concepts/Hermes-Agent]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
