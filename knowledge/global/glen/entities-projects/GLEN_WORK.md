---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: GLEN_WORK
tags: [status/active, domain/knowledge-management, glen-wiki, type/project]
---
# GLEN_WORK

## 개요

본 볼트 자체. [[global/glen/concepts/LLM-Wiki]] 패턴 기반 개인 세컨드 브레인. [[global/glen/entities-technologies/Obsidian]] + [[global/glen/entities-technologies/Claude-Code]] + [[global/glen/entities-technologies/obsidian-git]]으로 구동. 설계 출처는 [[global/glen/entities-people/안드레이-카파시]]의 LLM Wiki 아이디어, 구체적 구현 패턴은 [[global/glen/entities-people/Jay-Choi]]의 튜토리얼(2026-04-18-jay-choi-llm-wiki-self-replica)을 따른다.

## 아키텍처

3-레이어 구조:
- **raw/** — 원본 소스 (불변)
- **wiki/** — LLM이 작성·유지 (엔티티/개념/결정)
- **queries/** — 사용자 질의의 산물

타입 기반 frontmatter 스키마. Dataview/Bases로 동적 인덱싱.

## 기술 스택

- [[global/glen/entities-technologies/Obsidian]] — 노트 앱
- [[global/glen/entities-technologies/Claude-Code]] — LLM 에이전트
- Dataview — 동적 쿼리 (Obsidian 플러그인)
- Bases — 데이터베이스 뷰 (Obsidian 코어)
- [[global/glen/entities-technologies/obsidian-git]] — Git 동기화
- Excalidraw — 다이어그램 (Obsidian 플러그인)

## 핵심 인물

- glen (소유자)

## 주요 결정사항 (ADR)

- (없음 — 첫 결정사항이 생기면 `wiki/decisions/`에 등록)

## 노트

- 설계 문서: [docs/superpowers/specs/2026-05-20-second-brain-design.md](../../../docs/superpowers/specs/2026-05-20-second-brain-design.md) — 본 볼트의 메타 문서이므로 `sources:` (raw 전용)에는 포함하지 않음
- 구현 계획: [docs/superpowers/plans/2026-05-20-second-brain-implementation.md](../../../docs/superpowers/plans/2026-05-20-second-brain-implementation.md)
- 원격 저장소: github.com/glen85-creator/GLEN_WORK

## 관련

- [[global/glen/concepts/LLM-Wiki]]
- [[global/glen/entities-people/안드레이-카파시]]
- [[global/glen/entities-people/Jay-Choi]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
