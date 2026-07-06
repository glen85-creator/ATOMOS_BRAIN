---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Obsidian
tags: [domain/knowledge-management, domain/notes, glen-wiki, type/technology]
---
# Obsidian

## 개요

로컬 마크다운 파일 기반 노트 앱. "보관함(vault)"이라는 폴더 단위로 작동하며, 사실상 일반 폴더를 예쁘게 보여주는 뷰어 + 위키링크·플러그인 생태계의 결합. 무료.

## 핵심 특성

- **로컬 우선**: 모든 노트는 사용자 컴퓨터의 마크다운 파일. 클라우드 종속성 없음.
- **위키링크**: `페이지명` 문법으로 페이지 간 연결. 그래프 뷰로 시각화.
- **커뮤니티 플러그인**: 수많은 플러그인 생태계. 본 볼트가 쓰는 주요 플러그인:
  - obsidian-git — Git 동기화·버전 관리
  - Lean Terminal — 내장 터미널 (Obsidian 안에서 Claude Code 실행)
  - Obsidian Web Clipper — 브라우저 확장과 연동해 웹 페이지를 마크다운으로 저장
  - Dataview — frontmatter 기반 동적 쿼리 (본 볼트 `index.md`에서 사용)
- **frontmatter**: YAML 메타데이터. type·tags·aliases 등으로 페이지 분류.

## 사용처 (in our projects)

- [[global/glen/entities-projects/GLEN_WORK]] — 본 볼트의 노트 저장·렌더링 레이어

## 대안·비교 대상

- Notion, Logseq, Roam Research 등 (영상에서 직접 비교는 없음)

## 참고 자료

- 입문 튜토리얼: 2026-04-18-jay-choi-llm-wiki-self-replica

## 관련

- [[global/glen/entities-technologies/obsidian-git]]
- [[global/glen/entities-technologies/Obsidian-Web-Clipper]]
- [[global/glen/entities-projects/GLEN_WORK]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
