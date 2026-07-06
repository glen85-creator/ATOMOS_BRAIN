---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 멀티 브랜드 POS(Metacity) 연동"
tags: [domain/backend, domain/atomos, status/done, priority/high, glen-wiki, type/decision]
---
# ADR: 멀티 브랜드 POS(Metacity) 연동

## 맥락 — 글렌 요청

ATOMOS "데이터 근거성" 테스트를 위해 매장 하나(**청년38국수 구로점** `st_uid=I26052800001`, `br_uid=B26052700001`)의 POS 데이터를 적재해야 함. 기존 POS(Metacity) 연동은 **국수나무 단일 브랜드 하드와이어**. 글렌: "기존 POS 스케줄러에 신규 브랜드도 **공통으로** 들어가게."

## Phase 1 조사

- 라이브 자격증명 검증: 키 + br_uid=B26052700001 → `storeInfo.asp` RtnResult `000`, 매장 1개(구로점). 매출 데이터 2026-06부터(05-15 이전 없음) = **신규 매장 ~3주** → 매출-급락 z-score 감지 안 뜸(같은 요일 ≥5주 필요).
- 단일 브랜드 하드와이어 = `metacity_client.py`(전역 `settings.METACITY_BR_UID`/`API_KEY`) + `sync_service.py`(br_uid 기록). 스케줄러 `daily-sales-sync` beat 02:00 KST → `_daily_sync_async`가 `sync_stores()` 후 `stores` 순회.

## 결정 (brainstorming, 글렌 승인)

- 자격증명 저장 = **env JSON 맵** `METACITY_BRANDS`(Railway 시크릿). 키는 코드·DB 미진입.
- 테스트 타깃 = 청년38국수(작은 것부터 하나씩). 신규 브랜드는 **기존 02:00 공통 스케줄러 자동 합류**(새 beat 없음).

## 구현 (FastAPI#39, migration 0)

- 신규 `pos_brands.py`: `BrandCreds`(api_key `field(repr=False)` 마스킹) + `get_brands()`(env JSON 파싱 + 레거시 단일 env 폴백·br_uid 중복제거·never-raise) + `get_brand_creds`.
- `metacity_client.fetch_*(creds, …)` 호출별 br_uid/api_key 주입.
- `sync_service`: `_creds_for_store`(store→br_uid→creds)·creds 스레딩·`sync_all_stores()`·`_log` br_uid.
- `sales_tasks`/`routes.sync`: `sync_all_stores()` 전환 + ValueError 비재시도.
- 레거시 폴백으로 국수나무 무중단.

## 6차원 적대 리뷰 (워크플로 — ultracode)

스펙·하위호환·creds해결·멀티브랜드 일일·보안·회귀 → **16건 중 13 반증, 확정 3 반영**(블로커 0):
1. **minor** — manual/bulk task가 영구 ValueError(미등록 브랜드)를 재시도 → 비재시도(에러 반환)로.
2. **nit(보안)** — `BrandCreds` auto-repr이 api_key 노출(잠재) → `field(repr=False)`(스펙 "키 로그 마스킹" 목표 직결).
3. **nit** — `get_brands` 호출마다 JSON 재파싱 → skip(1-2 브랜드 무영향, 메모이즈 staleness 위험).

## 운영(글렌 수동)·잔여

- 브랜드 추가 = Railway env `METACITY_BRANDS` 설정(**FastAPI web + Celery worker 둘 다**) → 재배포 → `/sync/stores` → `/sync/bulk` 백필 → 검증. Railway CLI 미설치.
- 일일 "누락 날짜" 탐지가 글로벌(sales_closing any-row) — steady-state 정상, 중간 합류 갭은 bulk_sync로 보완(known limitation, 별도 follow-up).

## 교훈

- 단일→멀티 파라미터화: 전역 settings 직접참조를 호출별 주입으로 전환 + DB(store.br_uid)에서 creds 해결 = task/route 시그니처 무변경(호출부 안 깨짐).
- 라이브 자격증명을 read-only로 먼저 찔러 검증(데이터 유무·이력 깊이까지) = 신규 매장 한계(매출감지 불가)를 구현 전에 발견.
- 적대 리뷰가 "현재 무해하나 잠재 leak"인 dataclass repr 같은 footgun 포착.

다음: 청년38 백필(env 설정 후) → AI 데이터 근거성 점검(글렌 발의).

## 관련

- [[global/glen/decisions/2026-06-18-detection-toggle-consistency]]

## 출처(원본)

- raw/docs/FastAPI/docs/superpowers/specs/2026-06-18-pos-multibrand-design.md
