---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: LLM Wiki
tags: [domain/ai, domain/knowledge-management, glen-wiki, type/concept]
---
# LLM Wiki

## 정의

LLM이 직접 위키를 **컴파일**해 유지보수하는 지식 관리 패턴. [[global/glen/entities-people/안드레이-카파시]]가 2026-04에 제안.

## 핵심 아이디어

- **RAG와의 차이**: [[global/glen/concepts/RAG]]는 매 질의마다 원본을 검색·재합성한다. LLM Wiki는 LLM이 사전에 원본을 읽어 위키 페이지로 "컴파일"해 두고, 질의 시에는 위키를 참조한다. 카파시의 비유: 소스코드(raw) → 실행 파일(wiki) 컴파일.
- **3-레이어 구조**:
  1. **Raw**: 불변 원본 (논문·기사·메모). LLM은 read-only.
  2. **Wiki**: AI가 전적으로 소유하는 마크다운 파일 디렉토리 (요약·엔티티·분석). 사람은 read-only.
  3. **Schema** (e.g. `CLAUDE.md`): AI에게 위키 사용법·운영 규칙을 알려주는 설계도.
- **3대 작업**:
  1. **Ingest**: raw를 넣으면 AI가 요약 페이지 생성·인덱스 업데이트·관련 페이지 교차 수정.
  2. **Query**: 위키에서 답변 합성. 좋은 답변은 다시 위키에 저장.
  3. **Lint**: 모순·oldness·끊긴 연결 주기적 검증.
- **지속 가능성의 핵심**: 사람은 정리 유지보수가 귀찮아 포기하지만 AI는 지치지 않는다. 유지보수 비용이 0에 수렴 → 위키를 실제로 유지할 수 있다.
- **컴파운드 효과**: 카파시 표현으로 "지식은 복리로 쌓인다". 좋은 답변이 다시 위키에 저장되는 순환.

## 적용 예

- **카파시 본인**: 논문·연구 자료 정리
- **[[global/glen/entities-people/Jay-Choi]]**: "나 자신"을 주제로 — 개인 서비스 이력·실패·인사이트를 위키화
- **[[global/glen/entities-projects/GLEN_WORK]]**: 본 볼트. 업무·기술 지식 + 자기 자신 두 가지를 동시에 다룸

## 관련 개념

- [[global/glen/concepts/RAG]] (대비되는 패턴)
- 컴파일 (소스→실행파일 비유)

## 참고

- 원본 아이디어 파일: GitHub의 카파시 LLM Wiki spec (영상에서 링크 미공개, 직접 검색 필요)
- 본 볼트 설계 문서: [docs/superpowers/specs/2026-05-20-second-brain-design.md](../../docs/superpowers/specs/2026-05-20-second-brain-design.md)
- 입문 영상: 2026-04-18-jay-choi-llm-wiki-self-replica

## 관련

- [[global/glen/concepts/RAG]]
- [[global/glen/entities-people/안드레이-카파시]]
- [[global/glen/entities-projects/GLEN_WORK]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
