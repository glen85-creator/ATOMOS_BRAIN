---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Strategy V2
tags: [domain/ai, domain/b2b-saas, glen-wiki, type/concept]
---
# Strategy V2

## 정의

[[global/glen/concepts/ATOMOS]]의 AI 자동 폐쇄 사이클 코드명. 매시간 매출 감지 → AI 진단 → 본사 1차 승인 → 5개 자산 동시 생성 → 본사 2차 그룹 검토 → 점주 전달 → 21일 KPI 측정 → 학습 가중치 갱신의 한 사이클. Phase 1 V2 코드 완료, 2026-06-15 가동 대기.

## 핵심 아이디어

### 감지 룰
매출 -25% × 4일 (지역 기준) AND -20% × 3일 (자기 baseline)

### AI 생성 자산 5종
1. 매출 분석 보고서 (Hermes `analyst`)
2. SNS 카피 3종 (따뜻한 친근 / 트렌디 / 시그너처) (`copywriter`)
3. POP / 매장 안내문 (`pop-writer`)
4. 부정 리뷰 응대 초안 (`review-responder`)
5. 점주 코칭 메시지 (`coach`)

### 비용 모델
시나리오당 ₩2,000~5,000 (1 cycle) — Claude Sonnet 4.5 + Ollama Cloud Qwen 3 Hybrid. Ollama 정액 ₩140k/월로 분류 작업 무한 처리.

### 학습 루프
21일 후 `analyst-final` Skill이 효과 측정 → `strategy_learning` 가중치 갱신 → 다음 시나리오 추천 정확도 향상

### Phase 단계
- Phase 1: 데이터 모델 + sales-watch (코드 완료, 가동 대기)
- Phase 1b(2026-05-30 증분1): 실행루프(approve/finalize/cost/rollback/gate-check/autonomy-policy) 501 스텁 → **실동작 전환**, ATOMIC 콘솔로 전면개편. 상세 2026-06-08-hbs-atomic-console-engine-impl
- Phase 2: Paperclip CMO 통합 (B2C·B2B 동시) — ※ 2026-06-03 ADR로 Paperclip 역할이 "조직 껍데기 + Hermes 슬롯 두뇌"로 재정의([[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]])
- Phase 3: Hermes 4종 + 학습 루프
- Phase 4: 자기진화 (DSPy/GEPA)

## 적용 예

- 2026-06-15 가동 — HBS 자체 매장으로 시작
- 베타 본사 1~2곳 도입 후 외부로 확장

## 관련 개념

- [[global/glen/concepts/ATOMOS]] — 상위 시스템
- [[global/glen/concepts/Hermes-Agent]] — Skill 실행 런타임

## 참고

- `STRATEGY_HUB_V2_DESIGN.md`
- `docs/superpowers/specs/2026-05-03-strategy-hub-v2-phase1-design.md`
- `BUSINESS_PLAN.md` §3-2

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/Paperclip]]
- [[global/glen/decisions/2026-05-30-strategy-supabase-to-fastapi-phase1a]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/STRATEGY_HUB_V2_DESIGN
- raw/docs/hbs-dashboard/docs/BUSINESS_PLAN
- raw/docs/hbs-dashboard/docs/ROADMAP_B2C_TO_B2B
