# ATOMOS_OFFICE 조직 설계서 — AI 본사 캐노니컬 정의

> **버전**: v1.1 (2026-06-13 — 13슬롯 org 정식화) / **상태**: 로스터 승인됨 (브레인스토밍)
> **위상**: ATOMIC 콘솔이 감지한 일을 위임받는 **AI 본사(Paperclip 조직 = ATOMOS_OFFICE)** 구성의 **단일 진실 원천(SSOT)**.
> 에이전트 로스터·모델·페르소나(SOUL)·툴셋(TOOLS)·하트비트(HEARTBEAT)·실행/기록/학습 원리를 한 곳에 정본화한다.
>
> **이 문서가 인용하는 기존 확정 (재설계 아님)**:
> - `hbs-dashboard/docs/superpowers/plans/2026-06-03-atomic-engine-paperclip-hermes-adr.md` — 분할 모델(앱=입장게이트 / Paperclip=실행거버넌스) ★정본 ADR
> - `hbs-dashboard/docs/superpowers/specs/2026-06-08-atomic-detect-propose-tool-matrix-design.md` — 6도메인 감지·제안·도구 매트릭스 + §5 모델 배치
> - `hbs-dashboard/docs/superpowers/plans/2026-05-30-atomic-blueprint.md` — 실행 루프 5단계·기록 테이블 계약
> - `hbs-dashboard/docs/superpowers/specs/2026-06-08-s1-paperclip-dispatch-checkpoint.md` — terminal-native 디스패치 실증
> - `hbs-dashboard/docs/superpowers/specs/atomic-s0-state-audit.md` — VPS 실측
> - `hbs-dashboard/docs/HERMES_AI_HQ_MODEL_PLAN.md` — 예산 산출 (참고용으로 격하, §5 참조)
> - `hbs-dashboard/docs/superpowers/specs/2026-06-13-atomos-org-roster-charter-design.md` — 13슬롯 org 로스터 정식화 설계 (본 갱신의 근거)
>
> **표기**: ✅ 기존 확정 인용 / 🟡 본 문서 신규 제안(승인 필요) / 🔴 미결(§13)

---

## 0. 이 문서가 해결하는 것

조직 정의가 4곳(VPS 파일시스템 / 모델플랜 문서 / `registry.ts` / 비서설계 문서)에 흩어져 충돌·공백이 방치된 상태를 종결한다.

| 문제 | 해소 위치 |
|---|---|
| "4비서 vs 6역할 vs 8스킬" taxonomy 충돌 | §1 레이어 분리 |
| 모델 배치 2개 버전 충돌 (06-03 모델플랜 vs 06-08 매트릭스 §5) | §5 정본 확정 |
| "팀원"의 실체 모호 (원격 Hermes profiles vs Paperclip 슬롯) | §1-3 정본 확정 |
| 로스터 불일치 (VPS 6슬롯·어댑터 혼재 vs 타깃 13슬롯) | §3 + §12 마이그레이션 |
| 페르소나/SOUL/TOOLS/HEARTBEAT 정본 부재 (VPS에만 존재, 휘발 위험) | §4 org-as-code |
| 하트비트/스케줄 체계 부재 (routine 0, 전원 수동 wakeup) | §6 |
| 브리지 수동 스크립트 (`~/atomic-s1-exec/*.sh`) | §7-3 서비스화 |
| 기록 절반(비용 추정·propose 자동기록 누락) | §8 |
| 학습 미구현 (success_score 공식 부재) | §9 |

---

## 1. 용어·레이어 정리 — taxonomy 충돌 해소 🟡

기존 문서들의 "4비서 / 6역할 / 8스킬"은 충돌이 아니라 **서로 다른 3개 층**이다. 이를 공식화한다:

```
[L-USER]  Atomic 비서 (4종: 매장·SV·브랜드·본사)
          = 사용자 옆의 대화 인격. hbs-dashboard FE 레이어.
          = ATOMIC_ASSISTANT_DESIGN v1.1 §1 소관. ATOMOS_OFFICE와 별개. (본 문서 범위 밖)
              │ 요청·승인
              ▼
[L-ORG]   ATOMOS_OFFICE 에이전트 (= Paperclip 슬롯, 본사 "직원")     ← ★ 본 문서의 대상
          = §3-2 로스터 13슬롯 (CEO·CTO·ANALYST·MARKETING·RESEARCHER·HERMES + SCM·FINANCE·CRM·CONTENTS·ARCHIVES·BRAND_DIVISION·VISION)
          = 감지된 일(이슈)을 받아 분석·제안·실행하는 주체
              │ 호출
              ▼
[L-TOOL]  Skill / 도구 (sales_analyze, content_copy, review_respond …)
          = 작업 단위. 매트릭스 설계 §3 도구 레지스트리 소관.
          = registry.ts 8스킬은 이 층의 FE 메타데이터.
```

### 1-2. 거버넌스 경계 (✅ ADR 인용 — 불변)

