# VISION AI 매장 데이터 스키마 설계서 — 설치 전 데이터 모델 정본

> **버전**: v0.1 (2026-07-09 — 설치 전 설계 초안) / **상태**: 🟡 검토·논의용 (미승인, 마이그레이션 미작성)
> **위상**: 외식 매장 3개 구역(키오스크/홀/주방)에 Vision AI 설치 시 **추출·저장할 데이터의 테이블 스키마 단일 진실 원천(SSOT)**.
> 실제 테이블은 FastAPI(Railway) → **Supabase(Postgres)** 에 생성되며(`supabase/migrations/2026-07-09-vision-*.sql`), 대시보드(hbs-dashboard)와 ATOMOS 브레인이 이를 소비한다.
>
> **이 문서가 인용하는 기존 확정(재설계 아님)**:
> - `FastAPI/supabase/migrations/2026-06-21-store-competition.sql` — 자연키 캐시 테이블 관례(PK/jsonb/computed_at/한글 코멘트)의 템플릿 ✅
> - `FastAPI/supabase/migrations/2026-06-10-staging-tables-v2.sql` — 고빈도 이벤트 로그 PK(bigint identity + UNIQUE) + RLS 관례 ✅
> - `FastAPI/supabase/migrations/2026-06-09-atomos-settings.sql` — `touch_updated_at()` 트리거 관례 ✅
> - `FastAPI/app/services/sync_service.py` (`_sync_bills` 255–291 등) — POS 영수건 테이블(`sales_bills`)의 실제 컬럼 원천 ✅
> - `FastAPI/app/api/routes/capacity_sim.py` (`_pos_uid` 123–125) — `st_id → store_master_v2.pos_st_uid` 해석 로직 ✅
> - 개인정보위 「고정형 영상정보처리기기 설치·운영 가이드라인」, 개인정보보호법 제15·18·23·25조, 근로자참여법 제20조 ✅
>
> **표기**: ✅ 기존 확정 인용 / 🟡 본 문서 신규 제안(승인 필요) / 🔴 미결(§10, 사용자·법무 결정 필요)

---

## 0. 이 문서가 해결하는 것

Vision AI를 매장에 설치하기 **전에**, "무엇을 촬영·추론해서 → 어떤 테이블에 → 어떤 컬럼으로 남길지"를 확정한다. 하드웨어를 사기 전에 데이터 계약을 먼저 못박아, 설치 후 재작업·법 위반·데이터 손실을 방지한다.

| 문제 | 해소 위치 |
|---|---|
| 구역별로 무슨 데이터가 나오고 어디에 저장되는지 미정의 | §3–§6 구역별 테이블 스키마 |
| "통계 vs 개인정보" 경계가 모호 → 법 위반 리스크 | §2-1 프라이버시 3원칙 + §9 법적 분류 |
| 키오스크 인구통계를 영수건에 어떻게 잇나 | §4 + §8 POS 매칭(실제 `sales_bills` 기반) |
| 매장키(st_id vs st_uid) 혼선 | §2-2 공통 표준 + `store_master_v2.pos_st_uid` 해석 |
| 구역 스키마가 따로 놀아 조합이 안 됨(기기/직원 키 불일치, 단위 드리프트) | §2-2 크로스존 표준 (12-에이전트 검증 반영) |
| 동의·보유기간·파기 기록 등 법정 증빙 테이블 부재 | §7 컴플라이언스 지원 테이블 |
| 대시보드/ATOMOS까지의 소비 계약 미정의 | §8 데이터 흐름 |

> **근거 신뢰도**: 본 설계는 FastAPI 리포를 직접 열람한 그라운딩(실제 마이그레이션·`sync_service.py` 컬럼) + 구역별 설계 + 적대적 검증 + 완결성 비평(총 12개 병렬 에이전트)의 종합이다. 초안 1차에서 발견된 결함(홀 영수건 결합의 익명성 붕괴, 기기 레지스트리 고아화, 주방 익명 롤업의 재식별 가능성 등)은 본 문서에 이미 반영·수정되어 있다.

---

## 1. 개요·목적·범위

### 1-1. 3개 구역과 목적

