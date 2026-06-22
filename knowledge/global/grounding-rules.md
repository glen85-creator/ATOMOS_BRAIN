---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 분석 그라운딩 규칙
---

# 분석 그라운딩 규칙

- 제공된 evidence 수치와 도구로 조회한 데이터만 근거로 사용한다. 외부 추정·일반론으로 수치를 만들지 않는다.
- 모든 결론은 인용한 수치(z, dod_delta_pct, mom_delta_pct, gross, mu 등)와 연결한다.
- 외부 요인(휴무·날씨·행사) 가능성이 있으면 단정 대신 "확인 필요"로 표시한다.
- 제안 액션은 반드시 실행 가능한 안전도구 태그(tool_tag) 중 하나에 매핑한다.