- **앱(FastAPI+콘솔) = Admission Gate**: risk/confidence 결정론 판정, approve/reject/finalize, `audit_log`·`decision_type`, 학습 write-back. FE는 `strategyExecApi` 계약만 본다.
- **ATOMOS_OFFICE(Paperclip) = Execution Governance**: 에이전트 라이프사이클, 월예산(cost) 강제, 실행 디스패치, tool-call/활동 텔레메트리.
- **스파인**: `strategy_executions` 1행 ↔ Paperclip 이슈 1개 (`paperclip_issue_id` 링크).

### 1-3. "팀원"의 실체 = Paperclip 에이전트 슬롯 🟡 (정본 확정)

S0 설계의 "팀원 = 원격 hermes-agent 컨테이너의 profiles 4개(atomos-atomic·aiteam-tom·maketingteam-mimi·designteam-jhon)" 관점을 **폐기**하고, S1에서 실증된 경로를 정본으로 한다:

| | 정본 (채택) | 보조/폐기 검토 |
|---|---|---|
| 실체 | **Paperclip 에이전트 슬롯** — `hermes_local` 어댑터가 Paperclip 컨테이너 **로컬 hermes 바이너리**(`/paperclip/.local/bin/hermes`, v0.15.1, OPENROUTER_API_KEY)를 spawn | 원격 `hermes-agent-dq4x` 컨테이너 (profiles 4개, gpt-5.5/openai-codex **토큰 만료**) |
| 용도 | 본사 직원 전원 | cron/게이트웨이 등 보조 인프라로만 잔존 검토. ATOMOS 미션에 사용 금지 🔴 폐기 여부 §13-2 |

근거: S1 체크포인트 실측 — terminal-native(슬롯이 자기 이슈를 curl로 fetch)가 "Paperclip이 의도한 유일 정상 경로"로 확인됨. 원격 profiles 트랙은 토큰 만료 상태로 방치돼 있고 ATOMOS 루프에 관여한 적 없음.

---

## 2. 현재 실측 상태 (2026-06-10 기준)

**인프라**: VPS `paperclip-host`(Hostinger Docker) / Paperclip `paperclip-sab7-paperclip-1` v2026.517.0 / 회사 `88adce92-bd11-4655-a70a-05d728861c3a` (admin: glen_85@hbscom.com) / 2vCPU·8GB·GPU없음 → 클라우드 provider 라우팅 확정 (✅ S0).

**로스터 실태 — 6슬롯 등록, 실증 1**:

| 슬롯 | UUID | 어댑터 | 상태 | 실증 |
|---|---|---|---|---|
| ATOMOS_CEO | `5e2ad936-…` | hermes_local | idle | ✗ (instructions 번들만) |
| ATOMOS_CTO | `1e8561b3-…` | hermes_local | idle | ✗ |
| ATOMOS_ANALYST | `87031503-…` | codex_local | idle | ✗ |
| ATOMOS_RESEARCHER | `7329c63d-…` | codex_local | idle | ✗ |
| ATOMOS_MARKETING | `879bc246-…` | codex_local | idle | ✗ |
| **ATOMOS_HERMES** | `6d44aa65-…` | hermes_local | **paused** | **✅ 풀사이클** (deepseek-v4-flash·terminal·$5/월) |

**실증된 루프(S1)**: 감지 → 이슈 생성(본문=매장데이터) → wakeup → 에이전트가 이슈 curl·분석·JSON 코멘트 → 브리지 → `/api/atomic/engine/propose`(paperclip_issue_id 링크) → 콘솔 게이트·승인 → 실행 이슈 → deliverables → step-output×3·kpi-baseline·agent-run → 타임라인 가시화. (execution `bb759785` 검증)

**미가동**: routine 0개·ATOMOS cron 0개, 브리지=수동 쉘 스크립트, 어댑터 ctx-path 패치 휘발성(컨테이너 재생성 시 소실), measure-kpi/finalize는 시간 게이트(6~7월 마감) 대기.

---

## 3. 조직 구조 (정본 로스터)

### 3-1. 조직도 🟡 (13슬롯, 2계층)

```
                         ┌─────────────────┐
   [앱 Admission Gate    │   ATOMOS_CEO    │  오케스트레이터·영업 첫 관문
    통과분만 이슈 유입]   │  (총괄 두뇌)    │  (조율만·실행 금지, 2+도메인 분해)
                         └────────┬────────┘
        ┌──────────┬──────────┬───┴────┬──────────┬──────────┬──────────┐
        ▼          ▼          ▼        ▼          ▼          ▼          ▼
   ATOMOS_CTO  BRAND_      ANALYST  RESEARCHER CRM_TEAM   SCM_TEAM   FINANCE_TEAM
   (기술·DB·   DIVISION    [sales]  (상권·시장) (메시지·   [cogs]     [cost]
    API)       (브랜드우산)  진단              카카오·draft) 식자재     회계·손익·draft
        │          │
        ▼      ┌───┴────────┐
   ARCHIVES_   ▼            ▼
   TEAM     MARKETING   CONTENTS_STUDIO
   (기록·    [review]    (콘텐츠·발주·draft
    WIKI·    광고·응대     구 DESIGNER 흡수)
    쓰기전용)

   + ATOMOS_HERMES (범용 폴백 — 미활성 도메인 임시·긴급, CEO 직속·상시 on-demand)
   + ATOMOS_VISION_AI_TEAM (카메라·OCR — not-created, CEO 직속)
```

