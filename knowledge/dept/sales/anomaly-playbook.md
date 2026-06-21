---
scope: dept:sales
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 매출 급락 대응 플레이북 (D-SALES)
---

# 매출 급락 대응 플레이북

## 감지 의미
- z는 같은 요일 대비 robust 표준화 점수. z ≤ -3 = critical, -2 ≥ z > -3 = warning.
- dod_delta_pct = 전일 대비, mom_delta_pct = 전월 동기 대비 변화율(분수).

## 초동 점검 순서
1. 운영 아티팩트 배제: gross=0(휴무/미수집), 수집 결함일 여부.
2. 외부 요인: 우천·한파·인근 행사·공휴일.
3. 내부 요인: 운영 차질, 메뉴 품절, 인력.

## 권고 패턴
- 외부 요인 우세: 관망 + 점주 알림(notify), 데이터 확인(flag_data_issue).
- 내부 요인 의심: 담당 배정(create_task) + 의사결정 기록(record_decision).
- 마케팅 캠페인 필요: handoff_marketing.
