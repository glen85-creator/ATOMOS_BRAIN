# 외부 컨텍스트 자동 귀속 — 날씨(weather) MCP 슬라이스 설계

> 상태: **설계 — 사용자 리뷰 대기.** 2026-06-25.
> 부모: `2026-06-20-pipeline-redesign-design.md` §3c(컨텍스트 데이터 레이어). 첫 소스 = **날씨만**(글렌 결정). 캘린더·상권은 후속.

## 0. 목적 / 합격선
- **목적**: Hermes 단일역할 분석이 매출 이상의 "왜"를 **점주에게 묻는 대신**, **그날 그 매장의 날씨를 자동 조회**해 **외부요인(우천·폭설·한파) vs 내부요인**을 귀속. 과잉반응 방지 + 진단 신뢰성↑.
- **합격선(e2e)**: 매출 이상 1건을 run-v2로 분석 시, 분석이 `context_weather`를 **실제 호출**(call_log)하고, 진단문이 그날 날씨를 인용해 외부/내부 귀속을 명시(예: "6-24 강수 30mm → 우천 외부요인 가능성, 내부조치 보류 권고" 또는 "맑음 → 내부요인 조사 전환"). confidence/risk에 반영.
- 발송·실행 변경 없음. 옛 스택 무관.

## 1. 현 상태 (origin/main 기준)
- MCP 서버(`app/mcp_server/`): `tools.py`의 `_<tool>_impl` + `server.py` `@mcp.tool` 등록. 현재 노출 = `knowledge_search`·`data_sales_history`. 세션(execution_id·store_id=**st_id**·dept·brand_id)은 `context.current_session` contextvar(검증된 세션토큰), `_require_session()`로 취득. `_log_call(...)` → `atomos_mcp_call_log`. `_client()` = supabase.
- 날씨 데이터: `weather_daily`(stn_id·obs_date·**sum_rn**강수·snow_cm·avg/max/min_ta·iscs현상). 매장→관측소 = `stn_for_store(st_uid)`(weather.py). ⚠️ **st_uid(POS) 인자** — 세션 store_id는 **st_id(마스터)** → `store_master_v2.pos_st_uid`로 st_id→st_uid 변환 필요(마스터 2축, [[project_master_data_onboarding]]). `KMA_SERVICE_KEY`(Railway egress OK).
- 분석 프롬프트(`hermes_prompt.py`): 단계별 도구호출 지시(1 knowledge_search → 2 data_sales_history → 3 그라운딩 진단 → 4 tool_tag 매핑). `hermes_runner` 무결성: knowledge_search 실호출(call_log delta) 검증.
- `_TOOLSETS="atomos"`(서버단위) — 새 도구는 같은 서버에 등록되면 자동 노출.

## 2. 슬라이스 범위
### S1 · MCP 도구 `context_weather`
- `app/mcp_server/tools.py`: `_weather_context_impl(date: str | None = None) -> dict`. 세션 store_id(st_id) 취득 → **st_id→st_uid→stn_for_store→stn_id** 해소 → `weather_daily`[stn_id, date] 조회. `date` 미지정 시 execution의 trigger_context.check_date 사용(세션/조회). 반환: `{date, stn_id, found, rain_mm(sum_rn), snow_cm, avg_temp, max_temp, min_temp, phenomena(iscs), note}` + 간단 분류 `is_adverse`(예: 강수≥10mm or 적설>0 or 한파/폭염 임계) — 결정론, 데이터 없으면 `found:false`(환각 금지).
- `server.py`: `@mcp.tool`로 `context_weather` 등록(read-only, 스코프=세션 매장 한정). `_log_call(tool="context_weather", ...)`.
- 순수·읽기전용·스코프·로그 — 기존 도구 패턴 동일. raw SQL/외부쓰기 없음.

### S2 · 분석 프롬프트 배선
- `hermes_prompt.py` 작업절차에 단계 추가: "**context_weather 도구를 호출**해 감지 기준일의 날씨를 확인하라. 강수·적설·이상기온이면 **외부요인 가능성**을 진단·confidence에 반영하고, 평범하면 내부요인 조사로 기운다. 날씨 데이터 없으면(found:false) 그 사실을 risk에 적고 외부귀속을 단정하지 마라(그라운딩)."
- 진단 출력이 날씨를 인용하도록 유도(외부요인%/내부요인% 또는 서술적 귀속). 기존 스키마(diagnosis·proposed_actions·confidence·risk) 유지.

### S3 · (선택) 무결성
- knowledge_search처럼 context_weather 실호출 강제는 **이번 슬라이스 미포함**(프롬프트 권고까지). 날씨가 모든 도메인에 필수는 아니므로 강제보다 권고. 후속 검토.

## 3. st_id→stn 매핑 (핵심 디테일)
- 세션 store_id = st_id(예: ST-ET-GR-0001). `stn_for_store`는 st_uid. → 도구가 `store_master_v2`에서 st_id→pos_st_uid(st_uid) 조회 후 `stn_for_store(st_uid)`. pos_st_uid 미설정 매장이면 stn 해소 실패 → `found:false`(정직). (구현 시 `stn_for_store`가 st_id도 받게 오버로드할지 검토.)

## 4. 범위 외
캘린더(공휴일)·상권 컨텍스트(후속 소스) · context_weather 실호출 무결성 강제 · 외부요인 정량 모델(상관계수 자동 산출) · 발송/실행/등급 변경 · 옛 스택.

## 5. 검증
- **pytest**: `_weather_context_impl`(st_id→stn→weather 조회·found 분기·is_adverse 분류; supabase/stn_for_store monkeypatch) + server 등록(도구 surface 테스트). 회귀: 기존 mcp/hermes 테스트 불변.
- **e2e(글렌 트리거)**: run-v2 on a sales anomaly → `atomos_mcp_call_log`에 `context_weather` 실호출 + 진단문에 날씨 인용·외부/내부 귀속 확인.

## 6. 미결
- `is_adverse` 임계(강수 mm·적설·기온) 구체값 — plan에서 결정(보수적 기본 + 주석).
- 공휴일 데이터 소스(후속 캘린더 슬라이스 선결).
