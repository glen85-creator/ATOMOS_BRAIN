# VISION AI 매장 데이터 스키마 (간결판)

> 외식 매장 3개 구역(**키오스크 / 홀 / 주방**)에 Vision AI 설치 시 추출·저장할 데이터의 테이블 스키마.
> 각 표 = 예상 필요 컬럼 + 한글 설명. (실제 저장은 FastAPI → Supabase)
> 원칙: 원본 영상·얼굴 이미지는 저장하지 않고, 추정 통계값만 저장.

---

## 공통

### `vision_device` — 카메라/엣지 기기 레지스트리
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| device_code | text | 매장 내 기기 고유 코드 |
| zone | text | 담당 구역 (kiosk / hall / kitchen) |
| device_type | text | 기기 유형 (camera / edge_box) |
| label | text | 표시 이름 (예: 홀 천장 1번) |
| location | text | 설치 위치 설명 |
| status | text | 가동 상태 (active / inactive) |
| installed_at | timestamptz | 설치·등록 일시 |

### `vision_staff` — 직원 마스터 (주방 개인추적용)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| staff_code | text | 직원 코드 (사번) |
| display_name | text | 표시 이름 |
| role | text | 직무 (조리 / 설거지 등) |
| consent_biometric | boolean | 얼굴 식별 추적 동의 여부 |
| active | boolean | 재직 여부 |

---

## 구역 A — 키오스크 (주문 고객 인구통계)

### `vision_kiosk_order` — 주문 시점 고객 추정 데이터
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| captured_at | timestamptz | 추정 산출 시각 (주문 시점) |
| sal_ymd | date | 영업일 |
| party_size | int | 추정 일행 수 |
| age_dist | jsonb | 추정 연령대 분포 (예: {"20s":1,"30s":1}) |
| gender_dist | jsonb | 추정 성별 분포 (예: {"M":1,"F":1}) |
| estimated_age_band | text | 대표 연령대 |
| estimated_gender | text | 대표 성별 |
| sales_bill_id | bigint | 매칭된 영수건 (없으면 비움) |
| match_confidence | numeric | 영수건 매칭 신뢰도 (0~1) |

### `vision_kiosk_daypart` — 시간대별 집계
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| biz_date | date | 영업일 |
| daypart | text | 시간대 (아침/점심/저녁/심야) |
| order_count | int | 주문 수 |
| party_size_avg | numeric | 평균 일행 수 |
| age_dist | jsonb | 집계 연령대 분포 |
| gender_dist | jsonb | 집계 성별 분포 |
| linked_sales_amount | numeric | 매칭된 영수건 매출 합계 |

---

## 구역 B — 홀 (테이블 점유·고객 파악)

### `vision_hall_table` — 홀 테이블 마스터
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| table_no | text | 물리 테이블 번호 (POS 매칭용) |
| device_code | text | 촬영 기기 |
| roi_polygon | jsonb | 카메라 화면 내 테이블 영역 좌표 |
| seats | int | 좌석 수 |
| is_active | boolean | 운영 중 여부 |

### `vision_hall_session` — 테이블 점유 세션
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| table_no | text | 테이블 번호 |
| occupied_start | timestamptz | 착석 시각 |
| occupied_end | timestamptz | 이석 시각 |
| dwell_seconds | int | 체류 시간(초) |
| party_size | int | 추정 일행 수 |
| age_dist | jsonb | 추정 연령대 분포 |
| gender_dist | jsonb | 추정 성별 분포 |
| sales_bill_id | bigint | 매칭된 영수건 (선택) |

### `vision_hall_occupancy` — 시간대별 점유율 집계
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| bucket_start | timestamptz | 시간 버킷 시작 |
| bucket_seconds | int | 버킷 폭(초) |
| occupancy_rate | numeric | 점유율 (0~1) |
| turnover_count | int | 회전 수 |
| total_guests | int | 총 방문 인원 |
| avg_dwell_seconds | numeric | 평균 체류 시간(초) |
| age_dist | jsonb | 집계 연령대 분포 |
| gender_dist | jsonb | 집계 성별 분포 |

---

## 구역 C — 주방 (품질·인력)

### `vision_kitchen_zone` — 주방 스테이션 마스터
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| zone_id | text | 스테이션 고유 id (예: dishwasher-1) |
| zone_type | text | 유형 (dishwasher/sink(해면기)/prep/plating/pass) |
| zone_name | text | 표시명 (예: 해면기) |
| roi | jsonb | 카메라 화면 내 영역 좌표 |
| device_code | text | 촬영 기기 |
| active | boolean | 활성 여부 |

### `vision_kitchen_quality` — 플레이팅/토핑 품질 검사
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| zone_id | text | 검사 스테이션 |
| menu_uid | text | 검사 대상 메뉴 (미특정 시 비움) |
| inspected_at | timestamptz | 검사 시각 |
| quality_score | numeric | 품질 점수 (0~1) |
| passed | boolean | 합격 여부 |
| defects | jsonb | 결함 목록 (예: ["토핑부족","소스과다"]) |
| confidence | numeric | 판정 신뢰도 (0~1) |
| image_ref | text | 음식 사진 참조 (사람 미포함) |

### `vision_kitchen_activity` — 구역 활동 집계 (익명)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| zone_id | text | 스테이션 |
| bucket_start | timestamptz | 시간 버킷 시작 |
| bucket_seconds | int | 버킷 폭(초) |
| occupied_seconds | numeric | 구역 내 사람 존재 총 시간(초) |
| person_count_avg | numeric | 평균 인원 |
| visit_count | int | 구역 방문 횟수 (예: 해면기 N회) |

### `vision_kitchen_staff_shift` — 직원 일별 근무
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| staff_code | text | 직원 코드 |
| work_date | date | 근무일 |
| clock_in | timestamptz | 출근 (당일 최초 인식) |
| clock_out | timestamptz | 퇴근 (당일 최종 인식) |
| zone_seconds | jsonb | 스테이션별 체류 시간(초) (예: {"dishwasher-1":2550}) |
| total_active_seconds | numeric | 당일 총 활동 시간(초) |

### `vision_kitchen_staff_activity` — 직원 구역별 활동
| 컬럼 | 타입 | 설명 |
|---|---|---|
| st_uid | text | 매장 식별자 |
| staff_code | text | 직원 코드 |
| zone_id | text | 스테이션 |
| bucket_start | timestamptz | 시간 버킷 시작 |
| seconds | numeric | 해당 구역 체류 시간(초) |
| visit_count | int | 해당 구역 진입 횟수 |