### 3-2. 캐노니컬 로스터 — 13슬롯 (🟡 2026-06-13 org 정식화)

모델 배치 기본은 매트릭스 §5 승계, 비용 최소화로 deepseek-v4-flash 디폴트. 상세 메타는 `org/roster.yaml`.

| # | 슬롯 | reports_to | 담당 도메인 | 운영 모델 (타깃) | v1 상태 | 발송 |
|---|---|---|---|---|---|---|
| 1 | ATOMOS_CEO | — | 2+도메인 분해 | kimi-k2.6 | paused | — |
| 2 | ATOMOS_CTO | CEO | 운영 health | deepseek-v4-flash | paused | — |
| 3 | ATOMOS_ARCHIVES_TEAM | CTO | 전 사건 기록 | deepseek-v4-flash | not-created | 쓰기전용 |
| 4 | ATOMOS_BRAND_DIVISION | CEO | MKT/CONTENTS 조율 | deepseek-v4-flash | not-created | — |
| 5 | ATOMOS_MARKETING | BRAND_DIVISION | review | deepseek (→sonnet-4.6) | paused (승격2) | — |
| 6 | ATOMOS_CONTENTS_STUDIO | BRAND_DIVISION | MKT 산출 실물화 | deepseek +nano-banana-2/veo-3.1 | not-created | needs_external |
| 7 | ATOMOS_RESEARCHER | CEO | cost·cogs 협업 | gemini-3-flash | paused | — |
| 8 | ATOMOS_CRM_TEAM | CEO | review 협업 | deepseek-v4-flash | not-created | needs_external |
| 9 | ATOMOS_SCM_TEAM | CEO | cogs | deepseek-v4-flash | not-created | — |
| 10 | ATOMOS_FINANCE_TEAM | CEO | cost | deepseek-v4-flash | not-created | needs_external |
| 11 | ATOMOS_ANALYST | CEO | sales | deepseek-v4-flash (→sonnet-4.6) | **active (승격1 완료)** | — |
| 12 | ATOMOS_HERMES | CEO | 미활성 도메인 폴백 | deepseek-v4-flash | active-on-demand | — |
| 13 | ATOMOS_VISION_AI_TEAM | CEO | contract OCR | gemini-3-flash | not-created | — |

*구 DESIGNER_IMAGE/VIDEO → CONTENTS_STUDIO 흡수. 구 ATOMOS_VISION → VISION_AI_TEAM 리네임.*

### 3-3. 활성화 원칙 — 린 스타트 (✅ S1 승계 + 🟡 13슬롯 갱신)

- **타깃 로스터 정식화**: 13슬롯을 헌장에 박되, 각 팀 instruction 4파일(SOUL/AGENTS/TOOLS/HEARTBEAT)+adapter.yaml+Paperclip provision은 **그 팀 활성화 시** 작성(현 6슬롯만 `org/agents/` 존재).
- **v1 활성**: ANALYST(sales, 2026-06-12 skeleton 실증) + HERMES(범용 폴백 on-demand). 나머지 paused/not-created = $0.
- **승격 게이트**: ①도메인 `data_status=available` ②`tool_readiness≥partial` ③월 5건↑ 이슈 ④예산 책정. 순서(`roster.yaml` promotion_order): ANALYST(완료)→MARKETING→SCM→FINANCE→RESEARCHER→BRAND_DIVISION→CTO→CEO→CONTENTS→CRM→VISION→ARCHIVES.
- **관리자 노드**(BRAND_DIVISION·CTO)는 산하 위임 시 활성 필요 — 산하 팀 승격과 함께.
- **codex_local 잔재**(MARKETING·RESEARCHER)는 활성화 시 hermes_local 전환.

### 3-4. 감지 도메인 → 담당 팀 (라우팅 입력) 🟡

| 감지 도메인 | 담당 팀 | 협업 (fan-out 힌트) | 현 감지 상태 |
|---|---|---|---|
| sales 매출급락 | ANALYST | — | 라이브·디스패치 ✅ |
| cogs 원가·공급가급등 | SCM_TEAM | P&L=ANALYST | 감지 ✅·디스패치 ✗ |
| cost 공과금·계약만료 | FINANCE_TEAM | 계약 리서치=RESEARCHER | 감지 ✅·디스패치 ✗ |
| review 평판 | MARKETING | 고객 발송=CRM | 감지 ✅·디스패치 ✗ |
| opportunity 기회 | (보류) | — | 코드 실체 없음 |

