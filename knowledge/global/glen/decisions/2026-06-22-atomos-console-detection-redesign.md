---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: ATOMOS 콘솔 + 감지 기준 재설계 (Phase 2)
tags: [domain/frontend, domain/hbs-dashboard, status/active, priority/high, glen-wiki, type/decision]
---
# ATOMOS 콘솔 + 감지 기준 재설계 (Phase 2)

## 맥락 (Context)

글렌의 실사용 평가: 기존 **ATOMOS 콘솔**은 조악·난독했다 — 3탭(홈/감지/회고) + 1400줄 단일 모달, 세로 리스트, 칸반 없음, 그리고 **표시되는 수치가 검증되지 않아 사용가치가 낮았다.** 기존 **감지 기준** 화면(`/admin/atomos` 🔍탭)은 5열 표에 `robust z = (당일 − 동요일 중앙값)/(1.4826·MAD)` 같은 raw 수식이 박혀 비개발자·점주가 읽을 수 없었다.

요청: "기존 기능 고려하지 말고 과감하게" 재설계.

## 결정 (Decision)

두 surface를 백지에서 재설계하되, 백엔드 파이프라인(생명주기·CEO·슬롯·합성·발송)은 고정 토대로 두고 그 위 UI/UX를 재발명한다.

1. **전략 실행 보드** — 3탭+모달 폐기, 6상태 생명주기 칸반. **결정 열 강조** 채택: 상단에 결정 관문 2개(제안 대기=승인·보고 대기=발송)를 큰 카드로, 하단에 자동 단계(감지/진단/실행/발송됨)를 좁은 가로 흐름 레인으로 압축.
2. **검증 레이어 (근거성) — 풀스택 채택**: L1 출처·신선도 태그 + L2 계산식 펼치기 + L3 AI 주장별 `근거 ✓ / 근거 약함` 배지. L3는 백엔드(에이전트·합성)가 주장↔데이터 링크와 grounded 플래그를 emit + 서버측 보수적 sanity-check.
3. **감지 기준 규칙 카드** — raw 수식 표 → 평이한 한 문장 + 민감도 게이지 + **실시간 영향 미리보기**(캐시 점수 + 클라 재분류) + 예시 + 수식 펼치기.

## 대안 (Considered)

- 보드: 6단계 동등 칸반(흐름 전체 가시) / 압축+토글 → **결정 열 강조** 선택(운영자는 자동단계 개입 불가, "내 할 일"에 집중).
- 검증: 표시만(L1·L2) / FE우선·백엔드 점진 → **풀스택(L1+L2+L3)** 선택("AI가 지어냈는지" 판별이 핵심 가치).

## 근거 (Rationale)

근거성(데이터 뒷받침) = 콘솔이 "사용가치 없음"에서 벗어나는 핵심 차별점. 칸반 결정 열 강조 = 운영자 시선을 관문에 모음. 영향 미리보기는 `sales_items` 101만행 statement_timeout 위험 때문에 라이브 재집계 대신 캐시 점수 클라 재분류로 해결.

## 결과 (Consequences)

- FastAPI: 진단·합성 출력에 근거 메타(VerifiedClaim) 부착, 감지 점수 EP, 감지 raw 입력 persist.
- 4슬라이스 독립 출하: 보드 → 검증상세(L1/L2) → 감지 규칙카드 → L3 근거연결(최대 위험·마지막).
- 보안: read-only 신규 EP만, 무인증 디퍼드 정책 유지(send/auth 새로 안 염).
- 구현은 git worktree(병렬 세션 공유 리포).

정본 설계: hbs-dashboard `docs/superpowers/specs/2026-06-22-atomos-console-detection-redesign-design.md` (커밋 `17719c4`).

## 출처(원본)

- hbs-dashboard/docs/superpowers/specs/2026-06-22-atomos-console-detection-redesign-design.md