| 구역(zone) | 설치 위치 | 추출 목적 | 개인정보 등급 |
|---|---|---|---|
| **kiosk** | 매장 밖/입구 키오스크 | 주문 시점 고객 추정 인구통계(연령/성별/일행수)를 **영수건에 매핑**. (통행량 카운팅 아님) | 🔴 영수건 결합 시 **개인식별가능정보** |
| **hall** | 매장 안(홀) | 테이블 점유 세션·회전율·**익명** 인구통계 집계 | 🟢 익명(무연결 시) / 🔴 영수건 연결 시 개인정보 |
| **kitchen** | 주방 | 플레이팅/토핑 품질 + 구역 활동 + **직원 개인 단위** 근무(출근/스테이션 체류) | 🔴 개인 추적 = **생체인식정보(민감정보)** |

### 1-2. 범위
- **포함**: 3구역 데이터 테이블 스키마(컬럼/타입/키/인덱스/RLS), 공통 차원, 컴플라이언스 지원 테이블, 데이터 흐름, 법적 분류.
- **제외(별도 단계)**: 실제 SQL 마이그레이션 파일, 엣지 추론 코드, 대시보드 UI, 하드웨어 BOM(별도 문서).

---

## 2. 설계 원칙

### 2-1. 개인정보·노무 3원칙 (🟡 합의 필요)

1. **영상 미저장 · 통계값만** — 엣지(온디바이스)에서 추론 후 원본 프레임·얼굴 이미지·**얼굴 특징 템플릿(임베딩)은 어떤 컬럼에도 저장하지 않는다**. 클라우드로는 익명 추정값(분포/카운트)만 전송. (CCTV 통계 예외 — 개인정보보호법 제25조제1항제6호)
2. **결합=개인정보 전환** — 추정 인구통계를 **특정 영수건/개인에 연결하는 순간** 통계 예외를 벗어나 개인(식별가능)정보가 된다 → 동의·고지 확보 + 분리 저장 + RLS + 보유기간 관리가 강제된다.
3. **주방 개인추적 = 민감정보** — 얼굴로 특정 직원을 식별하면 생체인식정보(시행령 제18조제3호, 법 제23조). **별도 명시적 동의 + 근로자참여법 제20조 노사협의/근로자대표 협의**를 전제로만 활성화한다. (§9 상세)

### 2-2. 크로스존 공통 표준 🟡 (정합성 — 12-에이전트 검증 반영)

구역들이 따로 설계되면 조합이 안 되므로, 아래를 **전 구역 단일 규칙**으로 못박는다.

| 항목 | 표준 | 근거 |
|---|---|---|
| **매장키** | `st_uid text` (조인 대상 `stores.st_uid`). 원본 `st_id text` 병행 보관. **`st_uid`는 nullable** — `pos_st_uid` 없는 매장(no_pos_uid)은 익명 수집만. `store_id` 금지 | 그라운딩: `st_id ≠ st_uid`, `store_master_v2.pos_st_uid` 해석 필요 |
| **브랜드키** | `br_uid text` (nullable) — 전 fact/rollup 공통 포함(브랜드 필터) | `sales_bills.br_uid` |
| **기기키** | 모든 테이블은 카메라/엣지를 **`device_code text`** 로 참조(논리 FK→`vision_device`). `kiosk_id/camera_id/camera_device_id` 혼용 금지 | 검증: 기기 레지스트리 고아화 방지 |
| **직원키** | **`staff_code text`** 로 통일(논리 FK→`vision_staff`). `staff_id` 명칭 금지 | 검증: vision_staff split-brain 방지 |
| **PK 패턴** | 저빈도 차원/롤업 캐시 = **자연키 복합 PK**; 고빈도 이벤트 로그 = **`id bigint GENERATED ALWAYS AS IDENTITY` + UNIQUE(자연키)** | `store_competition` / `stg_*` |
| **시각** | `timestamptz` (plain timestamp 금지). 이벤트 적재 = `loaded_at`; 롤업 캐시 = `computed_at`; 가변 차원 = `updated_at` + `touch_updated_at()` 트리거 | `atomos-settings.sql` gotcha |
| **분포 컬럼** | `age_dist`/`gender_dist` = **정수 카운트** 저장(예 `{"20s":2}`), `jsonb not null default '{}'::jsonb`. 비율은 읽기 시 산출 (분수·카운트 혼용 금지) | 검증: fractions vs counts 드리프트 |
| **시간 단위** | **초(seconds) 통일** (`*_seconds`). 분(minutes) 금지 | 검증: 단위 드리프트 |
| **매칭 방식 enum** | `match_method ∈ {'table_time','time_window','manual','unmatched'}` (단일 어휘) | 검증: time_only/time_window 드리프트 |
| **비율 컬럼** | `numeric`, **CHECK (col BETWEEN 0 AND 1)** 강제 | 검증: 범위 CHECK 부재 |
| **POS 참조** | `sales_bill_id`는 **소프트 참조(하드 FK 미선언)** + 원본 매치키(`sal_ymd`,`match_sal_seq`,`pos_bill_table_no`) 병행. `sales_bills.id` 실제 타입 확인 전까지 FK 금지. `sal_seq` 단독 조인·`sales_items.id` 참조 금지 | 그라운딩: `sales_bills` DDL 부재, delete+insert |
| **RLS** | 개인(식별가능)정보 테이블 = `ENABLE ROW LEVEL SECURITY`(정책 없음 → service_role 전용). 순수 익명 롤업 = `store_competition`처럼 RLS 미적용(단 k-익명성 억제 적용) | `staging-tables-v2.sql` |
| **하이브리드 그레인** | 각 구역 = **팩트/이벤트 테이블 + 시간버킷 롤업 캐시** 2층 | 사용자 결정(Q2) |

