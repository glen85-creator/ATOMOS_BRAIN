---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: RAG
tags: [domain/ai, glen-wiki, type/concept]
---
# RAG

## 정의

Retrieval-Augmented Generation. 질의마다 원본 문서 코퍼스를 검색해 관련 청크를 찾고, 그것을 프롬프트 컨텍스트로 주어 LLM이 답변을 생성하는 패턴.

## 핵심 아이디어

- **on-demand 합성**: 답변에 필요한 지식은 매번 raw에서 끌어와 그 자리에서 합성. 사전 가공된 중간 산물(위키)이 없다.
- **장점**: 원본 충실성이 높음. 코퍼스가 자주 갱신돼도 인덱스만 다시 만들면 됨.
- **단점**: 매 질의마다 같은 검색·재합성을 반복. 지식이 LLM 안에 "쌓이지" 않고 휘발됨. 청크 단위 검색이라 문서 전체를 가로지르는 종합 판단이 약함.

## 적용 예

- 사내 문서 검색 챗봇 (대부분의 AI 챗봇 기본 패턴)
- ChatGPT의 "내 파일 검색" 기능

## 관련 개념

- [[global/glen/concepts/LLM-Wiki]] — RAG의 대안으로 제시됨. 위키를 사전에 컴파일해 두고 질의 시 위키를 참조.

## 참고

- 2026-04-18-jay-choi-llm-wiki-self-replica — RAG vs LLM Wiki 비교의 출처

## 관련

- [[global/glen/concepts/LLM-Wiki]]

## 출처(원본)

- Clippings/AI로 나를 복제했습니다  클로드 코드 × 옵시디언 × LLM Wiki
