---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Hermes Agent
tags: [domain/ai, domain/agent-runtime, glen-wiki, type/concept]
---
# Hermes Agent

## 정의

[[global/glen/entities-organizations/Nous-Research]]가 개발한 외부 에이전트 런타임. [[global/glen/concepts/ATOMOS]] Layer 1로 채택 ([[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent|ADR-001]], v1.1, 2026-05-17). Skill Registry + Provider Routing (OAuth + API LLM) + MCP 어댑터 + 캐시·재시도·로그를 제공. 자체 호스팅 가능. URL: https://hermes-agent.nousresearch.com/

## 핵심 아이디어

### v1.0 → v1.1 전환
v1.0에서는 자체 12 워커 풀을 구축할 계획이었으나, LLM 라우팅·재시도·캐싱·OAuth·MCP 어댑터를 모두 자체 구현해야 했음. v1.1에서 Nous Hermes 전면 도입 결정 — 자체 워커는 모두 **Hermes Skill**로 이식.

### Skill 구조
```
skills/
└── analyst/
    ├── skill.yaml          # 메타 (name, callerRoles, preferredTrack, ...)
    ├── prompt.md           # 시스템 프롬프트
    ├── input_schema.json
    └── output_schema.json
```

### 12 Skill (v1.1 기준)
- Watch: sales-watch, cost-watch, customer-watch, operation-watch, review-watch, finance-watch
- Analyst: analyst, analyst-final
- Generator: coach, copywriter, pop-writer, review-classify, review-responder

### Provider Routing — 이중 트랙
| 트랙 | LLM | 비용 모델 | 적용 |
|---|---|---|---|
| API | Anthropic API, OpenAI API, Ollama | 토큰당 과금 | cron Watch, 대량 호출 |
| OAuth | Claude Max, ChatGPT Plus, Gemini Advanced | 정액제 (한계비용 0) | 사용자 인터랙티브 |

본사 단일 Claude Max 1계정으로 매장 N개 비서 호출 가능 (rate-limit 한도 내).

### 자체 호스팅 토폴로지
- HQ Linux VM/Docker에서 hermes-agent 컨테이너 실행 (port 7437)
- Vercel ↔ Hermes는 mTLS or VPN-only
- OAuth 토큰은 Hermes Host 내부에서만 복호화 (Vercel·Supabase는 토큰 미보유)
- 모든 Skill 호출은 `request_id` 기준 audit_log 기록

### Gateway / API Server — OpenAI 호환 채널
2026-05-21-hermes-open-webui-integration 클립에서 명확화된 측면. Hermes Agent는 `hermes gateway run` 으로 **OpenAI 호환 API Server**를 노출한다 (기본 `http://127.0.0.1:8642/v1`, `~/.hermes/.env`의 `API_SERVER_ENABLED=true` + `API_SERVER_KEY=…` 로 활성).

이 덕분에 동일한 Hermes 에이전트를 다음 채널에서 모두 사용할 수 있다.

| 채널 | 용도 | 비고 |
|---|---|---|
| CLI | 빠른 진단·로컬 작업 | 기본 입구 |
| [[global/glen/entities-technologies/Open-WebUI]] | 웹 채팅 데모·교육·세일즈 | OpenAI 호환 엔드포인트로 연결 |
| Slack | 팀 업무 채널 운영 | 별도 어댑터 |
| cron | 무인 자동 실행 (Daily Briefing 등) | API 트랙 권장 |
| MCP | 외부 도구·리소스 통합 | Hermes 내장 어댑터 |

→ 채널을 늘리는 것이 본질이 아니라 **어떤 업무를 어느 입구에서 받을지** 정하는 것이 운영 결정.

## 적용 예

- HBS 자체 호스팅: PoC W0 2주 (2026-05+ 예정)
  - Nous Hermes 로컬 Docker 설치
  - Claude Max OAuth 연결
  - `analyst` 1종 구현 + Vercel → Hermes HTTP 통합 (mTLS)
  - 매장 1곳 시범

## 관련 개념

- [[global/glen/concepts/ATOMOS]] — 상위 시스템
- [[global/glen/concepts/Atomic-Assistant]] — Hermes를 호출하는 Layer 2
- [[global/glen/concepts/RAG]] — 다른 방향의 아키텍처 (대비)

## 참고

- 공식 사이트: https://hermes-agent.nousresearch.com/
- 본 볼트 설계 문서: `ATOMIC_ASSISTANT_DESIGN.md` v1.1 (2026-05-17) §0, §10, §12

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Atomic-Assistant]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]
- [[global/glen/entities-technologies/Open-WebUI]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
- Clippings/05-11. Hermes Agent Gateway로 Open WebUI 붙이기