---

## 3. 공통 디멘션

### 3-1. `public.vision_device` — 카메라/엣지 기기 레지스트리 (차원)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | 매장키(`stores.st_uid`). (st_id→pos_st_uid 해석 후 저장) |
| device_code | text | N | 매장 내 기기 고유 코드. **(st_uid, device_code) 자연키** |
| zone | text | N | CHECK (zone in **('kiosk','hall','kitchen')**) |
| device_type | text | Y | 'camera'/'edge_box'/'nvr' |
| label | text | Y | 운영자용 표시명(예: '홀 천장 1번') |
| location | text | Y | 물리 설치 위치·촬영범위 (CCTV 안내판/운영방침 근거) |
| status | text | N | DEFAULT 'active'. CHECK (status in ('active','inactive','maintenance')) |
| installed_at | timestamptz | Y | 설치/등록 시각 |
| decommissioned_at | timestamptz | Y | 철거/폐기 시각(보유기간 근거) |
| updated_at | timestamptz | N | DEFAULT now() + `touch_updated_at()` BEFORE UPDATE 트리거 |

- **PK** `(st_uid, device_code)` · **IDX** `(st_uid, zone)` · 개인정보 미포함.

### 3-2. `public.vision_staff` — 주방 개인추적용 직원 마스터 (차원, 민감)

> 얼굴 이미지·특징 템플릿(임베딩)은 저장 금지. 식별키(`staff_code`) + 동의 플래그만. 얼굴 특징 저장이 불가피하면 **암호화·분리 저장**(본 표 아님).

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| id | bigint IDENTITY | N | **대리 PK** (사번 재사용 시 이력 보존 위해 자연키 아님) |
| st_uid | text | N | 매장키 |
| staff_code | text | N | 사번/직원코드. **UNIQUE(st_uid, staff_code) WHERE active** |
| display_name | text | N | 표시명(이니셜/가명 최소화 권장 🔴§10) |
| role | text | Y | 주방 직무만(위생/안전/교육 목적). CHECK 권장. '홀서빙' 등 제외 |
| consent_biometric | boolean | N | DEFAULT false (opt-in). 생체(얼굴식별) 추적 동의 |
| consent_video | boolean | N | DEFAULT false (opt-in). 영상 추적 동의 |
| active | boolean | N | DEFAULT true. 재직 여부(동의와 독립) |
| updated_at | timestamptz | N | DEFAULT now() + 트리거 |

- **PK** `id` · **RLS** ENABLE(service_role 전용).
- ⚠️ 동의 취득일·철회 이력은 본 표가 아니라 **§7-2 `vision_staff_consent_log`** 에 남긴다(법정 증빙; 단일 `updated_at`로는 불충분 — 검증 반영).

### 3-3. `public.vision_settings` — Vision 전용 설정 (신규, 검증 반영)

전역 `detection_settings` 싱글톤과 별개로 Vision 파라미터의 집. 구역별 open-question("이 설정 어디 사나")을 해소.

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | 매장키. **PK(st_uid)** (전역 기본값은 별도 row 또는 null 정책 🔴) |
| quality_score_scale | text | N | DEFAULT '0-1' (품질점수 스케일 고정) |
| quality_pass_threshold | numeric | N | 합격 임계값. CHECK 0~1 |
| daypart_cutoffs | jsonb | N | `{"breakfast":6,"lunch":11,"dinner":17,"late":22}` 등 |
| business_day_cutoff_hour | int | N | DEFAULT 6 (심야 주문의 영업일 귀속 기준시) |
| bucket_seconds | int | N | DEFAULT 60 (롤업 버킷 폭) |
| k_anonymity_floor | int | N | DEFAULT 3 (집계 표시 최소 표본) |
| retention_days | int | N | DEFAULT 30 (PII 파기 기준일) |
| updated_at | timestamptz | N | DEFAULT now() + 트리거 |

