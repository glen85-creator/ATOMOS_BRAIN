---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Paperclip
tags: [domain/ai, domain/agent-runtime, glen-wiki, type/concept]
---
# Paperclip

## 정의

[[global/glen/concepts/Strategy-V2]] Phase 2에서 도입 예정인 멀티 에이전트 오케스트레이션 플랫폼. [[global/glen/concepts/Hermes-Agent]]가 "감지" 측면이라면 Paperclip은 "생성·집행" 측면. CMO·COO·CFO 가상 임원 에이전트가 협업해 마케팅·운영·재무 의사결정을 합성.

## 핵심 아이디어

- **Phase 2 통합 배경**: 합의 의사결정에서 "B2C AI는 별도가 아니라 Strategy V2 Phase 2(Paperclip)와 통합" — 감지([[global/glen/concepts/Hermes-Agent]]) + 생성(Paperclip)이 한 몸이어야 의미 있음. B2C·B2B 같은 에이전트 인프라 공유.
- **Paperclip 조직도** (Strategy Hub V2 design):
  - **CMO 에이전트** — 마케팅 카피, POP, SNS 콘텐츠 생성
  - **COO 에이전트** — 운영 코칭 메시지, 매장 SOP
  - **CFO 에이전트** — 비용 분석, 가격 시뮬레이션
- **v1.1 이식 후 위상**: ATOMIC_ASSISTANT_DESIGN v1.1 (2026-05-17)에서 자체 워커 폐기 결정 — Paperclip의 CMO/COO/CFO 역할이 Hermes Skill로 흡수될 가능성.

> 🔄 **역할 재정의·부활 (2026-06-03 ADR, 위 TODO 해소)**: v1.1의 "Paperclip 폐기"가 [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]로 **공식 번복**되되, 원래의 "실행자/가상 임원(CMO·COO·CFO)" 역할이 아니라 **"조직 껍데기"**(에이전트 슬롯·이슈/태스크·라이프사이클·예산·승인 게이트·config 롤백·감사·비용추적 내장)로 재정의됨. 각 슬롯의 "두뇌"는 [[global/glen/concepts/Hermes-Agent]]가 HTTP 에이전트로 채운다. 거버넌스 분할: 앱=Admission Gate(risk/confidence), Paperclip=Execution Governance(예산·승인·감사·롤백). S0 구현에서 `strategy_executions.paperclip_project_id/issue_id/agent_id` 링크 컬럼 추가, terminal-native 디스패치로 실제 Paperclip 경유 제안 실증(exec bb759785). 구현 상세: 2026-06-08-hbs-atomic-console-engine-impl.

## 적용 예

- Phase 2 (2026 후반): B2C·B2B 동시 가동 예정

## 관련 개념

- [[global/glen/concepts/Strategy-V2]] — 상위 시스템 (Phase 2)
- [[global/glen/concepts/Hermes-Agent]] — 동격 (감지 측)
- [[global/glen/concepts/ATOMOS]] — 최상위

## 참고

- hbs-strategy-hub-v2-design
- 2026-05-07-roadmap-b2c-to-b2b

## 관련

- [[global/glen/concepts/Strategy-V2]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/ATOMOS]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/STRATEGY_HUB_V2_DESIGN
- raw/docs/hbs-dashboard/docs/ROADMAP_B2C_TO_B2B