→ (b) 다음 레이어가 이 매핑으로 `elayer_dispatch.py`의 sales→ANALYST 하드코딩을 도메인→슬롯 테이블로 대체. 미활성 도메인은 HERMES 폴백 or skip.

### 3-5. 발송 게이트 (draft-only) 🟡

CRM(카카오)·FINANCE(손익서)·CONTENTS(실물 발주)는 `send_gate: needs_external`. 외부 발송 권한 Pack 승격 전까지 **초안 전용** — 산출물은 검토용 초안까지, 실제 발송은 Pack 충족 후. (헌장 "발송 금지·초안만" 정책 §11 준수)

### 3-6. ARCHIVES retrieval 🔴

terminal 전용이라 런타임 위키 pull 불가 → ARCHIVES는 **1단계 쓰기전용 기록자**(사건·산출물 로깅)로 출범. 읽기는 (a)FastAPI retrieval API or (b)CTO/DB 위임 — 후속(§13-11). GLEN_WORK 세컨드브레인과 역할 경계 후속.

---

## 4. 에이전트 정의 표준 — org-as-code 🟡

### 4-1. 원칙

**조직 정의는 이 리포(ATOMOS_BRAIN)가 정본**이고 VPS는 배포 타깃이다. VPS 파일시스템에만 존재하는 instructions 번들(휘발·추적불가)을 역수입해 정본화하고, 이후 변경은 리포 → VPS 단방향 배포만 허용한다.

### 4-2. 리포 구조

```
ATOMOS_BRAIN/
├── README.md
├── docs/
│   └── ATOMOS_OFFICE_ORG_DESIGN.md      # 본 문서 (조직 헌장)
├── org/
│   ├── company.yaml                      # 회사 메타: company_id, 정책 플래그
│   ├── roster.yaml                       # §3-2 로스터 표의 기계가독본 (배포 입력)
│   └── agents/<SLOT_NAME>/
│       ├── SOUL.md                       # 정체성·가치·톤·금지 (불변에 가까움)
│       ├── AGENTS.md                     # 운영 매뉴얼: 이슈 처리 절차·출력 JSON 계약·보고선
│       ├── TOOLS.md                      # 허용 toolsets·terminal 플레이북·외부 Pack
│       ├── HEARTBEAT.md                  # wake 조건·점검 체크리스트·침묵 규칙
│       └── adapter.yaml                  # adapterType·provider·model·toolsets·예산·status
├── bridge/                               # 디스패치 브리지 (§7-3) — atomic-s1-exec 스크립트 승계
├── patches/                              # hermes-paperclip-adapter ctx-path 패치 (§7-4 영구화)
└── deploy/                               # 리포 → VPS 동기화 (Paperclip REST PATCH)
```

### 4-3. 파일별 스키마

| 파일 | 내용 | 변경 빈도 |
|---|---|---|
| `SOUL.md` | ① 한 줄 정체성 ② 가치 서열 (정확성 > 비용절감 > 속도) ③ 톤 (한국어, 외식업 실무) ④ **금지** — 지정 플레이북 외 terminal 명령 금지, 시크릿 출력 금지, 추측을 사실처럼 보고 금지, 예산 초과 예상 시 중단·보고 | 낮음 |
| `AGENTS.md` | ① 보고선(reportsTo) ② 이슈 처리 절차 (수령→분석→산출→코멘트→done) ③ **출력 JSON 계약** (§7-2) ④ 에스컬레이션 조건 (저신뢰·고위험 → 사람) | 중간 |
| `TOOLS.md` | ① 허용 toolsets (v1: `terminal`만) ② terminal 4단계 플레이북: `curl 이슈 fetch → 분석 → JSON 코멘트 POST → 이슈 done` ③ 도구별 호출 예시 ④ Pack 자격증명은 환경변수 참조만 | 중간 |
| `HEARTBEAT.md` | ① wake 출처별 행동 (issue 배정 / routine / 수동 wakeup) ② 기상 시 체크리스트: 내 이슈 큐 확인 → 없으면 **즉시 침묵 종료** (토큰 낭비 금지) ③ 세션 연속성 (persistSession) 활용 규칙 | 낮음 |
| `adapter.yaml` | Paperclip PATCH 페이로드 원본: `adapterType: hermes_local`, `provider: openrouter`, `model`, `toolsets`, `persistSession: true`, `hermesCommand: /paperclip/.local/bin/hermes`, `budgetMonthlyCents`, `status` | 중간 |

### 4-4. 실증 예시 — ATOMOS_HERMES (S1 검증분 승계)

- SOUL: "ATOMOS 본사의 통합 실행 에이전트. 이슈 본문이 작업·출력 스키마를 지정한다."
- TOOLS: terminal만. 플레이북: `curl -s {{paperclipApiUrl}}/issues/{{taskId}}` → 분석 → `POST .../comments` (JSON) → 이슈 done. **4단계 외 명령 금지** (SOUL 금지 조항과 이중 잠금).
- 페르소나 원문: `~/atomic-s1-exec/persona.txt` (제네릭 실행, 671자) — M1에서 리포로 회수.

---