---

## 4. 구역 A — 키오스크 (매장 밖/입구): 주문 인구통계 → 영수건 매핑

> 🔴 **법적 전제**: 인구통계를 영수건에 연결 = 개인식별가능정보. 고객 동의/고지 + `vision_kiosk_order` 분리저장·RLS 필요(§9).

### 4-1. `public.vision_kiosk_order` — 주문 시점 인구통계 이벤트 (팩트)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| id | bigint IDENTITY | N | 대리 PK |
| vision_event_uid | text | N | 엣지 이벤트 UID. **UNIQUE**(멱등 재적재) |
| st_uid | text | Y | 매장키(no_pos_uid면 null) |
| st_id | text | Y | 비전측 원본 매장 id(감사·재매핑) |
| br_uid | text | Y | 브랜드키 |
| device_code | text | Y | 발생 키오스크 단말(→vision_device) |
| captured_at | timestamptz | N | 추정 산출 시각(=주문 시도). POS 시간창 매칭 앵커 |
| sal_ymd | date | Y | 영업일(business_day_cutoff 적용 산정) |
| party_size | int | Y | 추정 일행수 |
| party_size_conf | numeric | Y | 신뢰도. CHECK 0~1 |
| age_dist | jsonb | N | 연령대 카운트 `'{}'` |
| gender_dist | jsonb | N | 성별 카운트 `'{}'` |
| detections | jsonb | N | 인원별 추정 상세(연령/성별 확률만, 얼굴·특징점 없음) `'[]'` |
| sales_bill_id | bigint | Y | 매칭 영수건 `sales_bills.id` **소프트 참조** |
| match_sal_seq | text | Y | 매칭 근거 원본 `sal_seq`(감사용, 단독조인 금지) |
| match_table_no | text | Y | 매칭 근거 `bill_table_no`(테이블오더 키오스크만) |
| match_method | text | Y | enum(§2-2) |
| match_confidence | numeric | Y | CHECK 0~1 |
| matched_at | timestamptz | Y | 매칭 확정 시각 |
| consent_basis | text | N | DEFAULT 'legitimate_interest'. CHECK in ('consent','legitimate_interest'). **CHECK (sales_bill_id IS NULL OR consent_basis IS NOT NULL)** |
| purge_after | date | Y | 파기 예정일(retention_days) |
| loaded_at | timestamptz | N | DEFAULT now() |

- **PK** `id` · **UNIQUE** `vision_event_uid` · **IDX** `(st_uid, sal_ymd)`, `(captured_at)`, `(sales_bill_id)` · **RLS** ENABLE(영수건 결합 PII).

### 4-2. `public.vision_kiosk_daypart` — 매장×영업일×시간대 롤업 (캐시, 익명)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| biz_date | date | N | **PK 구성** |
| daypart | text | N | **PK 구성**. CHECK in ('breakfast','lunch','dinner','late') |
| br_uid | text | Y | 브랜드 롤업 |
| order_count | int | N | DEFAULT 0 |
| matched_order_count | int | N | DEFAULT 0 (매칭률) |
| party_size_total | int | N | DEFAULT 0 |
| party_size_sample_count | int | N | DEFAULT 0 (평균 분모 = party_size not null 수) |
| age_dist / gender_dist | jsonb | N | 집계 카운트 `'{}'` |
| linked_sales_amount | numeric | Y | 매칭 영수건 `bill_amount` 합(인구통계↔매출) |
| computed_at | timestamptz | N | DEFAULT now() (UPSERT 시 SET now() 명시) |

- **PK** `(st_uid, biz_date, daypart)` · 재식별 불가 집계값만(개인정보 비해당) · k-익명성 억제 적용.

---

## 5. 구역 B — 홀(매장 안): 테이블 점유 세션 + 익명 인구통계

> 🟡 **핵심 수정(검증 반영)**: `vision_hall_session`은 **순수 익명**으로 유지하고, 영수건 연결은 **별도 동의-게이트 테이블(§5-4)로 분리**한다. (익명 세션 행에 영수건을 붙이면 익명성이 깨져 통계 예외를 상실하기 때문)

