---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: ATOMOS 실행루프 정직화 · 조직 오케스트레이션 방향 (2026-06-12)
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# ATOMOS 실행루프 정직화 · 조직 오케스트레이션 방향 (2026-06-12)

## 맥락
글렌이 ATOMOS 콘솔의 "승인→발송" 루프에 위화감 제기 → 감지~승인은 살아있으나 승인 이후(실행·산출물·발송)는 화면만 있고 엔진이 없음을 진단. 이어 VPS 직접 제어 가능성과 ATOMOS_BRAIN을 에이전트 두뇌로 다는 설계를 검토.

## 결정
1. **조직 정본 = github `glen85-creator/ATOMOS_BRAIN`.** CEO=오케스트레이터(kimi, dispatch_plan) + 6슬롯(HERMES·ANALYST·MARKETING·RESEARCHER·CTO) 전부 Paperclip VPS에 provision됨·전원 paused. **단일-Hermes 가동은 버그가 아니라 헌장 §3-3 의도된 린스타트 v1**(비용 다이얼). 승격순서 ANALYST→MARKETING→CEO.
2. **위키 두뇌화 = push 모델**(슬롯 instructions static bake + 이슈 본문 inject). pull/RAG 아님 — 에이전트가 toolsets=terminal 단독 + SOUL/TOOLS 금지조항(임의 curl·git·fs 금지) 트리플락으로 위키 능동 쿼리 불가. 별도 RAG는 헌장 미결 #8이 '증분4 연기'로 이미 결정(재발명 금지).
3. **VPS 직접제어 = HTTP 보드 API(런타임: 이슈생성·wakeup·pause/un-pause·코멘트회수)·ssh+docker-exec(설정·모델·instructions·패치).** VPS 상주 Claude tmux 릴레이(pcmsg.sh)는 제어채널에서 제외, 대화 전용. admin 비번 평문로그인 → 전용 에이전트 키 Bearer 경로 추가(board operator 토큰은 Paperclip #3479 미구현).
4. **보안 분리**: S-APP(프론트→FastAPI Supabase JWT 인증, require_role, axios 인터셉터)는 **from-scratch·솔로 dev 보류**(require_role가 FastAPI에 아예 없음). S-BRIDGE는 완화(비번 로테이션·Traefik IP허용목록)+키 경로만.
5. **실행루프 정직화**: finalize는 산출물(완료 스텝 또는 agent_run)이 없으면 verdict를 achieved/partial/missed로 못 주고 inconclusive로 강등. 자동승격 스트릭도 산출물 있는 실행만 집계. 빈 완료가 학습·자동승격을 오염시키던 경로 차단.

## 산출물 (커밋)
- FastAPI `feat/bridge-auth-hardening` (b81d80e) · `fix/atomos-execution-honesty` (e4a0f03) — 둘 다 origin/main 격리 워크트리, 병렬 'master 정리' 세션 reconcile 후 머지.
- hbs main `ed79306` (D4-FE verdict 카드 경로·D2-FE 버튼 라벨, **배포됨**) · `d2cd9dd`·`8f7d46d` (설계·복구 문서).
- D1 데이터 오염 MCP 라이브 정정: SC-SR-001 success_score 100→50, 빈완료 2건 achieved→inconclusive, 미실행 스텝 4 skipped, 오염 학습행 삭제.

## 미해결
- FastAPI 워크트리 2개 머지 대기(reconcile 후). 정리: `git worktree remove`.
- `dashboard.py:2053` finalize도 산출물 가드 없음(별 도메인, 후속 티켓).
- 에이전트 키 board-mutation 권한 #1177 실측 미정 — dev 1사이클 후 admin 비번 제거 여부 결정.
- 후속 E층(승인 후 CEO dispatch→다중슬롯 fan-out): 헌장 M2~M4 풀포워드.


## 후속 (2026-06-12 PM) — skeleton 실증 + 예산 전략 확정

- **Walking skeleton END-TO-END 실증**: ELAYER_DISPATCH_ENABLED=true + ANALYST 활성화로 승인→ANALYST 실진단(deepseek)→콘솔 렌더까지 검증(exec 79c3fa76, cost $0.0006). 스파인(트리거→디스패치→회수→적재→표시) 정상. → "발송 버튼이 일을 안 한다" 원문제 해소 입증.
- **결정: Paperclip 예산 = advisory, 실비용 SoT = 우리 `agent_run`.** 근거: Paperclip 어댑터의 COST_REGEX가 에이전트 proposal의 `est_cost_usd`(비즈니스 액션 비용추정)를 LLM 지출로 오긁어 가짜 정지를 유발(ANALYST $350 사례, 실비용 $0.0006). regex 기반이라 돈 얘기하는 모든 에이전트에 재발 → Paperclip 예산은 노이즈 위로 높게(advisory) 두고, 실제 비용 추적·캡은 앱쪽(agent_run + autonomy cost_ceiling)에서. org 재설계 시 전 에이전트 동일 적용.
- **디스패처 수정**: create_issue(assignee·idle)의 Assignment run이 실측 성공 경로 → 중복 wake_agent(On-demand timeout) 제거(origin/main `00c6505`).
- **미결(다음 레이어)**: 스텝 모델 재설계 — 스텝 = B층 canned key_actions가 아니라 "디스패치 슬롯/산출물 1개당 1스텝". 다중슬롯·CEO 분해와 한 묶음으로 다음 브레인스토밍에서 결정.

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-11-execution-loop-audit-and-recovery.md
- hbs-dashboard:docs/superpowers/specs/2026-06-11-bridge-auth-hardening-design.md