## 5. 모델 정책

### 5-1. L1 — 슬롯 기본 모델 (✅ §3-2 표 = 매트릭스 §5)

### 5-2. L2 — 미션/스텝 오버라이드 (✅ 매트릭스 인용)

`strategy_scenario.recommended_steps[].model`로 스텝별 모델 지정 가능. 시나리오가 슬롯 기본값을 이긴다.

### 5-3. 에스컬레이션 (✅ 매트릭스 인용 + 🟡 수치)

저신뢰(confidence<0.5)·고위험(risk=high↑)·산출물 상호충돌 시 상위 tier(Gemini 3.1 Pro 등)로 1회 재시도. **전체 호출의 ≤5% 하드캡**. 초과 시 사람 에스컬레이션.

### 5-4. 06-03 모델플랜과의 관계 🟡

`HERMES_AI_HQ_MODEL_PLAN.md`의 Qwen3(전략)·Solar(한국어 CS) 배치는 **채택하지 않는다** (매트릭스 §5가 후행·시나리오 정합). 단 동 문서의 ①비용 시나리오 산식(절약 $75~85 / 표준 ~$111 / 헤비 ~$200) ②Kimi 호출 억제 레버 ③PII 마스킹(`mask.ts` 선행)·무료티어 금지 원칙은 **유효 승계**.

### 5-5. 단가표 운영 (✅ S1 #5 인용)

`ai_model_pricing`(model PK, input/output $/1M) = 비용 추정 기준. **신규 모델 활성화 시 OpenRouter 실단가로 시드 필수**. deepseek placeholder 교정 TODO 승계.

---

## 6. 하트비트·스케줄 체계 🟡

### 6-1. wake 출처 3종 (✅ 실측 인용)

Paperclip에 "N분마다 전 에이전트 기상" 루프는 **없다**. wake는 ① routine schedule ② issue 배정/모니터 ③ 수동 `wakeup`/`heartbeat/invoke` 뿐. → **idle/paused 슬롯의 상시 비용 = 0** (LLM 호출 없음). 이것이 비용 구조의 근간.

### 6-2. v1 정책 — issue-driven (event-driven)

- **상시 폴링 금지**. 감지는 FastAPI 쪽(detection_settings·캐시)이 수행하고, **발화 시에만** 브리지가 이슈 생성 + wakeup (§7-3).
- 슬롯은 작업 완료 후 **재-pause** (S1 보안 위생 승계).
- 모델플랜의 "Kimi 오케스트레이터 호출 억제" 레버와 정합 — CEO 슬롯은 다중 슬롯 조율이 실제 필요해질 때까지 기상시키지 않는다.

### 6-3. routine 최소 운용 (S2+)

| routine | 슬롯 | 주기 | 내용 |
|---|---|---|---|
| daily-health | CTO | 1회/일 | 어댑터 패치 생존·게이트웨이·예산 소진율 점검 → 이상 시에만 보고 |
| weekly-retro | ANALYST | 1회/주 | 종결 execution 회고 요약 (→ §9 학습 입력) |

그 외 routine 신설은 비용 다이얼 영향 평가 후. ⚠️ 원격 hermes-agent의 기존 cron(`daily-glen-work-git-sync`)은 ATOMOS와 무관 — 건드리지 않음.

---

## 7. 실행 원리

### 7-1. 표준 루프 — 단계 × 소유자 (✅ ADR·B0 인용, 🟡 표준화)

| 단계 | 소유 | 메커니즘 |
|---|---|---|
| 감지 | 앱 (FastAPI) | detection EP·캐시·`detection_settings` 노브 (6도메인) |
| 트리거 판정 | 브리지 | critical/이상 발화 + `dedup_key` 멱등 |
| 위임 | 브리지 → ATOMOS_OFFICE | Paperclip 이슈 생성(본문=데이터+출력 스키마) + 슬롯 wakeup |
| 분석·제안 | 슬롯 (terminal-native) | 이슈 curl → 분석 → **JSON 코멘트** (§7-2 계약) |
| 회수·등록 | 브리지 → 앱 | 코멘트 파싱 → `POST /api/atomic/engine/propose` (risk/confidence 태깅, `paperclip_issue_id` 링크) |
| 입장게이트 | **앱** | `autonomy_policy` 결정론 판정 → AUTO / HUMAN(콘솔 승인) |
| 실행 | 슬롯 (실행 이슈) | 승인된 액션 → 실행 이슈 생성 → deliverables 산출 |
| 기록 | 브리지 → 앱 | `step-output`·`agent-run`·`kpi-baseline` (X-Engine-Token) |
| 측정·종결 | 앱 | `measure-kpi` → `finalize` (verdict) — 시간 게이트 |
| 학습 | 앱 | §9 |
| 롤백 | 앱+Paperclip 2-파트 | `audit_log.before_data` 역적용 + 외부발송 보상 (✅ ADR §5) |

### 7-2. 제안 JSON 계약 🟡 (S1 산출물 정형화)

