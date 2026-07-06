---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Permission Matrix
tags: [domain/b2b-saas, domain/access-control, glen-wiki, type/concept]
---
# Permission Matrix

## 정의

[[global/glen/concepts/ATOMOS]]의 권한 모델 정본. 38 메뉴 × 7 역할 매트릭스. v1.0 (2026-05-17). 메뉴별 권한 + AI 비서 시야 + RLS 정책 세분화 기준의 단일 진실 원천. 코드 구현: `src/auth/permissions.ts`.

## 핵심 아이디어

### 7 역할
| 역할 | scope |
|---|---|
| super_admin | 모든 조직·본사·매장 |
| brand_admin | 특정 본사 + 본사 소속 매장 |
| brand_manager | 본사 R/W, 단 결제·인사 민감 영역 제외 |
| sv | 본사 R + 담당 매장 R/W |
| store_manager | 본인 매장 R/W |
| staff | 본인 매장 일부 R + 본인 정보 R/W |
| viewer | 지정 매장·본사 R 전용 (감사·외부 자문) |

### Access 코드 (10종)
`rw`, `rw-brand`, `rw-store`, `rw-assigned`, `r`, `r-brand`, `r-store`, `r-assigned`, `r-self`, `none`

### 38 메뉴 7 그룹
- 운영 (6): /dashboard, /strategy-timeline, /channel, /menu-engineering, /delivery, /simulator
- 전략 자동화 (2): /strategy-v2, /strategy-v2/retrospect
- 본사 관제 (4): /hq, /brand-kpi, /store-grading, /store-alerts
- 운영 도메인 (6): /sourcing, /hq/strategy, /sv, /menu-rd, /franchise, /brand-development
- 마케팅 (2): /content-studio, /review-manager
- 마스터 (9): /master/v2/{codes,suppliers,ingredients,recipes,stores,deployments,menu-costs,supply-chain,unmapped}
- 설정 (9): /admin/{store-profile,targets,channel-config,delivery-accounts,gateway-settings,labor-costs,fixed-costs,access-control}, /master/v2/migration

### AI 비서 시야 자동 도출
비서 시야 = 호스트 사용자의 매트릭스 행. 즉 사용자가 메뉴에서 접근 가능한 데이터 = 비서가 LLM에 보낼 수 있는 데이터.

## 적용 예

- `Layout.tsx`: `visibleMenusFor(role)` 사이드바 필터링
- `ProtectedRoute.tsx`: `canAccessMenu(role, path)` 라우트 가드
- RLS 정책: `rw-store`·`rw-brand` 의미를 데이터 행 필터로 변환 (user_scope JOIN)

## 관련 개념

- [[global/glen/concepts/ATOMOS]] §2 (권한 모델)
- [[global/glen/concepts/Atomic-Assistant]] (비서 시야가 본 매트릭스에서 파생)

## 참고

- `PERMISSION_MATRIX.md` v1.0 (2026-05-17) — 단일 진실 원천
- `src/auth/permissions.ts` — 코드 구현

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Atomic-Assistant]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/PERMISSION_MATRIX
