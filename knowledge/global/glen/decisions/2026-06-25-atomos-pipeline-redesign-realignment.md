---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: ATOMOS 파이프라인 재설계로 정렬 — CEO/조직/슬롯/Paperclip 폐기, Phase 2 매출 수직 슬라이스 착수"
tags: [domain/hbs-dashboard, domain/ai, domain/agent-runtime, domain/architecture, status/accepted, glen-wiki, type/decision]
---
# ADR: ATOMOS 파이프라인 재설계로 정렬 — CEO/조직/슬롯/Paperclip 폐기, Phase 2 매출 수직 슬라이스 착수

## 컨텍스트

[[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]는 [[global/glen/concepts/Paperclip]]을 "조직 껍데기"로 **재채택**하고 슬롯 두뇌만 [[global/glen/concepts/Hermes-Agent]]로 채우는 중첩구조였다. 그러나 이후 관리형 Paperclip 보드+hermes의 **성능/신뢰 문제**가 드러나(중복 차단·합성 flaky·발송 게이트 양방향 버그·환각 수치·정량화 부족), 2026-06-20 글렌+에이전트는 **전체 파이프라인을 우리가 통제하는 구조로 전면 재설계**하기로 결정하고 `2026-06-20-pipeline-redesign-design.md`("코어 설계 완성")로 박제했다.

2026-06-25 세션에서 글렌이 "콘솔에 아직 CEO·진단팀이 나오는데 이게 우리 설계냐, Hermes엔 CEO가 없는데"라고 의문을 제기 → **전체 설계 계획 점검** 결과: ⓐ 재설계(CEO/팬아웃 제거, 6단계 단일역할)는 **이미 정본 계획**이었고, ⓑ Phase 1(self-hosted Hermes VPS + 우리 MCP 서버)은 origin/main에 **배포 완료**(`ca4d287`: `app/mcp_server/*`+`hermes_runner.py`+마이그 007)이나, ⓒ 라이브 코드는 여전히 옛 CEO/슬롯/Paperclip 스택으로 돌고 최근 작업(PR#64 슬롯 1개 engine-swap, 미push FE 개편)은 **그 계획을 따르지 않은 off-plan 단편**이었음을 확인. 즉 글렌의 의심이 정확했다 — 정본 계획을 안 보고 옛 모델을 패치하던 드리프트.

## 결정

**`2026-06-20-pipeline-redesign-design.md`를 정본으로 정렬.** 6단계 파이프라인(감지 → **단일역할 Hermes 분석 + 출력 검증게이트** → 승인 → **화이트리스트 안전도구 레지스트리 실행** → 측정 → **단일 신뢰게이트 보고**), 실행모델 = **역할 단일단계**(다중에이전트 팬아웃·CEO 합성 제거).

**구현 착수 = Phase 2 매출 수직 슬라이스, 전략 A**(얇은 e2e 신경로): 매출 이상 1건을 플래그(`ELAYER_PIPELINE_V2_SALES_ENABLED`) 뒤 새 단일경로로 관통(감지 evidence 충실도 → 단일역할 Hermes+게이트 → 도구액션 승인 → 안전도구 레지스트리 `record_decision`·`create_task` → 측정 재사용 → 보고 신뢰게이트). **옛 CEO/슬롯/Paperclip 스택은 공존**(제거는 Phase 3, v2 검증 후). 슬라이스 spec = `2026-06-25-pipeline-phase2-sales-slice-design.md`.

## 결과

- 콘솔에서 "CEO·진단팀·슬롯" 개념이 (v2 경로부터) 소멸하는 방향. 글렌이 본 "승인 눌러도 안 변함"은 옛 경로 + 미push FE 때문임을 규명.
- **감지 통계 자체는 견고(우리 RPC 산물)** — 폐기 대상은 그 뒤의 오케스트레이션과 evidence 충실도 버그(`confidence=0.7` 하드코딩·필드 드롭)이지 이상치 감지 수치가 아니다.
- 재사용 대거 확정: `hermes_runner`/`hermes_prompt._SCHEMA`/`analysis_gate`(게이트 토대)/`app/mcp_server/*`/감지 RPC/승인·감사/측정 EP/발송 어댑터. 신축은 **안전도구 레지스트리**와 **보고 신뢰게이트** 두 곳에 집중.

## 구현·배포·라이브 결과 (2026-06-25, 동일 세션)

Phase 2 매출 수직 슬라이스를 subagent-driven으로 완주(16태스크 + 리뷰 수정 3건) → 배포 → **라이브 입증**.

- **v2 파이프라인 라이브 성공**: 마이그 013 prod 적용 + PR(FastAPI#66·hbs#73) 머지 + 플래그 `ELAYER_PIPELINE_V2_SALES_ENABLED=true`(web+worker) ON. 실 매출 이상 안건(`c69743a5`, ST-ET-GR-0001, z=-2.56, gross 329,900 vs 평소 614,400)에 `POST /executions/{id}/run-v2` → **실 self-hosted Hermes 단일역할 분석(62초)** → **CEO 없이** 데이터 근거 도구액션 3건 제안(`flag_data_issue`·`notify`·`record_decision`, 진단이 평소 대비/수집결함 가설을 명시) → `proposed_actions_v2` 영속 → 콘솔 표시. **"데이터 근거 AI 대응 + CEO 개념 제거"라는 재설계 북극성을 처음 실증.**
- **HERMES SSH 키 삽질 → 코드 하드닝**: `HERMES_VPS_SSH_KEY`가 Railway 변수에디터(개행=변수 경계)+한글 로케일(백슬래시 0x5C ↔ 원화기호 ₩ U+20A9)+메모장 라운드트립으로 손상돼 paramiko가 반복 실패. `hermes_runner._normalize_private_key`를 하드닝(base64 디코드 + ₩→백슬래시 보정 + 리터럴 `\n`→실개행 + 파싱실패 시 안전 지문 로그; FastAPI#67/#68). **운영 결론: 키는 base64 한 줄로 저장**(영숫자/+/= 만이라 인코딩 함정 0).
- **감지 근거 충실도 검증 → 3개 보완(글렌 "1,2,3 순서로")**: AI 제안이 근거에 맞는지 검토한 결과 진단 로직은 정확했으나 표시 버그·외부맥락 누락·실행도구 부족을 발견. ①hbs#75 — 감지근거 단위 버그(evidence의 `*_delta_pct`/비율은 **분수**인데 ×100 미적용으로 -54.8%를 "1%"로 표시하던 신뢰성 버그) 수정 + 등급비교 스케일 정합. ②FastAPI#69 — **§3c `context_weather` MCP 도구**: 분석이 감지 기준일의 그 매장 날씨를 자동 조회(st_id→pos_st_uid→관측소→`weather_daily`)해 외부요인(우천·폭설·한파) vs 내부요인 귀속, 데이터 없으면 `found:false`(환각 금지). ③FastAPI#70 — **안전도구 레지스트리 5개로 확장**(`notify`·`flag_data_issue`·`handoff_marketing` executor 추가). `notify`는 수신자 `ATOMOS_SEND_SANDBOX_TO` 하드코딩·`ELAYER_SEND_ENABLED` 게이트·멱등 → 실 점주 발송은 여전히 풀 인증 선결(디퍼드 보안).
- **FE 통합(hbs#74)**: 미머지로 갈라져 있던 콘솔 개편(6단계 스테퍼 `ExecutionDetail` + 감지근거 패널)과 prod의 v2 `ToolActionPanel`을 한 화면으로 합침. 글렌이 "localhost는 절차만, prod는 제안만 보인다(반반 꼬임)"고 한 증상의 근본(두 FE 트랙 분기) 해소. 글렌 로컬 employment 브랜치도 main 동기화 완료(`189cdd6`).

## 이전 결정과의 관계

- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]] **부분 번복**: Paperclip을 "조직 껍데기"로 유지한다는 결정을 폐기 — Paperclip 보드 자체를 제거 대상으로 전환(§7). 단 "앱이 admission/거버넌스 소유" 정신은 신 파이프라인의 검증게이트·승인·신뢰게이트로 계승.
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]와 **정합 강화**: self-hosted Hermes 단일런타임 방향으로 수렴.

## 미결 / 후속

①Phase 3 = 옛 스택(CEO 게이트/합성/트리아지/propose·`_DOMAIN_SLOTS` 팬아웃·`dispatch_execution`+PaperclipClient/600초 폴링·bytes/3) 디커미션 — 본 슬라이스 e2e 통과 + 며칠 라이브 안정 후. ②분석 게이트 ②수치정합·④환각 실값대조 강화(fast-follow). ③풀 콘솔 리디자인 + 미push FE 개편분 정리. ④외부발송 도구(notify/handoff)·실 점주 수신자 = 풀 사용자 인증 선결. ⑤`context.*` MCP 확장·cost/cogs/review 도메인(Phase 4).

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Paperclip]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]

## 출처(원본)

- ATOMOS_BRAIN/docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md
- ATOMOS_BRAIN/docs/superpowers/specs/2026-06-25-pipeline-phase2-sales-slice-design.md