에이전트 코멘트는 아래 스키마를 따른다 (브리지 파서·`/propose` 입력의 계약):

```jsonc
{
  "schema_version": 1,
  "kind": "proposal",            // proposal | deliverable
  "st_uid": "I22092100048",
  "diagnosis": "…",              // 진단 요약
  "actions": [{ "priority": "긴급|단기|중기", "title": "…",
                "what": "…", "how": "…", "owner": "…", "eta": "…",
                "expected_effect": "…" }],
  "risk": "low|med|high",
  "confidence": 0.0,
  "est_cost_usd": 0.0            // ⚠️ KRW 착각 방지: USD 명시 (S1 사고 승계)
}
```

### 7-3. 브리지 서비스화 🟡

> **개정 (2026-06-10, enrich 전환)**: FastAPI main에 **B층**(`tasks.auto_detect_sales` 05:30 —
> 감지 즉시 규칙 기반 pending 제안 생성, feat/domain-auto-trigger)이 머지되면서 위임 단계의 구조가 2층이 됐다.
> 브리지는 **신규 제안을 만들지 않고 B층이 만든 행을 보강(enrich)** 한다: B층 카드(05:30, canned 액션)
> → 브리지(06:00)가 Paperclip AI 분석으로 같은 행의 ai_recommendation 교체 + paperclip_issue_id 링크.
> 중복이 구조적으로 불가능하며 "1 execution ↔ 1 Paperclip 이슈" 스파인 원칙이 같은 행 위에서 성립한다.
> 상세: `bridge/README.md` / FastAPI `FEATURES.md` §10.

현재 수동 스크립트(`~/atomic-s1-exec/*.sh`)를 **FastAPI Celery 태스크로 승격**한다. 🔴 위치 최종확정 §13-4

- **권고 근거**: 감지 캐시·detection_settings·엔진 EP·Redis/beat 인프라가 전부 FastAPI(Railway)에 있음. VPS 상주 데몬은 단일실패점+패치휘발 리스크.
- 흐름: beat 주기(예: 1h, 감지 갱신 주기와 동기) → 발화 스캔 → `dedup_key` 신규분만 이슈 생성+wakeup → 코멘트 폴링(간격 30s·타임아웃 10m) → `/propose` → 슬롯 재-pause.
- 인증: Railway에 `PAPERCLIP_API_TOKEN`(board 발급) 신설 🔴 §13-4. admin 비밀번호 직접 사용 금지.
- 스크립트 자산은 `bridge/`로 승계 (healthcheck/configure/wakeup/poll/bridge/repause).

### 7-4. 어댑터 패치 영구화 🟡

`hermes-paperclip-adapter` ctx-path 패치(`execute.js` 5곳, `{{taskId}}` 주입 — S1 필수 전제)를 `patches/`에 보관하고, `deploy/`에 컨테이너 재생성 후 자동 재적용 스크립트(`.paperclip-patches`) 포함. 업스트림 PR 제출 검토 🔴 §13-5.

---

## 8. 기록 원리

### 8-1. 기록 계약 — 누가 어디에 무엇을 (✅ 확정 인용 + 🟡 갭 보강)

| 저장소 | writer | 시점 | 내용 |
|---|---|---|---|
| `strategy_executions` (스파인) | 앱(`/propose`·approve·finalize) | 제안~종결 | status 상태기계·`paperclip_issue_id`·measured_impact |
| `strategy_step_log` | 앱(approve 전개) + 브리지(`step-output`) | 실행 | 스텝 산출물·cost_amount |
| `kpi_snapshot` | 브리지/앱 (`kpi-baseline`·`measure-kpi`) | 승인 직후·측정기 | baseline/final + delta + verdict_suggested |
| `agent_run` | 브리지 (`/engine/agent-run`) | 슬롯 런마다 | model·token_in/out·cost(estimated 플래그)·platform |
| `strategy_cost` | 앱(수동) + step-output 연동 | 수시 | 실행 비용 집계(`total_cost_actual` 재집계) |
| `audit_log` | 앱 전용 | 결정마다 | before/after_data·decision_type(auto/human)·proposal_hash |
| `strategy_learning` | 앱(finalize) | 종결 | §9 |
| Paperclip(heartbeat_runs·issue_comments·activityLog) | Paperclip 원천 | 자동 | 실행측 텔레메트리 — 앱 테이블로 **투영**(원천 아님) |

**원칙**: 콘솔이 보는 진실 = 앱 테이블. Paperclip 기록은 투영 소스. `is_auto` 판정은 영원히 `audit_log` 기준 (✅ ADR §4).

### 8-2. 비용 기록 — 추정에서 실측으로 🟡

- 현행(✅): Paperclip/hermes가 토큰 미보고 → `ai_model_pricing` 단가표 × 추정 토큰, `estimated` 플래그 + 콘솔 "추정" 칩.
- 개선 경로: ① 어댑터 stdout에서 hermes usage 파싱 → `heartbeat_runs.usageJson` 백필 ② OpenRouter usage API 일배치 대조 ③ 차이 ±20% 초과 시 단가표 교정 알림. 🔴 우선순위 §13-6.

