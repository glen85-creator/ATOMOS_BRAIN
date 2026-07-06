---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: ATOMOS 파이프라인 전체 재설계 — self-hosted Hermes + 지식 wiki (2026-06-20)"
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# ADR: ATOMOS 파이프라인 전체 재설계 — self-hosted Hermes + 지식 wiki (2026-06-20)

## 컨텍스트
D-COGS 슬라이스를 실데이터로 끝까지(감지→외주→보고→발송) 돌려보니, 개별 버그 땜질로는 구조적 문제가 해결되지 않음이 드러남: 중복 차단(DB↔Paperclip 멱등 분열), CEO 합성 flaky("test"/"ok" 쓰레기 발송), 발송 게이트 양방향 버그(쓰레기는 통과·정상 fallback은 차단), 토큰/채널 설정 분산, 정량화 부족. 근원은 **Paperclip(보드)·hermes(에이전트)가 Hostinger 관리형 이미지 = 우리 소스 아님·휘발 패치만 가능한 블랙박스**라는 점. VPS recon으로 확정: `ghcr.io/hostinger/hvps-paperclip` + `hvps-hermes-agent`는 pull 이미지(소스 없음·Dockerfile 없음). [[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction|6-12 ADR]]의 "VPS 직접제어" 검토의 연장선에서 전면 재설계로 전환.

## 결정
1. **범위 = 전체 파이프라인 재설계** (감지→분석→승인→실행→측정→보고), 6단계 클린.
2. **실행 모델 = 역할 단일단계** — 도메인별 역할 1개가 분석. 다중 슬롯 CEO 팬아웃·합성 제거(복잡도 축소).
3. **"실행" 정의 = 사람 승인 → 한정 안전도구 자동실행 + 효과 측정.** 실행 위치는 **(A) 엔진이 실행**(Hermes는 분석+읽기전용 조사만; 신뢰 쌓이면 B로 확장).
4. **런타임 = self-hosted Hermes(Nous Research)를 우리 VPS에 직접 설치·통제.** 관리형 Paperclip 보드 + 관리형 hermes 제거.
5. **연동 단일 경계 = 우리 MCP 서버.** Hermes를 "우리 MCP 도구 + 최소 안전 내장도구"로 화이트리스트(`execute_code`·위험도구 차단), command-approval ON, 컨테이너 격리. 트리거=SSH CLI(비대화), 출력=구조화 파서.
6. **지식 wiki = knowledge-as-code.** 소스 GitHub `ATOMOS_BRAIN/knowledge/`(마크다운, 폴더=스코프) → 색인 Supabase **pgvector** → 검색 우리 MCP `knowledge.search(ctx)`가 **스코프(global/brand/dept/store)·권한 필터** 강제. v1=참조지식(사람 큐레이션), 학습지식(검증 사이클 자동축적)은 v2.

## 결과
- (+) 오늘의 거친 seam 구조적 제거: 멱등 단일원천, 동기·관측 가능, 실비용, 단일 트리거, 설정 단일화.
- (+) 매장/부서별 지식 + 권한 접근이 우리 레이어에서 깔끔히 성립(분석 품질↑).
- (+) 블랙박스 종속 탈피 — 모델·프롬프트·검증·재시도·도구·안전을 100% 통제.
- (−) self-hosted Hermes 구동·통제는 미검증(키스톤 리스크) → PoC 선행 필요.
- (−) 신규 컴포넌트(지식 wiki·MCP 서버·검증 게이트·실행 레지스트리) 구축량 큼 → D-COGS 한 도메인 먼저.

## 대안 검토
- **(기각) hermes 버리고 엔진 직접-LLM**: 가장 단순·통제 쉬움. 단 tool-use·자가개선·MCP·서브에이전트 등 에이전트 능력 상실. "실제 도구 실행" 야심엔 부족 → 글렌이 self-host Hermes 선택.
- **(연기) Hermes가 직접 실행(B)**: "실행까지"엔 부합하나 사람 게이트 때문에 재호출·통제 복잡 → 우선 (A) 엔진 실행.

## 참고
- **이 ADR은 [[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction|6-12 ADR]]의 다음 항목을 supersede/진화한다:**
  - "위키 두뇌화 = push 모델, **RAG 아님**" → **번복.** self-host Hermes + 우리 MCP 지식도구로 에이전트가 스코프 지식을 **pull(RAG) 가능**해짐(6-12의 차단요인=관리형 에이전트 terminal-only가 사라짐).
  - "Paperclip 보드 + 다중슬롯 CEO 팬아웃(M2~M4)" → **드롭/단순화**(보드 제거, 역할 단일단계).
  - "단일-Hermes 린스타트 v1" → 유지(여전히 역할 1개부터), 단 self-host로 통제.
- 정본 설계(LIVING): `ATOMOS_BRAIN:docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md`.
- 미결: self-hosted Hermes PoC, 분석 검증 게이트, 실행 안전도구 레지스트리, 측정 지표, 보고 신뢰게이트, 콘솔 UI+조직 시각화(2순위).

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction]]
- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- ATOMOS_BRAIN:docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md
- https://hermes-agent.nousresearch.com/docs
