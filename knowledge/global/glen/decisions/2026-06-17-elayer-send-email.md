---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 실발송 — 이메일 (샌드박스 MVP) — 2026-06-17
tags: [domain/atomos, project/hbs-dashboard, status/active, topic/security, glen-wiki, type/decision]
---
# 실발송 — 이메일 (샌드박스 MVP) — 2026-06-17

## 맥락
E층은 draft-only였다: 슬롯 fan-out→CEO 합성→`synthesized_report`(executive_summary·store_message·prioritized_actions·deliverables)→콘솔 점주 리포트 탭 표시까지. 글렌 최초 문제제기의 핵심 = "**발송 버튼이 진짜 일하게**". 외부 send 통합 전무, strategy 라우터 무인증(deferred security). 실송은 outward-facing·hard-to-reverse라 안전 설계가 코어.

## 결정 (브레인스토밍, 4-질문)
| # | 결정 | 선택 |
|---|---|---|
| 1 | 발송 포스처 | **실송 파이프라인 전체 + 샌드박스 수신자**(config 고정, 실 점주 플립은 후속) |
| 2 | 채널 | **이메일**(카톡/SNS는 동일 파이프라인 어댑터로 후속) |
| 3 | 발송 EP 인증 | **최소 인증**(서버사이드 공유 시크릿 헤더). 풀 유저인증은 실수신자 플립 전 선결 |
| 4 | provider | **Resend**(httpx POST, 테스트모드 onboarding@resend.dev→계정주 이메일로만) |

## 안전 불변식 (코어, 최종 리뷰 5/5 PASS)
①수신자 `ATOMOS_SEND_SANDBOX_TO` **하드코딩**(실 점주 미조회) ②`ELAYER_SEND_ENABLED` 기본 **False**(off=dry no-op) ③`X-ATOMOS-SEND-TOKEN`==env, **미설정 시 항상 401**(안전 기본) ④사람 승인 게이트(자동발송 없음, 대시보드 버튼) ⑤`sent_at` 멱등.

## 구현 (subagent-driven, 5태스크)
- **FastAPI PR#27**: migration(`strategy_executions` sent_at·send_channel·send_status·send_to) · config 5개 · `elayer_send.py`(`send_email` Resend soft-fail + `build_owner_email` 순수빌더) · `POST /api/strategy/executions/{id}/send`(가드 순서 token→enabled→exists→report→idempotent→send→record+audit) + GET report EP가 send-state 반환.
- **hbs PR#25**: 점주 리포트 탭 "발송" 버튼+send-state, `strategyExecApi.send`(토큰 헤더), types. **프론트는 executionId만 POST(수신자 로직 없음 — 서버사이드 샌드박스)**.
- 2단계 리뷰 + 최종 opus 교차리뷰(안전 불변식 5/5 PASS, 크로스레포 계약 일치).

## 운영 교훈
- **railway CLI 없음** → Railway/Vercel env는 글렌이 설정(RESEND_API_KEY·ATOMOS_SEND_TOKEN·SANDBOX_TO·ELAYER_SEND_ENABLED + VITE_ATOMOS_SEND_TOKEN). 키는 글렌이 `docs/resend_key.txt`로 전달(평문 키 → .gitignore 추가+E2E 후 삭제 권장).
- **Supabase 관리API 연결 타임아웃 ~10분 블립**(SELECT 1도 실패) — migration apply가 막힘. report EP가 신컬럼을 select하므로 **migration이 deploy 선결**(컬럼 없이 배포 시 점주 리포트 탭 깨짐) → Supabase 회복까지 머지 보류. 회복 후 진행.
- **서브에이전트 mid-task 사망**(Task5 프론트): EDIT 1/2 uncommitted 상태로 죽음 → 완료용 fresh agent에게 "현 상태+남은 EDIT 3/4" 인계해 마무리(skill의 fix-subagent 패턴).

## 라이브 E2E (글렌 메일함 실제 도착)
합성 리포트 seed(국수나무 노량진점)→글렌 Railway env 설정(SANDBOX_TO=glen_85@hbscom.com)→send EP 토큰 호출→`status=sent`·`resend_id`·**글렌 메일함 실제 도착 확인**·DB `sent_at`/`send_status=sent` 기록·재호출 `already_sent`(멱등). 토큰 미설정 시 401도 확인(보안 게이트 작동). seed 정리·ROADMAP ✅.

## 교훈
- **outward-facing은 안전 불변식이 코어**: 수신자 하드코딩·기본 OFF·토큰·사람 게이트·멱등을 설계 첫 질문부터 고정하고 EP 가드 순서로 박음. 최종 리뷰가 각 불변식 PASS/FAIL 명시 검증.
- **샌드박스 포스처가 리스크를 bound**: 실 파이프라인을 진짜 돌리되 수신자를 config 고정(글렌)으로 → "버튼이 진짜 일함"을 안전하게 입증, 실 점주 플립은 풀 유저인증 선결로 분리.
- **인프라 블립 ≠ 코드 문제**: Supabase 타임아웃은 외부 인프라 — 코드는 ready, 회복 대기. migration↔deploy 순서 의존성(신컬럼 select)을 인지해 머지 보류한 게 점주 탭 회귀 방지.

## 상태
실발송 이메일 샌드박스 MVP 라이브·머지·E2E 도착 입증. E층 종착점("발송 버튼") 첫 실증. 보안: 최소 토큰 인증(soft) — 실 점주 수신자 플립 전 풀 유저인증 선결([[global/glen/decisions/2026-06-15-5output-synthesis-delivery]]의 draft-only를 실송으로 닫음). 다음=카톡/SNS 채널·실 점주 수신자 플립·교차도메인 분해·CRM 슬롯. ADR 연속 [[global/glen/decisions/2026-06-17-multislot-perstep-reconcile]].

## 관련

- [[global/glen/decisions/2026-06-17-multislot-perstep-reconcile]]
- [[global/glen/decisions/2026-06-15-5output-synthesis-delivery]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-elayer-send-email-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-elayer-send-email.md