### 8-3. 기록 갭 봉합 목록 🟡

① propose 자동 agent_run 기록(현재 실행 런만 기록됨) ② `audit_log`에 엔진 이벤트(entity_type='engine') 추가 ③ wakeup→코멘트→propose 상관관계 ID(`request_id`) 일관 전파.

---## 9. 학습 원리 🟡

### 9-1. 종결 판정 (✅ 확정 인용)

`finalize` → `completion_verdict`: achieved(≥+5%) / partial(>-5%) / missed / inconclusive. measured_impact **풀 shape 저장 필수** (축약 시 FE 크래시 — FEATURES §2).

### 9-2. strategy_learning write-back 🟡

- **모든 verdict 기록** (성공만 기록 ✗ — 실패가 더 큰 학습 신호). inconclusive는 score 갱신에서 제외하되 행은 남김.
- 키: (scenario_id, brand_uid) 단위 UPSERT. 매장 단위 세분화는 표본 누적 후.

### 9-3. success_score 갱신 공식 (제안) 🔴 §13-7

```
outcome: achieved=1.0, partial=0.5, missed=0.0   (inconclusive 제외)
score' = score + α·(outcome − score)             (EMA, α=0.3, 초기값 0.5)
```
- 콘솔 노출: 시나리오 제안 카드에 score 배지 → 사람 승인 판단 보조.
- score < 0.3 시나리오는 자동 제안 중단(제안만 백로그) — 다이얼과 연동.

### 9-4. 자율성 승격 (✅ S3a 인용 + 🟡 보강)

5회 연속 사람 승인 → AutonomyDial 후보 추천 (확정). 보강: **후보 조건에 score ≥ 0.6 AND 해당 категории 롤백 이력 0** 추가 제안.

### 9-5. 지식 축적 (회고 → 재사용)

- weekly-retro routine(§6-3)이 종결 execution 요약 생성 → `ATOMOS_BRAIN/knowledge/` 적재 후보 🔴 §13-8 (B0 §5 wiki/RAG 미결 승계).
- best-practice 전파(SC-BP-001, 🌟기회 카드)는 학습의 공간 전파 경로 — 우수 매장 패턴 → 부진 매장 제안.

---

## 10. 예산·비용 거버넌스

### 10-1. 슬롯별 월예산 (Paperclip `budgetMonthlyCents`) 🟡

| 단계 | 슬롯 | 월예산 |
|---|---|---|
| v1 (현행) | HERMES $5 / 나머지 $0~5 paused | 합 ≤ $10 |
| S2 (ANALYST·MARKETING 승격) | HERMES $10 / ANALYST $10 / MARKETING $15 / CEO $20 | 합 ≤ $60 |
| S3 풀가동 | 모델플랜 표준 시나리오 정합 | 합 ~$111 (헤비 $200 캡) |

- Paperclip 예산 = **실행시점 강제** (초과 자동정지) — cost 가드의 집행 주체 (✅ ADR).
- ⚠️ **정정 (2026-06-13)**: Paperclip 어댑터 COST_REGEX가 proposal의 `est_cost_usd`(비즈니스 액션 비용추정)를 LLM 지출로 오긁어 가짜 정지를 유발(ANALYST $350 사례, 실비용 $0.0006). → **Paperclip 예산은 advisory로 격하**, 실비용 SoT = `agent_run`, 실제 캡 = 앱쪽 `autonomy_policy.cost_ceiling`. 돈 얘기하는 전 슬롯 동일.
- `autonomy_policy.cost_ceiling`(scope/category) ↔ 슬롯 월예산 **배분 변환규칙** 🔴 §13-9 (ADR 미결 승계): v1 잠정 규칙 제안 — *category별 ceiling 합 ≤ 담당 슬롯 월예산의 80%* (20% 버퍼).

### 10-2. PII (✅ 모델플랜 승계)

OpenRouter 디스패치 전 `mask.ts` 마스킹 선행. PII 취급 일(CS·정산)은 무료티어 금지.

---

## 11. 보안

| 항목 | 정책 |
|---|---|
| 엔진 쓰기 EP | `X-Engine-Token`=`ATOMIC_ENGINE_TOKEN` fail-closed 403 (✅). 회전 시 Railway Value에 **값만 64자** (오염 사고 재발 방지, FEATURES 승계) |
| terminal+`--yolo` | 승인된 트레이드오프 (✅ S1). 잠금 3중: ①SOUL 금지조항 ②TOOLS 4단계 플레이북 한정 ③작업 후 재-pause. blast 반경 = Paperclip 컨테이너 한정 |
| Paperclip board 자격 | 브리지는 전용 API 토큰 사용 (admin 비번 스크립트 사용 금지) 🔴 §13-4 |
| `autonomy_policy` RLS 0개 | 입장게이트 SoT인데 DB 미강제 — **보안 티켓 우선순위 상향** (✅ ADR §3-4, memory `project_deferred_security`) |
| `/api/atomic/engine/*`·`/api/hq/sim/*` | 실데이터·공개배포 전 인증·역할 게이트 강화 (✅ 승계) |
| 시크릿 | 리포에 값 커밋 금지. `adapter.yaml`은 키 이름만 참조. VPS `/root/.atomos/engine_token`·컨테이너 env가 실값 보관처 |

