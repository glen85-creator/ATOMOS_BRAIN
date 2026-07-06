---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 매출 capacity 시뮬레이션 (SP-A+C) 설계 결정
tags: [domain/hbs, domain/simulation, status/active, priority/high, glen-wiki, type/decision]
---
# 매출 capacity 시뮬레이션 (SP-A+C) 설계 결정

## 맥락 (Context)

글렌 요구: **매출 시뮬 vs 실제 매출 비교로 매출 목표를 세운다.** 매장의 물리·운영 변수(평수·테이블·좌석·회전율·객단가·객수·조리플로우·기물·인력·주방 throughput)를 모델링해 시간당 최대 판매수량·판매액을 산출하고, 실적이 못 미치면 어느 항목이 병목인지 가린다.

핵심 통찰: 기존 매출 시뮬 자산(점주용 `/dashboard/price-sim`, 본사용 `/dashboard/hq-sim`)은 **전부 "수량 고정" 가정** 하에 가격·원가·믹스 → 공헌이익만 본다. 즉 **수량/capacity 차원을 의도적으로 비워둠**. 이 결정은 그 빈 차원을 채운다 (중복 아님·보완).

거대 시스템이라 6개 하위 프로젝트(SP-A~SP-F)로 분해. 이 결정 = 토대 **SP-A(물리모델) + SP-C(좌석 capacity)** 만, PoC = **청년38국수 구로점 1매장**.

## 라이브 데이터 검증 (2026-06-23, Supabase MCP)

⚠️ 선행 hq-sim 설계 문서(2026-06-06)의 데이터 갭 진단이 일부 **stale**임을 실측으로 정정:

- **영수증/품목 timestamp 완비**: `sales_bills.bill_ordered_at` 78.2만행 · `sales_items.item_ordered_at` 116.9만행 (150매장·6개월·100% 실제 시각). → 2026-06-06 문서의 "bill_table_no 불가·시간대 데이터 없음"은 폐기. throughput/피크/capacity 모델링 가능.
- **혼합형 매장**: dwell(`bill_paid_at`−`bill_ordered_at`) 중앙값 ≥10분 ~28매장(dine-in), <1분 ~51매장(퀵서비스, 주문≈결제). → 회전율·식사시간은 **dine-in 매장만 측정 가능, 퀵서비스는 가정**. 구로점=퀵서비스(0.7분).
- **채널 분할 컬럼 신설**: `sales_closing.{dine_in,takeout,delivery}_{count,amount}` 존재(2026-06-06 "채널 분할 불가"도 정정). 단 **구로점은 전부 0**(미적재).
- **신뢰도**: `sales_bills`(거래수·금액·시각) 신뢰 / `sales_closing.rep_sales_count`(객수) 만성 과소수집([[global/glen/decisions/2026-06-20-pos-sales-reconcile]]). 매출은 두 소스 정합(구로점 ₩20.98M ≈ 1,639건×₩12,879).
- `store_master_v2.seat_count` 308중 130개만 채워짐, 구로점 NULL → 에디터 입력 필요.

## 결정 (Decision)

1. **포지셔닝**: capacity 시뮬 = 기존 시뮬이 비워둔 수량/물리 천장 차원. 선형 시뮬의 "객수 무한→매출 무한"에 물리 천장 부여.
2. **2D 에디터 (3D 보류)**: 점주가 테이블/좌석을 2D로 배치(드래그)·식사시간/회전율 가정 입력. 좌표는 capacity 수학엔 불필요하나 SP-D(주방 동선)·SP-E(인력 존) seam으로 저장. 3D는 모델링력 동일·빌드비용↑이라 보류.
3. **데이터 모델 A2**: 신규 `store_layout`(매장 1:1, 가정값+측정캐시+캔버스) + `store_table`(테이블별 좌석·타입·x/y/w/h), RLS fail-closed. `store_master_v2`는 마스터 SSOT라 오염 회피 — 시드로만 읽음.
4. **capacity 엔진 = 팀(party) 단위**: 천장(`party_slots×max_turns×util`)·타깃(회전율 가정)·실적(`bills_day×dine_ratio`) 3선 + 좌석효율(부차, `avg_party`로 인원 로스) + **병목 1차 분류기**(수요 제약/좌석 제약/주방 의심, 시간대 피크 분석). 단위 일관성 위해 좌석(인원)이 아닌 팀 단위 채택 — 매출·영수증이 팀 단위라 데이터 정직.
5. **근거성(측정/가정 배지)**: 입력별 measured/assumed 표기. 구로점은 객단가=측정, 회전율·식사시간·dine-in비중=가정. ([[global/glen/decisions/2026-06-22-atomos-console-detection-redesign]]의 검증 레이어 철학과 일치)
6. **API** `/api/sim/capacity/*` (기존 `/api/sim/*`·`/api/hq/sim/*`와 분리), 전부 FastAPI 경유.

