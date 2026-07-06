---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 전략실행(strategy.ts) Supabase 직결 → FastAPI 경유 전환, Phase 1a/1b 분리"
tags: [domain/hbs-dashboard, domain/backend, domain/architecture, status/accepted, glen-wiki, type/decision]
---
# ADR: 전략실행(strategy.ts) Supabase 직결 → FastAPI 경유 전환, Phase 1a/1b 분리

## 컨텍스트

프론트 `src/api/strategy.ts`(전략실행 로그)가 Supabase에 직접 접근해 `CLAUDE.md`의 "프론트 Supabase 직접접근 금지" 아키텍처 규칙을 위반했고, approve/finalize/cost 메서드는 baseURL 없는 상대경로 `fetch`라 프로덕션에서 깨져 있었다. cost-hub·인건비·고정비 전환에서 확립된 `cost.py` 헬퍼+Pydantic+Phase A 패턴을 재사용 가능했다. team-lead 실DB 확인 결과 `strategy_execution_cost` 테이블·`finalized_at`·`rejection_reason` 컬럼이 전부 부재 → #5~7(approve/finalize/cost)은 단순 전환이 아니라 신규설계+마이그레이션 사안.

## 결정

**Phase 1a**로 조회 3개+reject(#1~4)만 FastAPI `/api/strategy/*` 7 EP로 전환·배포하고, approve/finalize/cost(#5~7)는 **HTTP 501 스텁으로 분리**해 Phase 1b(별도 실행루프 설계)로 격상. 이름충돌 회피 위해 `client.ts`에 `strategyExecApi` 신설(기존 `strategyApi`=전략허브와 구분), `strategy.ts`는 thin wrapper 위임으로 페이지·훅 0줄 수정. 상대 `fetch`→axios baseURL 이관(프로덕션 버그 동시 수정). JWT+scope 403은 Phase A 공통 제외(Phase B 부채).

## 결과

Supabase 직접접근 제거·빌드 0에러로 아키텍처 규칙 준수. 후속 Phase 1b(증분1)에서 501이 실동작으로 전환되며 `autonomy_policy` 신설·실행루프가 닫힘(같은 작업 사이클 내 해소). 보안(JWT+scope)은 디퍼드.

## 대안 검토

- **#5~7까지 한 번에 전환**: 참조 테이블·컬럼 부재로 신규설계가 선행돼야 해 일괄 전환 불가 → 501 스텁으로 분리.
- 동일 패턴이 `supabase-cleanup-roadmap`의 Phase 1(A 전략실행) PoC로 확립되어 C(HQ/분석)·B(SV)·D(사업개발)·E(마스터)로 확장 예정.

## 참고

- 2026-06-08-hbs-atomic-console-engine-impl (구현 요약, 증분1에서 Phase 1b 해소)
- 2026-05-30-cost-hub-fastapi-migration (선행 패턴)

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/concepts/Strategy-V2]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/reports/2026-05-30-phase1-strategy-exec-report.md
- raw/docs/hbs-dashboard/docs/superpowers/plans/2026-05-30-phase1-strategy-exec-migration.md
- raw/docs/hbs-dashboard/docs/superpowers/plans/2026-05-30-supabase-cleanup-roadmap.md
