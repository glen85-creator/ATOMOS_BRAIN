---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Atomic Assistant
tags: [domain/ai, domain/b2b-saas, glen-wiki, type/concept]
---
# Atomic Assistant

## 정의

[[global/glen/concepts/ATOMOS]] Layer 2. 사용자 옆의 비서 인격으로, 의도 분류 + 응답 합성 + [[global/glen/concepts/Hermes-Agent]] Skill 호출 결정을 담당. v1.1 (2026-05-17)에서 4종으로 단순화.

## 핵심 아이디어

### 4종 비서 (v1.1)
| 비서 | 호스트 역할 | 인격 |
|---|---|---|
| 매장 비서 | store_manager (단일·다매장) | "옆에 있는 베테랑 SV처럼" |
| SV 비서 | sv | "베테랑 SV의 디지털 분신" |
| 브랜드 비서 | brand_admin · brand_manager | "본사 임원·실무진의 손" |
| 본사 비서 | super_admin | "조직 OS 본부장" |

staff는 비서 없음 (열람만, AccessControl 매트릭스의 r-self 한정).

### 인격 공통 원칙
- 항상 1인칭 복수 ("저희가 분석한 결과로는…")
- 사실 → 해석 → 권고 순서
- 사람을 평가하지 않음
- 모르면 모른다고 함 (데이터 부족·k-익명성 미달 시 답변 거부)

### 데이터 시야 자동 도출
호스트 사용자의 user_scope에 따라 LLM에 보낼 데이터를 사전 필터링. 다른 매장·본사 데이터는 절대 LLM 입력에 포함 안 됨. 익명 집계는 k≥5 보장 후 시야에 추가 가능. ([[global/glen/concepts/Permission-Matrix]])

### Chain Depth ≤ 3
한 사용자 의도에서 다른 Skill을 부르는 깊이는 최대 3. 그 이상은 사용자 재승인 필요.

## 적용 예

- 점주가 "어제 매출이 왜 떨어졌나요?" → 매장 비서 → Hermes `analyst` Skill 호출 → 응답 합성
- 매출 -28% 4일 위기 → 매장·SV·브랜드 비서 동시 알림 → 점주 승인 → coach/copywriter/pop-writer Skill 체인

## 관련 개념

- [[global/glen/concepts/ATOMOS]] — 상위 시스템
- [[global/glen/concepts/Hermes-Agent]] — 호출하는 외부 에이전트
- [[global/glen/concepts/Olympus-Console]] — Atomic 활동 가시화 UI
- [[global/glen/concepts/Permission-Matrix]] — 시야 결정 근거

## 참고

- `ATOMIC_ASSISTANT_DESIGN.md` v1.1 (2026-05-17) — 단일 진실 원천
- `ATOMOS_INTEGRATED_DESIGN.md` §4 — 개요

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/Olympus-Console]]
- [[global/glen/concepts/Permission-Matrix]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
- raw/docs/hbs-dashboard/docs/ATOMOS_INTEGRATED_DESIGN