### 5-1. `public.vision_hall_table` — 홀 테이블 마스터 (차원)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | 매장키. **PK 구성** |
| table_no | text | N | 물리 테이블 번호(POS `bill_table_no` 매칭). **PK 구성** |
| br_uid | text | Y | 브랜드키 |
| device_code | text | N | 촬영 기기(→vision_device) |
| roi_polygon | jsonb | N | ROI 좌표 `'[]'` |
| seats | int | Y | 좌석 수(점유율 분모) |
| is_active | boolean | N | DEFAULT true |
| created_at | timestamptz | N | DEFAULT now() |
| updated_at | timestamptz | N | DEFAULT now() + 트리거 |

- **PK** `(st_uid, table_no)`.

### 5-2. `public.vision_hall_session` — 테이블 점유 세션 (팩트, **익명**)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| id | bigint IDENTITY | N | 대리 PK |
| session_uid | text | N | 엣지 세션 ID. **UNIQUE**(멱등·시작시각 보정 안전) |
| st_uid | text | Y | 매장키(no_pos_uid면 null) |
| st_id | text | Y | 원본 매장 id |
| br_uid | text | Y | 브랜드키 |
| table_no | text | N | →vision_hall_table |
| device_code | text | Y | 촬영 기기 |
| occupied_start | timestamptz | N | 착석 시각 |
| occupied_end | timestamptz | Y | 이석 시각(진행중 null) |
| dwell_seconds | int | Y | 체류(초) |
| party_size | int | Y | 추정 일행수(익명) |
| age_dist / gender_dist | jsonb | N | 익명 카운트 `'{}'` |
| avg_vision_confidence | numeric | Y | CHECK 0~1 |
| detections | jsonb | N | 집계 상세(개인 추적키·타임스탬프 없음) `'[]'` |
| sal_ymd | date | Y | 영업일(롤업·매칭 보조) |
| loaded_at | timestamptz | N | DEFAULT now() |

- **PK** `id` · **UNIQUE** `session_uid` · **IDX** `(st_uid, occupied_start)`, `(st_uid, sal_ymd)` · **영수건 컬럼 없음(익명 유지)**.

### 5-3. `public.vision_hall_occupancy` — 매장×시간버킷 점유율 롤업 (캐시)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| bucket_start | timestamptz | N | **PK 구성** |
| bucket_seconds | int | N | **PK 구성**(다중 버킷폭 충돌 방지) DEFAULT 60 |
| occupancy_rate | numeric | N | DEFAULT 0. CHECK 0~1 |
| turnover_count | int | N | DEFAULT 0 (회전 수) |
| total_guests | int | N | DEFAULT 0 |
| table_count | int | Y | 분모 감사용 |
| avg_dwell_seconds | numeric | Y | 평균 체류(초) |
| sample_count | int | N | DEFAULT 0 (k-익명성 억제 기준) |
| age_dist / gender_dist | jsonb | N | 집계 카운트 `'{}'` |
| computed_at | timestamptz | N | DEFAULT now() |

- **PK** `(st_uid, bucket_start, bucket_seconds)` · `sample_count < k` 버킷은 분포 억제.

### 5-4. `public.vision_hall_session_pos_link` — 영수건 연결 (🔴 옵션, 동의-게이트)

> 사용자·법무가 "홀 인구통계를 영수건에 연결"을 선택할 때만 생성·적재. 순수 익명 세션과 **물리 분리 + RLS**.

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| id | bigint IDENTITY | N | PK |
| session_id | bigint | N | →vision_hall_session.id (소프트) |
| st_uid | text | N | 매장키 |
| sales_bill_id | bigint | Y | 영수건 소프트 참조 |
| sal_ymd | date | Y | 매치키 |
| pos_bill_table_no | text | Y | 매칭 근거 원본 |
| match_method | text | Y | enum |
| match_confidence | numeric | Y | CHECK 0~1 |
| consent_ref | text | Y | 동의/고지 근거(→§7-1) |
| matched_at | timestamptz | Y | |
| purge_after | date | Y | 파기 예정일 |
| loaded_at | timestamptz | N | DEFAULT now() |

- **RLS** ENABLE(service_role 전용).

---

## 6. 구역 C — 주방: 품질 + 익명 활동 + 직원 개인 추적

> 🔴 **개인 추적(§6-4/6-5)은 생체인식정보(민감정보)**. 별도 동의 + 노사협의 완료 전 적재 금지(§9).