## 결과 (Consequences)

- 구로점 PoC 기대 결과: 좌석 천장 ≫ 실적 → **"좌석은 병목 아님"** 자동 도출 → 수요/주방으로 화살표(1차 분류기 가치 입증). 즉 이 모델의 산출물은 "증석하라"가 아니라 병목 분류기.
- **측정 회전율 분기 미발현**: 구로점 퀵서비스라 측정 회전율 도출 불가(가정만). 하이브리드 측정 분기 데모는 dine-in 매장 필요(엔진은 지원).
- 후속 = SP-D(조리플로우·기물)·SP-E(인력 시프트)·SP-F(throughput 솔버·마케팅 연결), spec §9 분해. 별도 plan.
- 보안: `PUT layout` 쓰기 EP는 실 멀티유저 전 `require_role` 선결(현 dashboard EP 무인증 디퍼드 보안 연장선).

## 산출물

- Spec: `hbs-dashboard/docs/superpowers/specs/2026-06-23-sales-capacity-sim-design.md` (커밋 `df6a85a`)
- Plan: `hbs-dashboard/docs/superpowers/plans/2026-06-23-sales-capacity-sim.md` (14 Task, 커밋 `71993b1`)
- 브랜치: `feat/capacity-sim` (워크트리 `~/hbs-dashboard-capsim`, origin/main 06582f8 기반), 미푸시·미구현(계획까지).
- 방법론: superpowers brainstorming(5섹션 합의·인라인 목업) → writing-plans(TDD 14 Task).


## 2026-06-24 — UI/UX 개편 (후속 결정)

초기 SP-A~F는 기능 우선이라 한 화면에 분석범위·배치편집·조리스텝·진단·목표를 좌우 2단으로 모두 노출 → 글렌 "너무 복잡·용어 어려움·박스 큼" 피드백. 결정: (1) 2탭 분리(현황·목표 / 매장 설정) — 편집은 가끔 하는 작업이라 기본 화면에서 빼고 요약 우선. (2) 사용자 문구 전수 쉬운 말 + 내부 코드명(SP-D 등) 제거 — 비개발 점주/운영진 대상. (3) 편집 캔버스 전체폭 + 논리 캔버스 확대(1000×620)로 박스 다수 수용. 순수 프론트 개편(계산·API·DB 불변). 기존 저장 배치(canvas_w=360)는 코드 자동 마이그레이션 대신 prod 재시드로 처리(YAGNI). 브랜치 feat/capacity-sim-ui, 로컬 5173 반영, prod 배포 보류(검토 중).


## 2026-06-24 15:31 — UI 현대화 Phase1 (후속 결정)

v1 개편 후 "촌스럽다·매장별 불가·저장 위치·컨트롤 불편" 피드백. 핵심 결정: (1) 신규 UI 라이브러리(shadcn/Tailwind) 도입 대신 **이미 있는 인하우스 디자인 시스템(components/ui + Sneat 토큰 + lucide) 재사용** — capacity-sim이 그걸 안 써서 촌스러웠던 것이 근본 원인. (2) 매장별은 전역 useSelectionStore(st_uid·POS축)가 아니라 **costApi.stores(st_id·master축, 원가 기능과 동일)** 사용 → 백엔드 무변경. (3) 2단계 분리: Phase1=프론트 현대화+매장별+레이아웃 재배치+모던 컨트롤, Phase2=홀/주방 영역(zones·백엔드). 로컬 5173 반영, prod 배포 보류.


## 2026-06-24 16:15 — 통합 배치 에디터 Phase2 (후속 결정)

