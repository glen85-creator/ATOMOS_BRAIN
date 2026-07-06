---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 비용 메일 수집 → 재료 매핑 → 매장별 실효단가 → 메뉴원가 실반영
tags: [domain/food-franchise, domain/cost, status/active, glen-wiki, type/decision]
---
# 비용 메일 수집 → 재료 매핑 → 매장별 실효단가 → 메뉴원가 실반영

## 맥락 (Context)

레시피 메뉴 원가는 **물류 한 채널 기준 단가**로 계산돼 있었다. 그러나 매장(구로점 모델매장, 청년38국수)은 쿠팡·식봄 등 다른 채널에서도 식자재를 산다는 것이 확인됐다. 또한 매장 메뉴 원가 화면에 **말도 안 되는 값**(연탄불고기 69,556원·비빔냉면 26,800원·원가율 1830%)이 섞여 있었다. 진짜 손익(영업이익)을 내려면 실제 다채널 원가 + 인건비·고정비·공과금이 필요하다.

## 결정 (Decisions)

1. **비용 메일 수집**: Resend Inbound(`*@atomos.im`) → `cost_transaction`. 쿠팡 혼합주문 품목을 대표품목명으로 **식자재/소모품/비품 자동분류**(감사 3인 교차검증). 쿠팡 주문의 전체 품목은 `line_items` jsonb로 저장.
2. **비용·손익 통합 허브**: 흩어진 9개 메뉴 → `비용·손익` 탭 하나로. 매장·월 선택 공유. 단, **메일함(커뮤니케이션)·메일계정·목표(전역 selector)는 성격이 달라 분리**.
3. **매핑 vs 가격 분리** (글렌 핵심 지적): 상품→재료 **매핑은 전사 공통**(`ingredient_alias`, 한 번), **가격은 매장별**(`supply_chain_record`, store_id). 매장 재료 **실효단가 = 그 매장 전 채널(물류 wms_couger + 쿠팡/식봄 cost_mail) 수량가중평균**.
4. **메뉴원가 = 표준 + 실제 overlay**: 배포 표준원가(`store_menu_cost_v2`)는 보존, 매장 실효단가 기준 **실제 원가를 나란히** 표시(덮어쓰기 X)·미매핑은 커버리지% 정직 표기. **전처리(sub-recipe) 카테고리 분리**해 판매 메뉴 목록·평균 지표에서 제외.
5. **이상 원가는 대부분 가격이 아니라 데이터 정합**: 원인 3종 = 자동백필 단가 오류(잔치육수 10배·냉면비빔장)·**레시피 오연결**(재료명↔ig_id 불일치: 물만두→등심돈까스·대파→달걀)·**미사용/오배포 메뉴**(청년38에 없는 연탄불고기). **WMS 실매입가가 ground truth**. `recalc_store_costs`는 현재단가를 재사용하므로 근본(재료단가/레시피)을 고쳐야 반영됨.
6. **문서 OCR 자동수집** (방향 확정, 미구현): 메일 첨부(임대계약서·세금계산서·고지서 PDF/이미지) → **Claude 비전 OCR** → 구조화 추출 → **사람 1클릭 확인 후** 계약(`vendor_contract`)·고정비(`fixed_cost_entry`)·공과금(`utility_bill_entry`) 등록. 우선순위: 임대계약서→관리비 세금계산서→정수기 렌탈→공과금 고지서.

## 결과 (Consequences)

- 구로점: **고원가(40%+) 17개→3개, 평균 원가율 79.4%→30.1%**, 비정상 값 전부 제거.
- 임대계약서를 (수동)OCR 판독 → 계약(오형식·월 280만·2028-05-22 만료)+월 고정비 등록으로 **손익 구성 시작**. 테스트 인건비 삭제.
- 매핑/채널단가/실효단가/실메뉴원가/store-queue RPC·EP + FE 화면 배포(FastAPI PR#118~136·hbs PR#121~136 다수, 마이그 019~022).

## 미결 (Open)

- 손익 숫자 채우기: 인건비(실제 직원)·관리비·통신·보험·공과금 (내일 사용자 확인).
- 문서 OCR 파이프라인 구축(스펙→구현).
- 전처리↔부모 메뉴 원가 **자동 동기화**(현재 스냅샷 값이라 미보장).
- 실벤더(쿠팡/식봄/카드) 알림 이메일을 `38_guro@atomos.im`로 변경 → **실시간 수집**(현재 6주 백필만).
- **보안**: 무인증 비용/매핑 EP에 로그인 인증(실데이터/공개 전 필수).

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/concepts/ATOMOS]]
- [[global/glen/entities-people/glen]]

## 출처(원본)

- raw/meetings/claude-conversations/2026-07-06-cost-mail-menu-cost
