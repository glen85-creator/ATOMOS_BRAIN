---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 지오코딩 온보딩 자동화 + 미지오코딩 백필"
tags: [domain/hbs-dashboard, domain/sangwon, domain/geocode, status/active, type/adr, glen-wiki, type/decision]
---
# ADR: 지오코딩 온보딩 자동화 + 미지오코딩 백필

## 맥락
경쟁 상권 카드([[global/glen/decisions/2026-06-21-sangwon-competition-card]])는 매장 좌표(`store_geo`)에 의존. 신규매장이 좌표 없이 새는 것 방지 + 기존 활성 13매장 미지오코딩 회복. **제약: VWorld 지오코더는 Railway IP를 차단** → 지오코딩은 반드시 KR에서 실행해야 함.

## 핵심 결정
1. **실행 위치 = Vercel icn1(서울) 함수.** ⭐probe로 확정: **Railway는 VWorld 차단이지만 Vercel icn1(서울 데이터센터)은 도달 OK**(probe가 INVALID_KEY 응답 수신 = 연결 정상). probe-gated 설계(A=icn1 함수+cron / B=브라우저 폴백) → A 채택.
2. **자동 + 수동 병행.** icn1 함수가 일일 cron(03:00 KST)으로 좌표 미확보 활성매장 자동 지오코딩(Supabase 직접). 자동 불가(주소오류) 매장은 관리자 패널 수동 좌표.
3. **실패 표기로 무한재시도 방지.** `store_geo.status`(null/failed/manual) — failed는 자동 재시도 안 함.
4. **백필은 정밀매칭만.** 토큰 점진제거+PARCEL 폴백은 면/동 centroid 오탐(반경 경쟁엔 치명) → ROAD 전용·도로명+건물번호·refined_addr 검증.

## 솔루션 (FastAPI#54·#55, hbs#59·#60·#61)
- `api/geocode-stores.ts`(region icn1, 일일 cron) + `api/_lib/geocode.ts`(정제·VWorld road→parcel). `store_geo.status`/`geocode_error`. Railway `GET /sangwon/ungeocoded-stores`+`POST /sangwon/store-geo`. 관리자 `/admin/atomos` 📍지오코딩 탭(목록·수동좌표 KR범위검증).

## 결과
운영 중 활성 매장 좌표 **100%**(13 중 11 회복: cron/정밀 7 + 수동 4). 잔여 2=폐업(st_use=Y 오염→마스터 위생). 수동 4는 namuya.co.kr 매장찾기 실주소(춘천CGV·동백역·평택고덕[POS 987→945 오타]·진접[해밀에당→해밀예당 오타교정]), 전부 refined_addr 검증.

## 디버깅 연쇄 (systematic-debugging)
①ESM `.js` 확장자 누락→MODULE_NOT_FOUND(tsc/vitest는 통과·Vercel 런타임만 실패) ②PR#54 push 누락→plan/spec만 머지→push+#55 재머지 ③Vercel SUPABASE_SERVICE_ROLE_KEY 값 오류→함수 read 500(정상키 REST·supabase-js 둘 다 200으로 격리) ④brute-force가 면/동 centroid 오탐→ROAD 정밀매칭 교정+오염 리셋 ⑤**읍/면 토큰이 VWorld ROAD 매칭을 깸**→면 제거로 3개 추가 회복.

## 교훈
- Vercel Node ESM: 상대 import `.js` 필수. env 변경은 재배포해야 적용. preview/immutable URL은 배포보호 401(cron은 BYPASS).
- VWorld ROAD: 읍/면 토큰 제거·`로N길` 도로명 공백분리 금지·도로명+건물번호 정밀매칭만(centroid 폴백 금지). 프랜차이즈 실주소 = namuya.co.kr 매장찾기 권위.
- 환경: wsl bash -lc 병렬호출·for루프·멀티라인·중첩인용 깨짐 → Python 스크립트·순차·절대경로.

## 다음
폐업 2 st_use 위생([[global/glen/decisions/2026-06-20-pos-sales-reconcile]] 계열 마스터 정리)·신규매장 온보딩 자동 합류 검증.

## 관련

- [[global/glen/decisions/2026-06-21-sangwon-competition-card]]
- [[global/glen/entities-technologies/Supabase]]
- [[global/glen/concepts/ATOMOS]]

## 출처(원본)

- FastAPI#54·#55 / hbs#59·#60·#61 (2026-06-21)
- spec: ~/FastAPI/docs/superpowers/specs/2026-06-21-geocode-onboarding-design.md
