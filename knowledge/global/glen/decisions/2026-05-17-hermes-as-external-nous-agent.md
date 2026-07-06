---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR-001: \"Hermes\"를 Nous Research의 외부 에이전트 런타임으로 단일 정의"
tags: [domain/agent-runtime, domain/architecture, status/accepted, glen-wiki, type/decision]
---
# ADR-001: "Hermes"를 Nous Research의 외부 에이전트 런타임으로 단일 정의

## 컨텍스트

[[global/glen/concepts/Atomic-Assistant]] v1.0 (2026-05-15 이전) 시점까지 본 시스템 설계에서 "Hermes"는 **자체 구축할 12 워커 풀(analyst·coach·copywriter·sales-watch 등)** 을 가리키는 내부 명칭으로 사용되어 왔다. 동시에 [[global/glen/entities-organizations/Nous-Research]]가 운영하는 외부 오픈소스 에이전트 런타임 [Hermes Agent](https://hermes-agent.nousresearch.com/) 가 같은 이름을 갖고 있어 명명 충돌이 잠재해 있었다.

2026-05-17 ATOMOS 전략 회의 (`raw/meetings/claude-conversations/57256c3e-…` L.66980-67260) 에서 사용자(glen)가 "내가 처음부터 말한 Hermes는 [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com)" 임을 명시. 그동안의 v1.0 설계가 **자체 워커 풀** 방향으로 잘못 발전했음이 확인됨.

자체 워커 풀을 유지할 경우 다음을 모두 자체 구현해야 하는 부담이 있었다.
- LLM Provider Routing (Anthropic / OpenAI / Gemini)
- OAuth 정액제 토큰 관리 (Claude Max / ChatGPT Plus / Gemini Advanced)
- Skill Registry · 캐싱 · 재시도 · 로그
- MCP / ACP 통합

외부 Hermes Agent는 위 기능이 검증된 외부 도구로 이미 제공된다.

## 결정

본 시스템에서 "Hermes"라는 명칭은 **[[global/glen/entities-organizations/Nous-Research]]가 개발·유지보수하는 외부 오픈소스 Hermes Agent (자체 호스팅 가능)** 만을 가리킨다. 자체 12 워커 풀 구상은 폐기한다.

세부 결정:

1. **단일 정의** — 문서·코드·발표에서 "Hermes"는 외부 Nous Hermes Agent. 우리가 만드는 것은 그 위의 [[global/glen/concepts/Atomic-Assistant]] 비서와 Skill들이다.
2. **자체 12 워커 폐기** — 기존 워커는 `skills/{name}/{skill.yaml, prompt.md, input_schema.json, output_schema.json}` 구조의 **Hermes Skill** 로 이식 (12종 카탈로그 유지: Watch 6 + Analyst 2 + Generator 5 — v1.1 §10 표).
3. **호스팅 토폴로지** — HQ Linux VM/Docker에서 `hermes-agent` 컨테이너 실행 (port 7437). Vercel ↔ Hermes 통신은 **mTLS 또는 VPN-only**. OAuth 토큰은 Hermes Host 내부에서만 복호화 (Vercel·Supabase는 토큰 미보유). 모든 Skill 호출은 `request_id` 기준 `audit_log` 기록.
4. **이중 트랙 비용 모델** — API 트랙 (Anthropic/OpenAI/Ollama 토큰당 과금) + OAuth 정액 트랙 (본사 단일 Claude Max/ChatGPT Plus/Gemini Advanced 계정으로 매장 N개 비서 호출). `via_oauth` 플래그 + Auto-downgrade + Prompt Caching.
5. **운영 책임 분리** — Hermes 호스팅·OAuth·Skill 카탈로그는 **본사** 책임. Vercel Functions · Atomic 비서 UI · 권한 매트릭스 · 마스킹 정책은 우리 책임 그대로.

## 결과

### 긍정

- 검증된 외부 도구를 백엔드로 사용해 LLM 라우팅·OAuth·MCP 통합을 자체 구현하지 않아도 됨.
- 정액제 OAuth 채택 시 비용 절감 (예상 월 $113 API → $35~50 하이브리드, ATOMIC_ASSISTANT_DESIGN v1.1 §9 추정).
- 명명 충돌 해소 — "Hermes = Nous 외부 도구" 단일 의미.
- Atomic 비서·권한 매트릭스·마스킹·[[global/glen/concepts/Olympus-Console]] 등 본 시스템의 차별화 자산은 그대로 유지.

### 부정

- HQ 자체 호스팅 인프라 부담 (24/7 가용성, Docker 운영, OAuth 토큰 갱신).
- Vercel ↔ Hermes 네트워크 의존성 (mTLS/VPN 설정 필요).
- Nous Research 라이선스·로드맵 변경 시 리스크 (외부 의존성).
- 기존 v1.0 워커 코드 자산은 폐기 또는 Skill로 재구성 필요.

### 후속 변경 (실행 완료)

- `ATOMIC_ASSISTANT_DESIGN.md` v1.0 → v1.1 (2026-05-17, 2026-05-17-atomic-assistant-design-v1.1 요약 참조)
  - §0 아키텍처 결정 신설
  - §1 비서 4종 단순화 (매장·SV·브랜드·본사)
  - §5 Skill Chain 깊이 ≤ 3
  - §10 `HermesSkillSpec` / `SKILL_REGISTRY` / `invokeHermesSkill` 인터페이스
  - §11 Olympus 비용 표시 `API $X / OAuth 정액 ($0)`
  - §12 PoC W0 5단계 + 워커 → Skill 이식 매핑표 + Phase 1 27h 작업 분해

## 대안 검토

| 옵션 | 평가 |
|---|---|
| A. 외부 Nous Hermes 셀프호스트 백엔드 | **채택**. 정액제 OAuth + Skills + MCP + Provider Routing 즉시 활용. |
| B. Vercel Sandbox에 Hermes 호스트 | 보류. Sandbox는 ephemeral이라 OAuth 토큰 영속화 까다로움. PoC 검증 후 재고. |
| C. 우리 자체 워커 유지 + Hermes 패턴만 차용 | 폐기. OAuth 정액제 효과 없음, 명명 충돌 잔존. |
| D. 점주·SV가 Hermes CLI 직접 사용 | 폐기. 점주에게 CLI는 부적합. |

## 참고

- 외부 도구: https://hermes-agent.nousresearch.com/
- 의사결정 발생 시점 대화 로그: `raw/meetings/claude-conversations/57256c3e-1a31-49a3-9065-6d95d7d9cd60.md` L.66980-67700 (정정 인지 → 4 옵션 비교 → v1.1 작성)
- 본 결정의 명문화: `ATOMIC_ASSISTANT_DESIGN.md` v1.1 §0
- 관련 후속 ADR (확정): [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]] — Paperclip 부활·Hermes 슬롯 두뇌(본 v1.1 "Paperclip 폐기" 결정을 부분 번복)
- 후속 ADR 후보 (미발췌):
  - Phase 1 5결정 매트릭스 (대화 L.43002)
  - Hermes/Paperclip 명명 보류 (L.41715)
  - Olympus §11 마이그레이션 (L.68302)

## 관련

- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Atomic-Assistant]]
- [[global/glen/entities-organizations/Nous-Research]]

## 출처(원본)

- raw/meetings/claude-conversations/57256c3e-1a31-49a3-9065-6d95d7d9cd60
- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
