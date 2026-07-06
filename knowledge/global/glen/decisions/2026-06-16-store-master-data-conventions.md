---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 매장 마스터 데이터 보정 컨벤션 (2026-06-16)"
tags: [domain/backend, domain/data, project/hbs-fastapi, status/active, glen-wiki, type/decision]
---
# ADR: 매장 마스터 데이터 보정 컨벤션 (2026-06-16)

## 컨텍스트
`매장 정보.xlsx` 일괄적재와 후속 보정 과정에서, `store_master_v2`의 식별자/매칭/정정 방식에 대한 규칙이 필요했다. 핵심 제약: ① `st_id`(`ST-{지역}-{타입}-{seq}`)에 지역·타입이 박혀 있고 309행 전체가 `region_code`/`store_type_code` 컬럼과 **항상 일치**(불변식). ② 매출/POS 데이터는 `st_uid`(POS UID), 마스터/운영은 `st_id`로 키가 갈리고 `code_mapping`이 다리. ③ POS 동기화 코드(`sync_service.py`/`sales_tasks.py`)는 수정 금지(CLAUDE.md).

## 결정

1. **이중 키 체계 유지.** 매출/POS 테이블 = `st_uid`(예 `I22091400094`), 마스터/원가/SV 테이블 = `st_id`(예 `ST-SE-RD-0038`). 둘은 `code_mapping(entity_type=store, external_system=pos_metacity/wms_couger/hq_bp)`로 연결. `internal_code`는 다형 참조라 FK 없음.

2. **매칭 우선순위 + 비파괴 upsert.** 쿠거코드(`wms_couger`) → 사업자번호 → **매장명(지점명 보존 정규화)** → 신규. 매칭분은 **NULL 컬럼만 COALESCE**로 채우고 없는 code_mapping만 추가(재실행 멱등). 매장명 정규화는 상태표기 `(종결)/(신)`만 제거하고 **지점명은 보존**(브랜드 수준으로 뭉개면 동명 오충돌).

3. **타입/지역 정정 시 st_id 처리 = 참조 유무로 분기.**
   - **신규 매장(이번 세션 생성, 참조=code_mapping뿐)** → `st_id` **재발급**으로 불변식 유지. 예: OT→RD = `ST-SE-OT-0001`→`ST-SE-RD-0038`(+code_mapping.internal_code 갱신).
   - **기존 매장(매출·POS·원가 등 `st_id` 참조 가능성)** → **`region_code`/`store_type_code` 컬럼만** 갱신, `st_id`는 불변 키로 유지(라벨↔컬럼 의도적 불일치 허용). PK 연쇄변경은 고위험이라 회피. 예: ET 지역 보정 39건.

4. **타입 정보가 원천에 없으면 추정 금지·`OT` 기본.** 엑셀 공란이면 `OT(기타)` 채번, HQ 확인 후에만 실타입 보정(라운지=특수상권 등은 추정 아닌 회신 기반).

5. **POS 테스트 매장 제외 = DB 트리거.** `sync_service.sync_stores()`가 매 동기화마다 POS API의 `st_use`를 upsert하므로 수동 `st_use='N'`은 되돌아감. POS 파이썬 미수정 원칙상, `stores` BEFORE INSERT/UPDATE 트리거로 해당 `st_uid`의 `st_use`를 영구 `'N'` 고정(`brands_keep_name` 트리거와 동일 패턴).

## 결과
- **긍정**: 불변식 일관 유지(신규), 기존 매장 PK 안정(매출 연쇄 변경 회피), 멱등 재적재, POS 코드 무수정. 운영 DB 291→309 정합.
- **부정/비용**: 기존 매장 보정 시 `st_id` 라벨이 실제 지역/타입과 어긋나는 행 누적(예 `ST-ET-OT-0086`=실제 경기/일반). `st_id`는 출생시 라벨로만 신뢰하고 **타입/지역은 항상 컬럼을 읽어야** 함(앱은 이미 그러함 — `st_id` 파싱 코드 없음 확인).

## 대안 검토
- *모든 보정에 st_id 재발급*: 불변식은 완벽하나 기존 매장의 매출/POS 참조까지 연쇄 갱신 필요 → 고위험·대규모, 기각.
- *컬럼만 갱신 일괄 적용*: 신규 매장에도 적용하면 불변식이 처음부터 깨짐. 신규는 참조가 없어 재발급이 싸므로 분기 채택.
- *테스트매장 코드레벨 필터*: `sales_tasks.py` 수정 필요(CLAUDE.md 위반) → 트리거로 대체.

## 참고
- 작업 요약: 2026-06-16-hbs-store-bulk-load-corrections
- 스키마: hbs-master-v2-schema
- 미해결: 라벨↔컬럼 불일치 누적분 정리 정책, 동명 중복(OF-0007/0008) 처리, ET 잔여 84.

## 출처(원본)

- FastAPI:scripts/load_stores_from_excel.py
- FastAPI:supabase/migrations/2026-06-16-exclude-test-store-sync.sql
