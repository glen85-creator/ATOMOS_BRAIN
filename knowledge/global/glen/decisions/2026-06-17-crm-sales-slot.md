---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: CRM 정식 슬롯 (sales fan-out) — 2026-06-17
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# CRM 정식 슬롯 (sales fan-out) — 2026-06-17

## 맥락
ATOMOS 정식 owner 슬롯 중 CRM_TEAM이 마지막 미생성(provision됐으나 paused 스텁). 헌장 역할="메시지/카카오 발송·고객정보·패턴 분석"(uuid 6f620065). 핵심 긴장: FINANCE/SCM은 cost/cogs 자동트리거가 있었으나 **CRM은 도메인 트리거·고객-레벨 데이터(개별 방문/이탈)가 전무**(POS=매장-레벨 sales).

## 결정 (브레인스토밍)
- 일감 소스: **A — sales fan-out 슬롯**(MARKETING 슬롯 패턴). 신규 CRM 도메인(B)은 고객-레벨 데이터 부재로 비현실적; provisioning-only(C)는 E2E 빈약. A가 즉시 일감+검증된 fan-out.
- 산출물: **PROPOSAL**(리텐션 전략 — 재방문/단골/윈백), RESEARCHER 빌더 미러. MARKETING(콘텐츠 텍스트)와 구분=CRM은 누구에게/왜/전략. CEO 합성이 중복 제거.
- 데이터 한계: 고객-레벨 데이터 없어 **매장-레벨 전략**(개별 타깃 아님).
- 활성화: FINANCE/SCM 패턴(VPS budget 0→1000·pt·warm-up).

## 구현 (subagent-driven, 4태스크)
- **FastAPI PR#28**: config(`ATOMOS_CRM_AGENT_ID`=6f620065·`ATOMOS_CRM_MODEL`·`ELAYER_SALES_CRM_ENABLED` 기본True) · routing `_DOMAIN_SLOTS["sales"]`에 CRM `_Spec`(issue_kind `sales-crm`·step_name "고객 유지·재방문 (CRM)"·enabled_getter·floor=False) · `build_sales_crm_issue`(RESEARCHER 미러·리텐션 지시·PROPOSAL_SCHEMA)+`ISSUE_BUILDERS["sales-crm"]`.
- **ATOMOS_BRAIN#10**: `payloads/ATOMOS_CRM_TEAM.json`·`apply-crm.sh`(RESEARCHER sed 미러).
- **hbs#27**: spec+plan+ROADMAP. VPS 활성화(컨트롤러). migration·FE 없음.
- 2단계 리뷰 + 최종 opus 리뷰(uuid/issue_kind/step_name/flag 체인 전부 PASS, 빌더 RESEARCHER 미러 sound, 기존 6슬롯 무변경).

## 라이브 E2E (decompose가 CRM 선택)
국수나무 춘천CGV점 sales seed → approve → **7스텝 전개(CRM 포함)** = config+routing+approve 와이어링 라이브 확인 → **CEO 동적분해가 CRM 선택**(ANALYST floor+RESEARCHER+SNS+CRM) → CRM 에이전트 실 리텐션 proposal(CGV 입지·관객수 의존 진단+6 actions, 정식 schema) → step completed·`agent_run worker_role=ATOMOS_CRM_TEAM success`. **비-floor CRM을 decompose가 선택한 실증**(가지치기 후보지만 매출급락에 리텐션 관련성 인정 — A 접근의 가치 입증). 정리·재-pause·ROADMAP ✅.

## 🎉 ATOMOS 정식 owner 슬롯 6/6 완성
ANALYST(sales)·MARKETING(review+sales 4채널)·RESEARCHER(sales)·FINANCE(cost)·SCM(cogs)·**CRM(sales 리텐션)** + HERMES(on-demand 폴백). **미생성 owner 0.** paused 스텁=BRAND_DIVISION·CONTENTS·ARCHIVES·VISION(도메인/데이터 생길 때).

## 교훈
- **데이터 현실이 슬롯 설계를 정함**: CRM의 헌장 역할은 고객 메시지/패턴이나 고객-레벨 데이터가 없어 신규 도메인(B) 불가 → sales fan-out 슬롯(A, 매장-레벨 리텐션 전략)이 유일한 즉시-일감 경로.
- **decompose가 비-floor 슬롯을 선택**: CRM은 floor 아님(가지치기 후보)이나 CEO가 매출급락에 리텐션 관련성을 인정해 선택 → fan-out+동적분해가 의도대로 작동(관련 슬롯 선택, 무관 슬롯 가지치기).
- **검증된 패턴 결합**: FINANCE/SCM(활성화) + MARKETING-슬롯(routing/builder)을 합쳐 무-placeholder·빠른 슬라이스. 두 미러를 라이브 코드로 확인 후 박음.

## 상태
CRM 정식 슬롯 라이브·머지·E2E 입증. ATOMOS 정식 owner 6/6 완성. 다음=카톡/SNS 채널·실 점주 수신자 플립·교차도메인 분해·throughput. ADR 연속 [[global/glen/decisions/2026-06-17-elayer-send-email]].

## 관련

- [[global/glen/decisions/2026-06-17-finance-scm-slots]]
- [[global/glen/decisions/2026-06-17-elayer-send-email]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-crm-sales-slot-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-crm-sales-slot.md
