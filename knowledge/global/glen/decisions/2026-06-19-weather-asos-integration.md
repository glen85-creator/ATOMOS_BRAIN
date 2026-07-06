---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 기상청 ASOS 과거관측 날씨 × 매출 연동 (감지 근거성)"
tags: [domain/hbs-dashboard, domain/detection, status/active, type/adr, glen-wiki, type/decision]
---
# ADR: 기상청 ASOS 과거관측 날씨 × 매출 연동 (감지 근거성)

## 맥락
글렌 전략 전환(하나씩 원인부터 검증)의 연장선 — 감지(매출 급락/이상)가 **데이터 근거**를 갖추려면 외생 변수를 분별해야 한다. 첫 외생 변수 = 날씨("그날 폭우/한파였나"). 매출 급락이 진짜 이상인지, 날씨 탓인지 AI가 구분하게 하는 것이 목적.

## 결정
- **API = 기상청 지상(종관) ASOS 일자료** (공공데이터포털 `getWthrDataList`, EP `apis.data.go.kr/1360000/AsosDalyInfoService`). 무료 `KMA_SERVICE_KEY`(동의·심사 불요), env 보관.
- **과거 소급**이 목적이므로 ASOS(관측). 미래/실시간 수요예측은 별개로 **단기예보**(`VilageFcstInfoService_2.0`, nx/ny 격자, 같은 계정 별도 활용신청) — 차기 슬라이스.
- 응답 60+컬럼 중 **외식 관련 12컬럼만** 적재(sum_rn·avg/max/min_ta·snow_cm·avg_ws·max_ins_ws·avg_rhm·sun_hr·cloud·iscs).
- 코드: `weather_client.py`(fetch_asos_daily·_normalize·stn_for_store)·`weather_service.py`(weather_daily upsert)·`routes/weather.py`(`POST /weather/backfill`·`GET /weather/sales-correlation`). DB `weather_daily(stn_id, obs_date PK, …12)`.
- 매장→지점: PoC 하드 매핑 서울=108. 향후 위경도 최근접 ASOS/AWS 자동매핑.

## 근거 / 대안
- 대안: 유료 날씨 SaaS / 단기예보만 → ASOS가 무료·과거소급·관측치라 근거성에 적합. 단기예보는 미래 슬라이스로 분리.
- br_uid·90 EP 교체 같은 과한 리팩터 회피 — 신규 라우터 1개·기존 sales_closing 조인만.

## ⭐ 핵심 발견 (Railway egress)
에이전트 샌드박스(해외/데이터센터 IP)는 data.go.kr 403 차단당하지만, **Railway 서버는 정상 호출**(backfill 18행 적재 성공). → data.go.kr 연동 코드는 Railway에서 돌리는 것이 정답. (로컬/CI 검증 시 403은 환경 문제이지 키·설계 문제가 아님.)

## 결과 (라이브 E2E, 구로점 2026-06)
PR #40 머지·배포·env 설정 후: backfill 서울 108 6/1~18 18행 적재 → sales-correlation 구로점.
- 6/1~3 급락이나 **맑음** → 날씨 아님 = 신규 오픈 램프업.
- 6/7·6/14 **0원** = 일요일 휴무(영업 안 함).
- 6/8~6/17 정상(150~218만), 날씨 영향 미미.
→ 단순 급락 플래그(월평균×0.6)를 날씨로 **분별**하는 가치 입증. (6월 서울 건조해 비-매출 직접 링크는 약함.)

## 슬라이스 2 (2026-06-20, FastAPI#41 · hbs#55/#56)
운영자 면 연동 완료: 매출 달력(MonthlyCalendarCard) 셀 우상단에 날씨 아이콘+최고기온(폭염/강풍 배지·툴팁). BE `weather_classify.py`(순수 결정론: 하늘 4단계 전운량 + 강수 + 특이배지) → `monthly-calendar` EP `weather` 필드(실패 격리) → FE `weatherDisplay.ts`. 매일 D-1 자동수집 Celery `collect_weather_daily`(06:10 KST). 4·5월 백필. 라이브 검증 통과(6/16 구름조금+폭염 등). 프로세스: brainstorming→spec→writing-plans→subagent-driven 2단계 리뷰. 환경 교훈: P4 churn으로 워크트리 HEAD 오염 → 독립 클론 + `git -C` 절대경로.

## 다음
감지 카드 날씨 배지(감지-통합) · 위경도 최근접 지점 자동매핑 · 단기예보(미래 수요예측). 메모리 `project_weather_asos`.

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/entities-technologies/FastAPI]]
- [[global/glen/entities-technologies/Supabase]]
- [[global/glen/entities-technologies/Railway]]

## 출처(원본)

- raw/meetings/claude-conversations/57256c3e-1a31-49a3-9065-6d95d7d9cd60.md
