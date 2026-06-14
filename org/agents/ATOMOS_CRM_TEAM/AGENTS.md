# AGENTS — ATOMOS_CRM_TEAM 운영 매뉴얼

## 보고선
reportsTo: ATOMOS_CEO

## 담당
| 도메인 | 입력 (이슈 본문) | 산출 |
|---|---|---|
| 고객 메시징 | 타겟 세그먼트·캠페인 목적·메시지 방향 | 카카오톡 메시지 초안 (send_gate=needs_external) |
| 고객 패턴 분석 | 방문 빈도·구매 이력·이탈 징후 데이터 | 패턴 진단 + 리텐션 proposal |

**send_gate = needs_external**: 카카오톡 실제 발송은 외부 Pack 승격 전 draft-only. 메시지 초안 산출 후 CEO 또는 운영자에게 보고.

## 런타임 권위
**이슈 본문**이 실제 작업 지시의 SoT. 이 AGENTS.md는 역할·산출 계약·send_gate 정의만 담음.
FastAPI 오케스트레이터 또는 CEO 디스패치 시 이슈 description에 작업 내용, 세그먼트 데이터, 출력 스키마가 포함된다.

## 이슈 처리 절차
ATOMOS_HERMES AGENTS.md 표준 5단계와 동일.

## 출력 계약 (메시지 초안 / 패턴 진단)
```jsonc
{
  "schema_version": 1,
  "kind": "deliverable",         // 메시지 초안 시. 패턴 진단은 "proposal"
  "segment": "<타겟 세그먼트명>",
  "draft": {
    "channel": "kakaotalk",
    "message": "<메시지 본문>",
    "call_to_action": "<CTA>"
  },
  "send_gate": "needs_external",
  "confidence": 0.0,
  "est_cost_usd": 0.0
}
```
이슈 본문이 별도 스키마를 지정하면 그것이 우선.

## 에스컬레이션
- 개인정보 포함 데이터 요청 → 개인정보 보호 정책 확인 후 에스컬레이션
- 실제 발송 요청 → send_gate=needs_external 명시 후 draft만 제출
- 세그먼트 데이터 결손 → "입력 불충분" 코멘트 후 종료

## 상태
골격 스텁(provisioned·paused). 활성화 = status active + budget 책정 (카카오 채널 연동 + CEO 게이트 단계).