Phase1 현대화 후 에디터 UX 피드백. 결정: (1) 좌석/주방 레이어 탭을 없애고 한 캔버스 통합(홀/주방은 탭이 아니라 영역으로 구분). (2) 홀/주방 영역은 드래그 분할선(축+위치) 모델, 저장은 우선 localStorage(임시) — 백엔드 zones는 prod 배포 필요라 후속 이관. (3) 항목 편집은 캔버스 하단 인스펙터 대신 클릭한 항목 옆 플로팅 팝업. (4) 박스 기본 크기 축소 + 구로점 시드 데이터 비우고 1000×620 리셋(빈 화면에서 직접 배치). (5) 페이지 폭 넓힘(min(1600,95vw))+현황·목표 2열. 100% 프론트+1회 데이터, 백엔드 코드 무변경. 로컬 5173 반영, prod 배포 보류.


## 2026-06-24 — SP-G DES 병목 시뮬 (후속 결정·배포·라이브)

글렌 질문: **"실제 과거 매출 데이터를 대입해 점=고객을 시뮬레이션 돌려 병목을 찾아낼 기술이 있나?"** → 답 = **이산사건 시뮬(Discrete-Event Simulation, DES)**. 기존 SP-A~F capacity 엔진은 station min-throughput **해석적 근사**(시간당 평균)인 반면, DES는 실제 도착 타임스탬프(`bill_ordered_at`)를 그대로 리플레이해 **순간 동시성·대기 큐·balk(못 받은 손님)**까지 잡는다.

결정·구현:
1. **엔진 = SimPy 대기행렬 네트워크** (`app/services/des_sim.py`, 순수·결정적). 파티=영수증 entity, 좌석/주방 스테이션=`simpy.Resource`. 파티가 좌석 점유(만석+대기>patience면 balk) + 동시에 아이템을 레시피대로 주방 스테이션에 라우팅. 미커버 메뉴는 `(가정)` 기본 스테이션. 가동률=busy/(활동구간×용량). pytest 5/5.
2. **EP** `POST /api/sim/capacity/{st_id}/des`: 실데이터 파이프라인 `sales_bills`→`sales_items`(bill 그룹)→`recipe_cooking_step`(전역)→`equipment_master`. arrive_sec=`_epoch(ordered)-midnight`, dwell=`paid-ordered`.
3. **프론트** `DesPanel.tsx` = CapacitySim 3번째 "병목 시뮬" 탭(병목 verdict·자원별 가동률 바·시간대 대기큐 차트·통계·정직성 caveat).
4. **적대적 4-렌즈 리뷰 → 실결함 2 수정**(엔진은 8차원 no-blocker): ① **PostgREST 기본 1000행 truncation** — 실측 최대 store-day가 items 1501개라 이미 초과 → 명시적 `limit`. ② **midnight 타임존 미고정** — `bill_ordered_at`은 timestamptz(+00 앵커, KST 벽시계가 +00 라벨)인데 midnight은 naive(서버 로컬 tz) → `midnight`을 `+00:00`으로 고정해 **서버 tz 무관하게 정확**. + 정직성 caveat(결제시각 null·좌석 미설정).

