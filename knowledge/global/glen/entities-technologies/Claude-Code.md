---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Claude Code
tags: [domain/ai, domain/dev-tools, glen-wiki, type/technology]
---
# Claude Code

## 개요

Anthropic의 공식 CLI 코딩 에이전트. 터미널·데스크톱 앱·웹·IDE 익스텐션으로 제공. 파일 시스템·셸·git에 직접 접근해 코드 작성·편집·실행·디버깅을 수행한다. Opus/Sonnet/Haiku 모델 패밀리 위에서 동작.

## 핵심 특성

- **에이전트형**: 단일 응답이 아니라 도구 호출 루프(Read/Edit/Bash/Grep 등)로 다단계 작업 수행.
- **CLAUDE.md 기반 설정**: 프로젝트 루트의 `CLAUDE.md`가 세션 시작 시 자동 로드되어 운영 규칙·금지사항·도메인 지식을 주입.
- **스킬·서브에이전트**: 재사용 가능한 워크플로우를 스킬로 정의. 독립 작업을 서브에이전트에 위임.
- **메모리**: 사용자별 영구 메모리 시스템 (`~/.claude/projects/.../memory/`). 세션 간 사용자 프로필·피드백·프로젝트 컨텍스트 누적.

## 사용처 (in our projects)

- [[global/glen/entities-projects/GLEN_WORK]] — 본 볼트의 LLM 에이전트. Obsidian의 Lean Terminal 플러그인 안에서 실행.

## 대안·비교 대상

- Cursor, Aider, GitHub Copilot CLI, Codex (영상에서 직접 비교는 없음)

## 참고 자료

- 본 볼트 운영 규칙: [`CLAUDE.md`](../../../CLAUDE.md)
- 입문 튜토리얼: 2026-04-18-jay-choi-llm-wiki-self-replica

## 관련

- [[global/glen/entities-technologies/Obsidian]]
- [[global/glen/entities-projects/GLEN_WORK]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
