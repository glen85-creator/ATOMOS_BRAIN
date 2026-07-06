---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: Open WebUI
tags: [domain/ai, domain/llm-ui, status/external, glen-wiki, type/technology]
---
# Open WebUI

## 정의

오픈소스 웹 채팅 UI. OpenAI 호환 API 엔드포인트를 모델 백엔드로 붙여 쓰는 범용 LLM 인터페이스. 대화 기록·사용자 계정·모델 선택 UI를 기본 제공한다. 본 볼트에서는 [[global/glen/concepts/Hermes-Agent]]의 Gateway/API Server에 연결되는 **외부 입구(channel)** 중 하나로 다룬다.

## 본 볼트에서의 위치

[[global/glen/concepts/Hermes-Agent]]의 채널 모델(CLI / Slack / cron / MCP / 웹 UI) 중 **웹 UI 입구**를 구현하는 외부 도구. Hermes 자체의 공식 기능은 아니지만 Hermes 공식 문서가 Integration 흐름을 제공한다.

## 연결 토폴로지

```
사용자 → Open WebUI (브라우저, http://localhost:3000)
       → Hermes Gateway/API Server (http://127.0.0.1:8642/v1, OpenAI 호환)
       → Hermes Agent (Skill·도구·메모리·터미널)
```

Open WebUI는 Hermes를 OpenAI 호환 모델로 간주하고 호출한다. 응답·도구 사용·기억 참조는 Hermes 쪽에서 일어나고, 결과만 채팅 화면으로 돌아온다.

## 설치 핵심

- Hermes 측: `~/.hermes/.env`에 `API_SERVER_ENABLED=true` + `API_SERVER_KEY=…` 후 `hermes gateway run`. 로그에 `[API Server] listening on http://127.0.0.1:8642` 확인.
- Open WebUI: Docker 권장 (`ghcr.io/open-webui/open-webui:main`). 포트 `3000:8080`, `OPENAI_API_BASE_URL=http://host.docker.internal:8642/v1` 환경변수로 Hermes Gateway를 가리킨다.
- 첫 접속 사용자가 admin이 된다.

## 데모 가치

비개발자에게 "터미널이 아닌 웹 채팅 화면"으로 Hermes의 역할형 에이전트(분석·정리·작성)를 한 번에 보여줄 수 있다. 본 볼트의 [[global/glen/concepts/ATOMOS]] 컨텍스트에서는 매장·SV·브랜드·본사 4종 비서를 시연하는 입구로 활용 후보.

## 채널별 역할 분담 (Hermes 채널 모델)

| 채널 | 적합 용도 |
|---|---|
| Open WebUI (웹) | 데모·교육·세일즈 시연. 비개발자 친화. |
| Slack | 실제 팀 업무 채널 운영, 결과 공유 |
| CLI | 빠른 진단·로컬 작업 |
| cron | 무인 자동 실행 (Daily Briefing 등) |

→ "채널을 많이 늘리는 것"이 아니라 "어떤 업무를 어느 입구에서 받을지" 결정의 문제.

## 본 볼트 적용 시 고려

- Open WebUI는 별도 프로젝트라 Hermes의 공식 기능이 아니다 — 외부 UI 연동 가이드 수준.
- Docker 없이도 가능하나 설치 부담 ↓ 위해 Docker 권장.
- Open WebUI를 붙인다고 역할형 에이전트가 자동 생기지 않는다. 역할 분담은 Hermes의 profile·Skill·toolset·위임 규칙으로 별도 설계해야 한다. Open WebUI는 결과를 **보여주는** 인터페이스일 뿐.
- API key·OAuth 토큰을 공유 문서·스크린샷에 노출하지 않도록 주의 (예시값 `<example-api-server-key>` 사용).

## 참고

- 공식: https://github.com/open-webui/open-webui
- 컨테이너 이미지: `ghcr.io/open-webui/open-webui:main`
- 원문 가이드: [WikiDocs 346918](https://wikidocs.net/346918)

## 관련

- [[global/glen/concepts/Hermes-Agent]]

## 출처(원본)

- Clippings/05-11. Hermes Agent Gateway로 Open WebUI 붙이기
