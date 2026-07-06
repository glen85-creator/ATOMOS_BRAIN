---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 종합 대시보드 경쟁 상권 카드 + 실행 허브 제거"
tags: [domain/hbs-dashboard, domain/sangwon, domain/detection-groundedness, status/active, type/adr, glen-wiki, type/decision]
---
# ADR: 종합 대시보드 경쟁 상권 카드 + 실행 허브 제거

## 맥락
감지 근거성(detection groundedness)의 **2번째 외생축 = 경쟁/입지**(1번째 = 날씨). "매출 부진이 경쟁 포화 탓인지" 데이터로 보여주려 상권 PoC를 실기능화. 동시에 종합 대시보드의 구식 **실행 허브(ActionHubPanel)**가 ATOMOS 콘솔과 기능 중복 → 그 자리를 카드로 교체.

## 핵심 결정
1. **사전계산 캐시(A안).** 상권 API는 느리고(매장당 517건 파싱) 과밀 등급은 전매장 분포를 요구 → 월1회 배치가 전매장 계산해 `store_competition` 캐시 적재, 대시보드는 캐시만 읽어 즉시 렌더. (라이브 호출·반경 토글은 범위 밖.)
2. **동종 직접경쟁 TOP5 = 거리순.** 상권 API엔 매출·리뷰 없음 → 인기순 불가, 거리순(haversine)만 데이터 근거. 동종 = 면류 키워드(국수·칼국수·우동·냉면·라면·쌀국수·짜장·짬뽕 등; 분식·양식면 제외=오탐방지).
3. **과밀 등급 = 전매장 백분위 4단계**(초과밀≥75/과밀≥50/보통≥25/한산). 순위 기반이라 분포 쏠림에 안정적.
4. **자기 매장 제외**(E2E서 발견): 상권 API가 자기 매장도 반경 내 업소로 반환 → 동일좌표(0m) direct에서 제외.
5. **실행 허브 통째 제거**: 실행제안=콘솔 대체·목표갭=타 카드 중복·체크리스트=콘솔 실행스텝 대체. `StrategyAddButton`·`strategyApi`·`RecentStrategyImpactCard` 보존, 고아 checklist/action-rec FE 정리.

## 솔루션 (FastAPI#51·#52, hbs#57·#58)
- `store_competition`(st_uid·competitor_count·by_category·direct_count·direct_top5·grade·percentile·computed_at) + `sangwon_competition.refresh_competition` + `tasks.refresh_competition` 월1회 비트 + `POST /sangwon/refresh-competition`.
- `GET /sangwon/competition-card?st_uid=`(캐시·no_coord/pending) + FE `CompetitionCard.tsx`(매출 달력 옆).

## 결과
라이브 E2E: 구로 음식점 517·초과밀·동종 28(고향밀면 44m·국수 164m·짬뽕·쌀국수, 분식 오탐 0), 독산 456·초과밀. 전매장 225 캐시. 자기매장 제외 검증(독산 0m 제거).

## 프로세스
brainstorming(카드방향·동종범위·캐시 아키텍처·실행허브 제거 전체검토)→spec→writing-plans→subagent-driven(2단계 리뷰). 코드리뷰 반영: 동종 키워드 오탐 제거·limit run 등급 미기록·자기매장 제외(E2E 발견).

## 다음
경쟁밀도 감지 통합(배지)·인기/규모 랭킹(네이버·카카오)·반경 토글·브랜드별 동종 키워드.

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/entities-technologies/FastAPI]]
- [[global/glen/entities-technologies/Supabase]]
- [[global/glen/decisions/2026-06-19-weather-asos-integration]]

## 출처(원본)

- FastAPI#51·#52 / hbs#57·#58 (2026-06-21)
- spec: ~/FastAPI/docs/superpowers/specs/2026-06-21-sangwon-competition-card-design.md
