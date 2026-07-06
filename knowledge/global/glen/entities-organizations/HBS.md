---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: HBS
tags: [domain/food-franchise, status/active, glen-wiki, type/organization]
---
# HBS

## 개요

외식 프랜차이즈 본사. **주식회사 HBS** (HBS Co., Ltd. — **H**APPY **B**RIDGE **S**UDOGWON). 6개 브랜드를 운영하는 다본사(multi-brand) 조직. 자체 운영을 위해 [[global/glen/entities-projects/HBS-Dashboard]] + [[global/glen/entities-projects/HBS-FastAPI]] B2B SaaS를 구축 중이며, 검증 후 외부 프랜차이즈 본사에 판매하는 비즈니스 모델을 추진. 조직 코드: `OR-001`.

## 회사 정보

| 항목 | 내용 |
|---|---|
| 정식 사명 | 주식회사 HBS (HBS Co., Ltd.) |
| 약어 풀이 | HAPPY BRIDGE SUDOGWON |
| 대표 | 이구승 |
| 본사 | 서울특별시 광진구 천호대로 615 2층 |
| 사업자번호 | 445-88-02233 |
| 가맹문의 | 1588-6020 |
| 가맹 담당 이메일 | glen_85@hbscom.com ([[global/glen/entities-people/glen]]) |
| 회사 소개서 | `D:/WORK/HBS/YOUTH38_CLAUDE/docs/company/HBS 회사 소개서.pptx` |

## 주요 인물

- glen — 1인 개발자 (LLM 보조)

## 관련 프로젝트·제품

- [[global/glen/entities-projects/HBS-Dashboard]] — 프런트 ([[global/glen/entities-technologies/React]] + [[global/glen/entities-technologies/Vercel]])
- [[global/glen/entities-projects/HBS-FastAPI]] — 백엔드 ([[global/glen/entities-technologies/FastAPI]] + [[global/glen/entities-technologies/Railway]])

## 운영 브랜드 (6개, 2026-05 기준)

| 코드 | 브랜드 | 매장 수 |
|---|---|---|
| `BR-GSN` | [[global/glen/entities-organizations/국수나무]] | 약 200 *(BUSINESS_PLAN 199, 정합성은 264 정본 도출 시점 재집계 필요)* |
| `BR-C38` | [[global/glen/entities-organizations/청년38국수]] | 약 50+ *(BUSINESS_PLAN 시점 추정, 정본 264 분배는 미확정)* |
| `BR-HWP` | [[global/glen/entities-organizations/화평동왕냉면]] | - |
| `BR-TKY` | [[global/glen/entities-organizations/도쿄스테이크]] | - |
| `BR-JGI` | [[global/glen/entities-organizations/지구인]] | - |
| `BR-PNS` | [[global/glen/entities-organizations/파네시마]] | - |

**관리 매장 264** (Atomos Manifesto v3 / 소개서 v2.0, 2026-05-16 정본). 5일 전 `BUSINESS_PLAN.md`의 287(운영 199 / 휴점 74 / 기타)은 더 넓은 모집단 기준이며 본 위키는 264를 사용한다.

## 핵심 외부 시스템 연동

- [[global/glen/entities-organizations/메타시티]] — POS 공급사 (매출 데이터 원천)
- [[global/glen/entities-organizations/요기요]] — 배달 플랫폼
- [[global/glen/entities-organizations/쿠팡이츠]] — 배달 플랫폼
- [[global/glen/entities-organizations/배달의민족]] — 배달 플랫폼

## 노트

- HBS 자체 6 브랜드 287매장이 dogfooding 운영 데이터의 핵심 자산 (BUSINESS_PLAN §10).
- 베타 본사 영업 후보로 1~2곳을 외부 본사로 도입 예정 (ROADMAP_B2C_TO_B2B §5).

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/entities-organizations/국수나무]]
- [[global/glen/entities-organizations/청년38국수]]
- [[global/glen/entities-organizations/다산38국수]]

## 출처(원본)

- raw/docs/hbs-dashboard/root/PROJECT_CONTEXT
- raw/docs/hbs-dashboard/docs/BUSINESS_PLAN
- raw/docs/hbs-dashboard/docs/ATOMOS_INTEGRATED_DESIGN
- raw/docs/youth38/CLAUDE