### 6-1. `public.vision_kitchen_zone` — 스테이션 ROI 마스터 (차원)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| zone_id | text | N | 스테이션 고유 id(예 'dishwasher-1'). **PK 구성** |
| zone_type | text | N | CHECK in ('dishwasher','sink','prep','plating','pass'). sink=해면기 |
| zone_name | text | Y | 표시명 |
| roi | jsonb | N | ROI 좌표 `'{}'` |
| device_code | text | Y | 촬영 기기 |
| active | boolean | N | DEFAULT true |
| created_at / updated_at | timestamptz | N | DEFAULT now() (updated_at 트리거) |

- **PK** `(st_uid, zone_id)`.

### 6-2. `public.vision_kitchen_quality` — 플레이팅/토핑 품질검사 (팩트, 음식=비PII)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| id | bigint IDENTITY | N | PK |
| source_event_id | text | N | 엣지 UID. **UNIQUE(st_uid, source_event_id)** |
| st_uid | text | N | 매장키 |
| br_uid | text | Y | 브랜드키 |
| zone_id | text | Y | 검사 스테이션(보통 plating/pass) |
| device_code | text | Y | 촬영 기기 |
| menu_uid | text | Y | 메뉴(`menus` 논리조인, 미특정 null) |
| inspected_at | timestamptz | N | 검사 시각 |
| quality_score | numeric | Y | CHECK 0~1 |
| passed | boolean | N | 합격 여부 |
| defects | jsonb | N | 결함 배열 `'[]'` |
| defect_count | int | Y | defects 개수(대시보드 필터) |
| confidence | numeric | Y | CHECK 0~1 |
| model_version | text | Y | 재현·감사용 |
| image_ref | text | Y | **음식 사진**(얼굴·사람 미포함 크롭 보장). 보존기한 관리 |
| image_purge_after | date | Y | 이미지 파기 예정일 |
| loaded_at | timestamptz | N | DEFAULT now() |

- **PK** `id` · **UNIQUE** `(st_uid, source_event_id)` · **IDX** `(st_uid, inspected_at)`, `(st_uid, menu_uid)`.
- ⚠️ `image_ref`는 반드시 **음식 ROI로 크롭 + 엣지단 얼굴/사람 마스킹** 후 업로드(주방 카메라는 손·상반신이 잡히므로 무보장 시 개인영상정보로 전환).

### 6-3. `public.vision_kitchen_activity` — 스테이션×시간버킷 **익명** 활동 롤업

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| zone_id | text | N | **PK 구성** |
| bucket_start | timestamptz | N | **PK 구성** |
| bucket_seconds | int | N | DEFAULT 60 |
| occupied_seconds | numeric | N | DEFAULT 0. CHECK 0~bucket_seconds |
| person_count_avg | numeric | N | DEFAULT 0. CHECK ≤ max |
| person_count_max | int | N | DEFAULT 0 |
| visit_count | int | N | DEFAULT 0 ('해면기 분당 N회' 지표) |
| k_suppressed | boolean | N | DEFAULT false (저인원 버킷 억제 플래그) |
| computed_at | timestamptz | N | DEFAULT now() |

- **PK** `(st_uid, zone_id, bucket_start)`.
- ⚠️ **재식별 주의(검증 반영)**: 이 익명 롤업은 §6-4/6-5 개인 롤업과 동일 그레인이라, 저인원 주방에서 두 표를 조인하면 "누가 있었는지" 역산 가능. → 개인 롤업이 켜진 매장에서는 이 표도 **service_role 접근 + k-익명성 억제(`person_count_max < k`면 억제)** 를 적용한다.

### 6-4. `public.vision_kitchen_staff_shift` — 직원 일별 근무 (팩트, 🔴 민감)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| staff_code | text | N | →vision_staff. **PK 구성** |
| work_date | date | N | **PK 구성** |
| clock_in | timestamptz | Y | 출근=당일 first_seen |
| clock_out | timestamptz | Y | 퇴근=당일 last_seen |
| zone_seconds | jsonb | N | **zone_id별** 체류 초 `'{}'`(예 `{"dishwasher-1":2550}`) |
| total_active_seconds | numeric | N | DEFAULT 0 |
| consent_ref | text | Y | 동의 근거(→§7-2) |
| purge_after | date | Y | 파기 예정일 |
| computed_at / updated_at | timestamptz | N | DEFAULT now() (updated_at 트리거) |

- **PK** `(st_uid, staff_code, work_date)` · **RLS** ENABLE(service_role 전용).
- ⚠️ `zone_seconds` 키는 **zone_type이 아니라 zone_id**(dishwasher-1/-2 구분 보존 — 검증 반영).

