---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Supabase
tags: [domain/database, domain/backend, glen-wiki, type/technology]
---
# Supabase

## 개요

PostgreSQL 기반 BaaS. Postgres + Auth + Storage + RLS + Realtime + Edge Functions. service_role 키(전권) + anon 키(RLS 통과만) 이원화.

## 사용처 (in our projects)

- [[global/glen/entities-projects/HBS-Dashboard]] / [[global/glen/entities-projects/HBS-FastAPI]] — DB. 프로젝트 `nmeiydjbusrtyckrsyai` (`HBS_POS_DATA_HUB`, ap-southeast-1). Postgres 17.
- RLS 정책으로 [[global/glen/concepts/Permission-Matrix]] 시행 — 운영 테이블 23개 RLS 단계적 활성화 중
- service_role 키는 백엔드(Railway·Vercel functions)만, 프런트엔드 절대 노출 금지

## 핵심 특성

- Row Level Security (RLS) — 행 단위 권한
- `auth.uid()` + SECURITY DEFINER 함수 (`current_user_role()`)
- GIT 스타일 마스터 버전 관리는 자체 컬럼(`parent_rv_id`)으로 구현

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-projects/HBS-FastAPI]]

## 출처(원본)

- raw/docs/hbs-dashboard/root/PROJECT_CONTEXT
- raw/docs/hbs-dashboard/docs/ATOMOS_INTEGRATED_DESIGN