---

## 12. 마이그레이션 플랜 (현재 → 정본)

| 단계 | 내용 | 산출물 | 게이트 |
|---|---|---|---|
| **M0** | 본 문서 + 리포 골격 (org/·bridge/·patches/·deploy/) | 이 커밋 | 사용자 승인 |
| **M1** | VPS instructions 번들 5종 회수 → `org/agents/` 정본화 + ATOMOS_HERMES persona.txt·s1-exec 스크립트 회수 | agents/ 번들 | VPS 읽기 접근 |
| **M2** | 로스터 정합: codex_local→hermes_local 전환, 모델/예산/툴셋 PATCH, 패치 영구화 | deploy 스크립트 실행 로그 | §13-3 확정 |
| **M3** | 브리지 서비스화 (Celery beat + PAPERCLIP_API_TOKEN) | FastAPI `app/services/atomos_bridge.py`(가칭) | §13-4 확정 |
| **M4** | ANALYST 승격 (D-SALES 1순위) + routine 2종 가동 | 승격 로그·첫 자동 루프 | M2·M3 + 승격 게이트(§3-3) |
| **M5** | 학습 루프 가동: measure-kpi/finalize (6~7월 마감 도래) → strategy_learning → score → 승격 후보 | 첫 verdict·score | 시간 게이트 |

---

## 13. 미결 결정 목록 (사용자 확정 필요 🔴)

| # | 결정 | 선택지 | 권고 |
|---|---|---|---|
| 1 | 모델 배치 정본 | 매트릭스 §5 vs 06-03 모델플랜 | **매트릭스 §5** (본 문서 §3-2 반영) |
| 2 | 원격 hermes-agent 컨테이너 처우 | 보조 잔존 vs 폐기 | 토큰 만료 방치 상태 — glen-work cron만 이전 후 **폐기** |
| 3 | codex_local 3슬롯 전환 | hermes_local 통일 vs 유지 | **통일** (실증 경로·키 1원화) |
| 4 | 브리지 위치·인증 | FastAPI Celery vs VPS cron / 전용 토큰 발급 | **Celery + 전용 board API 토큰** |
| 5 | 어댑터 패치 | 로컬 영구화만 vs 업스트림 PR | 영구화 먼저, PR은 후속 |
| 6 | 비용 실측 | usage 파싱 vs OpenRouter API 대조 vs 현행 추정 유지 | v1 추정 유지 + S2에서 usage 파싱 |
| 7 | success_score 공식 | §9-3 EMA(α=0.3) 채택 여부 | 채택 (단순·설명가능) |
| 8 | 지식 저장소 | ATOMOS_BRAIN/knowledge vs 별도 wiki/RAG | BRAIN 우선, RAG는 증분4 |
| 9 | cost_ceiling↔슬롯예산 변환 | §10-1 잠정 규칙(80%) 채택 여부 | 채택 후 실측 보정 |
| 10 | DESIGNER·vision 슬롯 생성 시점 | 외부 API(이미지/영상/OCR) 계약 시 | S3 후반, D-MKT 데이터 소스 확보 후 |
| 11 | ARCHIVES retrieval 메커니즘 | FastAPI API vs CTO/DB 위임 | 1단계 쓰기전용 출범 후 결정 |
| 12 | CEO 활성화 타이밍 | 2+도메인 분해 수요 vs kimi 비용 | 코드 라우팅으로 버티다 최후 승격 |
| 13 | opportunity 도메인 | 코드 실체 신설 여부 | 수요 확인 후 정의 |
| 14 | 발송 Pack(needs_external) | 카카오/발주 외부 권한·자격 정의 | CRM/FINANCE/CONTENTS 활성화 직전 |

---

## 부록 A. 관련 식별자 (실측)

- 회사: `88adce92-bd11-4655-a70a-05d728861c3a` / Paperclip `paperclip-sab7-paperclip-1` (:54501)
- ATOMOS_HERMES: `6d44aa65-3149-4a0a-a2d2-20de1805bf95`
- 엔진 EP: `/api/atomic/engine/{store-kpi,executions,propose,steps,step-output,kpi-baseline,measure-kpi,agent-run}` (FastAPI `app/api/routes/atomic_engine.py`)
- 콘솔 RPC: `get_atomic_feed` / `get_ai_cost_summary` (`migrations/004`)
- 매장 ID 이중체계: master=`st_id`(ST-…) / POS·엔진=`st_uid`(I…), 매핑 `store_master_v2.pos_st_uid`
- 토큰: VPS `/root/.atomos/engine_token` ↔ Railway `ATOMIC_ENGINE_TOKEN`
