---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Obsidian Web Clipper
tags: [domain/knowledge-management, domain/browser-extension, glen-wiki, type/technology]
---
# Obsidian Web Clipper

## 개요

Obsidian 공식 브라우저 확장. 웹 페이지를 클릭 한 번으로 마크다운으로 변환해 지정한 볼트 폴더에 저장.

## 핵심 특성

- 페이지 본문을 마크다운으로 변환 (광고·네비 등 제거)
- 저장 시 frontmatter에 `title`, `source` (URL), `author`, `published`, `created`, `description`, `tags: [clippings]` 자동 기입
- 저장 폴더는 확장 설정에서 변경 가능. 본 볼트는 `Clippings/`를 기본 폴더로 사용.

## 사용처 (in our projects)

- [[global/glen/entities-projects/GLEN_WORK]] — 웹 아티클의 1차 진입점. `Clippings/`에 떨어지면 `raw/articles/`와 동등하게 인제스트 대상이 됨 (CLAUDE.md §5.1).

## 대안·비교 대상

- MarkDownload 브라우저 확장, Notion Web Clipper, Pocket

## 참고 자료

- 2026-04-18-jay-choi-llm-wiki-self-replica

## 관련

- [[global/glen/entities-technologies/Obsidian]]
- [[global/glen/entities-projects/GLEN_WORK]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
