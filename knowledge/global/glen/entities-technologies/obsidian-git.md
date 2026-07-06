---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: obsidian-git
tags: [domain/version-control, domain/knowledge-management, glen-wiki, type/technology]
---
# obsidian-git

## 개요

Obsidian 커뮤니티 플러그인. 볼트를 Git 저장소로 다루며 주기적으로 자동 commit·push·pull을 수행. 모바일·데스크톱 어디서나 같은 볼트를 동기화하고 변경 이력을 추적할 수 있게 한다.

## 핵심 특성

- 자동 commit (간격 설정 가능)
- 자동 push/pull
- 충돌 해결 UI
- 볼트 단위 동작 — 한 볼트 = 한 Git repo가 일반적

## 사용처 (in our projects)

- [[global/glen/entities-projects/GLEN_WORK]] — 본 볼트와 `github.com/glen85-creator/GLEN_WORK` 사이의 동기화. 본 볼트의 모든 변경은 자동으로 커밋 대상이 된다 (CLAUDE.md §10).

## 대안·비교 대상

- Obsidian Sync (공식 유료), iCloud/Dropbox 동기화 (이력 추적 없음)

## 참고 자료

- 2026-04-18-jay-choi-llm-wiki-self-replica

## 관련

- [[global/glen/entities-technologies/Obsidian]]
- [[global/glen/entities-projects/GLEN_WORK]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
