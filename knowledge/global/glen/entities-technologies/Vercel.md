---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Vercel
tags: [domain/hosting, domain/frontend, glen-wiki, type/technology]
---
# Vercel

## 개요

Next.js 제작사가 운영하는 프런트엔드 호스팅·서버리스 플랫폼. Edge Functions, Cron Jobs, AI Gateway 등 제공. main 브랜치 push → 자동 배포.

## 사용처 (in our projects)

- [[global/glen/entities-projects/HBS-Dashboard]] — 프런트 배포 + Vercel Functions (Strategy V2 워커) + Vercel Cron (`/api/cron/sales-watch`)
- AI Gateway: Anthropic Claude Sonnet 4.5 + Ollama Cloud Qwen 3 라우팅
- v1.1 결정 후 — Vercel은 cron 스케줄러 + 데이터 fetch + 마스킹 + Hermes Skill 호출 + 결과 저장만 담당 (프롬프트·LLM 라우팅은 Hermes Host로 이관)

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- raw/docs/hbs-dashboard/root/README
- raw/docs/hbs-dashboard/docs/ATOMIC_ASSISTANT_DESIGN