**배포·검증**: FastAPI [#63](https://github.com/glen85-creator/FastAPI/pull/63)→main `f440b10`(Railway·simpy), hbs [#69](https://github.com/glen85-creator/hbs-dashboard/pull/69)→main `39b3cef`(Vercel), GitHub API squash 머지(글렌 승인). **prod 데이터 E2E**(로컬 EP를 prod Supabase로 직접 호출, 구로점 2026-06-18 180건): peak=**12시(점심)·13·11시**로 한국 점심러시가 정확히 잡힘 = tz 앵커 검증(틀렸으면 새벽 2-4시), 병목="기타(가정)"(레시피 커버리지 12%), 신규 caveat 발화 검증.

방법론: brainstorming(병목 진단+1일 리플레이 2모드 합의) → writing-plans(8 Task) → 인라인 구현 → 4-렌즈 적대 리뷰 → 배포. ⚠️구로점은 좌석·기물 미설정이라 풍부한 주방 병목 데모는 레이아웃 재시드 후속. PUT/DES EP 무인증=디퍼드 보안 백로그.


## 2026-06-25 — 조리 스텝 인력 연결: 기능 역할 기반 2계층 (후속 결정·배포)

글렌 검토 요청: 조리 스텝 담당이 자유 텍스트라 특정 직원의 업무 부하·1인당 공헌이익을 못 구한다(+단계 복제·총 소요시간 필요). 핵심 모델링 충돌: **`recipe_cooking_step`은 메뉴 단위 전역**(모든 매장 공유)인데 **`staff_master`(직원)는 매장 단위**(시급·계약이 사람·매장마다 다름) → 전역 레시피에 특정 매장의 개인을 직접 못 박음.

결정 = **2계층**: (1) 레시피 스텝 담당 = **기능 역할**(조리/전처리/토핑/홀/카운터/세척) — 전역 조인키. (2) 매장 직원(기존 인력비용 화면 `Admin/LaborCosts.tsx` — 직원 마스터 시급·계약·근무시간 CRUD + 월별 4대보험 자동산출, 이미 존재하나 데이터 비어있음)에 그 **기능 역할을 부여**(SP-E) → 분석이 역할로 매장별 직원·시급·계약을 연결해 업무 부하도·1인당 공헌이익 산출. 스텝→개인 직접지정안은 기각(레시피를 매장별로 분리해야 하는 큰 구조 변경). ⚠️ `staff_master.role_type`은 고용형태(정규/알바/일용/매니저/점주)지 기능 역할이 아님 → 기능 역할은 별도 축.

이번 슬라이스(배포 완료, hbs PR #71→main `7ec224d`, Vercel): 단계 복제·삭제·총 소요시간 + 담당 기능역할 드롭다운(`laborRoles.ts` 공유 상수, code를 기존 `staff_role` TEXT에 저장·마이그레이션 없음·기존 비표준값 보존). 100% 프론트. spec `hbs/docs/superpowers/specs/2026-06-24-cooking-step-role-labor-design.md`. SP-E로 분리: staff_master 기능역할 필드 + 역할 노동시간(스텝×메뉴 판매량)×시급/인원 → 부하·1인당 공헌이익. `LABOR_ROLES`가 두 계층 조인키.


## 2026-06-25 — SP-E 인력 부하·1인당 공헌이익 (2계층 실현·배포·라이브)

위 2계층 결정을 구현. brainstorm 확정: 통합 대시보드(부하+1인당 공헌이익)·겸직 비중 모델·입력은 인력비용(LaborCosts)/분석은 capacity 새 "인력" 탭·월 단위.

★**아키텍처 = DRY**: 판매량·공헌이익은 **기존 메뉴 엔지니어링 재사용**(`/api/dashboard/engineering`: monthly_qty·blended_contribution·cost_status — 백엔드 재구현 안 함), 계산 엔진은 **FE 순수함수 `laborMath.ts`**(vitest), 백엔드는 **thin config**(데이터 조립만, 계산 없음). 마이그 013 `staff_role_alloc`(staff_id·role_code·weight·PK·RLS).

산식: demand_h[role]=Σ(스텝 duration×월판매량)/3600 · supply_h[role]=Σ(month_hours[주당×4.345]×weight) · util=demand/supply(공급 0이면 null) · 직원별 busy=역할 공급비중 분배 · CM=Σ(공헌이익×qty, cost_status=registered만) · 1인당=CM/인원 · 인당생산성=CM/노동시간 · 인건비대비=CM/월인건비 · 역할 공헌배분=노동시간 비중.

배포: BE [FastAPI #65](https://github.com/glen85-creator/FastAPI/pull/65)→main `fe80e4b`(Railway; cost.py alloc CRUD + capacity_sim labor-config EP) · FE [hbs #72](https://github.com/glen85-creator/hbs-dashboard/pull/72)→main `e56c283`(Vercel; laborMath·LaborPanel·LaborCosts 역할입력). 실행=**subagent-driven**(컨트롤러가 마이그/워크트리/커밋/배포, 구현 subagent 5개가 코드+빌드/테스트, Task별 리뷰)+4-렌즈 적대리뷰(반영: `_validate_staff_id` sibling 일관성·정직성 caveat 3종). prod E2E: 배포 labor-config EP가 구로점 시드직원 2명 조인 정상 반환(month_hours=주당×4.345·allocs·labor_cost null→시급추정 폴백+caveat) 확인 후 테스트직원 삭제(staff_master 0 복원).

⚠️ 구로점 레시피 역할이 레거시 "직원/알바"(role code 아님)·staff_master 비어있음 → 실사용은 조리스텝 역할 갱신 + 직원·역할 입력 후. 후속: 시간대 시프트·weight 합 검증 강화·require_role(디퍼드 보안). spec/plan `hbs/docs/superpowers/{specs,plans}/2026-06-25-capacity-sp-e-labor-analysis*`.

## 관련

- [[global/glen/decisions/2026-06-20-pos-sales-reconcile]]
- [[global/glen/decisions/2026-06-22-atomos-console-detection-redesign]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-23-sales-capacity-sim-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-23-sales-capacity-sim.md