### 6-5. `public.vision_kitchen_staff_activity` — 직원×스테이션×버킷 롤업 (🔴 민감)

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| st_uid | text | N | **PK 구성** |
| staff_code | text | N | **PK 구성** |
| zone_id | text | N | **PK 구성** |
| bucket_start | timestamptz | N | **PK 구성** |
| bucket_seconds | int | N | DEFAULT 60 |
| seconds | numeric | N | DEFAULT 0 (체류 초) |
| visit_count | int | N | DEFAULT 0 |
| computed_at | timestamptz | N | DEFAULT now() |

- **PK** `(st_uid, staff_code, zone_id, bucket_start)` · **RLS** ENABLE(service_role 전용).

---

## 7. 컴플라이언스 지원 테이블 (검증에서 발견된 법정 증빙 누락 보완)

### 7-1. `public.vision_consent_notice` — 고객 동의·고지 기록 (kiosk/hall)
`st_uid, zone, purpose, basis('consent'/'legitimate_interest'), notice_version, notice_text, retention_days, effective_from timestamptz, effective_to timestamptz` — 키오스크 화면/안내판에 실제 게시한 고지 버전을 증빙. (per-row `consent_basis` 태그만으로는 적법근거 입증 불가)

### 7-2. `public.vision_staff_consent_log` — 직원 생체동의 이력
`id bigint IDENTITY, st_uid, staff_code, consent_type('biometric'/'video'), granted boolean, event_at timestamptz, actor text` — 부여/철회 **시점 이력**(제23조 안전성 확보조치·표준지침 제41조 증빙). `vision_staff`의 현재 플래그와 분리.

### 7-3. `public.vision_retention_log` — 파기 대장
`id, table_name, st_uid, purged_row_count, purge_reason, period_from, period_to, purged_at timestamptz, actor` — "보유기간 경과 시 파기하고 **파기 기록 유지**" 의무 이행.

### 7-4. `public.vision_ingest_deadletter` — 수집 실패/거부 이벤트
`id bigint IDENTITY, zone, st_id, device_code, payload jsonb, reason('no_pos_uid'/'unknown_device'/'malformed'/…), received_at timestamptz` — no_pos_uid 매장 세션 등이 **소리 없이 유실**되지 않도록 기록(데이터 손실 가시화).

---

## 8. 데이터 흐름

```
[엣지 박스 (매장, 온디바이스 추론)]
  · YOLO11 등으로 프레임 추론 → 원본 프레임 즉시 폐기(미저장)
  · 익명 통계/추정값만 JSON POST
        │  HTTPS (익명 통계·추정값만; 원본 영상·얼굴 임베딩 미전송)
        ▼
[FastAPI (Railway) — 신규 app/api/routes/vision.py]  ※ 엣지 인증(API키/서비스토큰) 🔴§10
  POST /api/vision/kiosk/order      → vision_kiosk_order (UPSERT: vision_event_uid)
  POST /api/vision/hall/sessions    → vision_hall_session (UPSERT: session_uid)
  POST /api/vision/kitchen/quality  → vision_kitchen_quality (UPSERT: source_event_id)
  POST /api/vision/kitchen/activity → vision_kitchen_activity (UPSERT: PK)
  POST /api/vision/kitchen/staff-*  → staff_shift/activity (동의 검증 후에만)
  공통 게이트:
   (1) st_id → store_master_v2.pos_st_uid 해석(_pos_uid). 실패 시 st_uid=null + deadletter.
   (2) device_code 존재·active 검증(vision_device).
   (3) 주방 개인추적: vision_staff.consent_biometric=true AND active=true 만 허용, 아니면 익명 강등.
        │  service_role
        ▼
[Supabase (Postgres) — 위 vision_* 테이블]
        │  Celery beat 사전집계(refresh_competition 패턴): 롤업 truncate/재집계 + computed_at SET now()
        │  POS 매칭 잡: sales_bills 시간창 매칭 → sales_bill_id/match_* 기록 (지연 영수건 백필)
        ▼
[대시보드(hbs-dashboard) / ATOMOS 브레인]
  · dashboard.py 조회 EP 신설 → src/api/types.ts 동기화 → FEATURES.md 갱신 (CLAUDE.md 규칙)
  · ATOMOS는 롤업/집계를 감지·제안 루프 입력으로 소비
```

