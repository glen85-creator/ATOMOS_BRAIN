---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Nous Research
tags: [domain/ai, status/active, glen-wiki, type/organization]
---
# Nous Research

## 개요

오픈 모델·에이전트 런타임을 개발하는 AI 연구·제품 조직. 자체 파인튜닝한 Hermes 시리즈 오픈 모델 (Hermes 2/3 — Llama·Mistral 기반)과 [[global/glen/concepts/Hermes-Agent]] (Hermes Agent Runtime)을 운영. ATOMOS v1.1 (2026-05-17) 결정으로 외부 에이전트 런타임으로 전면 채택됨 — 자체 12 워커 풀 구상 폐기와 맞바꿈.

## 관련 프로젝트·제품

- [[global/glen/concepts/Hermes-Agent]] — https://hermes-agent.nousresearch.com/
- Hermes 시리즈 오픈 모델 (Hermes 2 Pro Llama-3, Hermes 3 등)

## 노트

- 본 볼트에서의 위상: HBS Dashboard / ATOMOS의 핵심 외부 의존. Nous Research 정책·라이선스 변경이 ATOMOS 아키텍처에 직접 영향 — 2026-05-17-atomic-assistant-design-v1.1 §모순·의문에서 회귀 비용 산정이 TODO로 남아 있음.
- 호스팅 모델: HBS는 HQ Linux VM/Docker에서 자체 호스팅 예정 (Vercel ↔ Hermes mTLS or VPN-only). OAuth 토큰은 Hermes Host 내부에서만 복호화.

## 관련

- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]
- [[global/glen/entities-technologies/Open-WebUI]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