- **불변 규칙 준수**: 백엔드는 Python에서 `CREATE TABLE` 하지 않음 — 전 DDL은 `supabase/migrations/2026-07-09-vision-{common,kiosk,hall,kitchen,compliance}.sql`를 Supabase MCP `apply_migration`으로 적용(멱등). 기존 `sync_service.py`/`sales_tasks.py` 미수정.

---

## 9. 개인정보·노무 리스크 & 동의 요건

| 구역/데이터 | 법적 분류 | 필수 요건 |
|---|---|---|
| **kiosk 인구통계→영수건** | 개인식별가능정보(통계 예외 이탈) | 고객 동의(제15조1항1호) 또는 정당이익(6호)+고지, CCTV 안내판(제25조4항), 원본 프레임·특징점 미저장, 분리저장·RLS, 30일 파기 |
| **hall 익명 집계** | 익명정보(무연결·미저장 시 법 적용 대상 아님) | 원본 미저장, 무연결·무식별, k-익명성, 안내판, 목적구속 |
| **hall→영수건 연결(옵션)** | 개인식별가능정보 | kiosk와 동일 요건 + `vision_hall_session_pos_link` 분리·RLS |
| **kitchen 익명 활동** | 원칙 익명이나 **개인 롤업 공존 시 재식별 가능** | 개인 롤업 매장은 service_role+ k-익명성 억제 |
| **kitchen 개인 추적** | **생체인식정보=민감정보(제23조)** | ① 별도 명시적 동의(단 고용 종속상 임의성 흠결 위험→동의만으론 부족), ② **근로자참여법 제20조1항14호 노사협의**(상시30인↑ 노사협의회, 미만 근로자대표 협의)·취업규칙, ③ 안내판, ④ 특징정보 암호화·분리보관, ⑤ 목적구속(위생/안전/교육; 근태·징계 목적외 이용 금지), ⑥ 최소보유·파기 |

**출처(법령·가이드라인)**: 개인정보위 고정형 영상정보처리기기 가이드라인(pipc.go.kr) · 개인정보보호법 제15·18·23·25조 · 개인정보 보호 표준지침 제41조 · 근로자참여협력법 제20조 · 생체정보 보호 안내서. (검색 근거 URL은 워크플로우 산출물 `legal.citations` 참조)

---

## 10. 미결 이슈 🔴 (사용자·법무 결정 필요) / 다음 단계

### 10-1. 결정 필요한 핵심 갈림길
1. **키오스크/홀 영수건 연결 동의**: 인구통계를 개별 영수건에 연결할 것인가(→고객 동의/고지 확보 필요), 아니면 순수 익명 유지인가? → §4·§5-4 존폐 결정.
2. **주방 개인추적 동의·협의**: 얼굴 기반 개인 추적을 켜기 전, 생체 별도 동의 + 노사협의를 확보할 것인가? 미확보 시 §6-4/6-5 적재 불가(익명 §6-3만 운영).
3. **PII 보유기간**: 기본 30일 파기 수용 vs 사유 명시 후 연장?
4. **매칭 허용 정책**: 최소 `match_confidence` 임계값, 허용 미매칭률(POS에 kiosk/채널 플래그 없고 `bill_table_no` 자주 null → 상당수 미매칭 불가피).
5. **daypart 경계 + 영업일 컷오프 시각**(심야 주문 오귀속 방지).
6. **no_pos_uid 매장**: 익명만 수집 vs 대상 제외? (→ `st_uid` nullable 여부 확정)
7. **사번 재사용**·**display_name 최소화(이니셜/가명)** 정책.
8. **품질점수 스케일**(0–1) 및 임계값 소유 위치(→§3-3 확정).
9. **k-익명성 최소 표본값**(기본 3).

### 10-2. 다음 단계 (이 문서 확정 후)
1. §10-1 결정 반영해 스키마 동결 → `FastAPI/supabase/migrations/2026-07-09-vision-*.sql` 5개 작성(Supabase `apply_migration`).
2. `app/api/routes/vision.py` 수집 EP + `st_id→pos_st_uid` 공통 리졸버 + 엣지 인증.
3. Celery 롤업/매칭 잡, k-익명성 억제.
4. `dashboard.py` 조회 EP → hbs-dashboard `src/api/types.ts` 동기화 → 양 리포 `FEATURES.md` 갱신.
5. ATOMOS: `ATOMOS_VISION_AI_TEAM` capability에 매장 Vision 파이프라인 추가(현재 dormant, 계약서 OCR/계량기 판독 슬롯).

---

*본 문서는 설계 초안(v0.1)이며, 실제 테이블 생성 전 §10-1 결정과 검토가 선행되어야 한다.*
