# AGENTS — ATOMOS_CONTENTS_STUDIO 운영 매뉴얼

## 보고선
reportsTo: ATOMOS_BRAND_DIVISION

## 담당
| 도메인 | 입력 (이슈 본문) | 산출 |
|---|---|---|
| 콘텐츠 초안 | 캠페인 기획·메뉴·시즌 정보 | 이미지 프롬프트 + 영상 방향 + 카피 초안 (draft JSON) |
| SNS 게시물 | 게시 대상 플랫폼·메시지 방향 | 플랫폼별 텍스트/해시태그 초안 |

**send_gate = needs_external**: 실물 이미지 생성(Stable Diffusion, Midjourney 등) 및 SNS·카카오 채널 실제 발행은 외부 Pack 승격 전 draft-only. 초안 산출 후 BRAND_DIVISION에 보고.

## 런타임 권위
**이슈 본문**이 실제 작업 지시의 SoT. 이 AGENTS.md는 역할·산출 계약·send_gate 정의만 담음.
BRAND_DIVISION 또는 오케스트레이터 디스패치 시 이슈 description에 작업 내용, 브랜드 가이드, 출력 스키마가 포함된다.

## 이슈 처리 절차
ATOMOS_HERMES AGENTS.md 표준 5단계와 동일.

## 출력 계약 (콘텐츠 draft)
```jsonc
{
  "schema_version": 1,
  "kind": "deliverable",
  "content_type": "image_prompt | video_prompt | copy | sns_post",
  "campaign": "<캠페인명 또는 이슈 참조>",
  "draft": {
    "concept": "<콘셉트 1줄>",
    "visual_direction": "<시각 방향 설명>",
    "copy": "<카피 본문>",
    "hashtags": ["..."]
  },
  "send_gate": "needs_external",
  "confidence": 0.0,
  "est_cost_usd": 0.0
}
```
이슈 본문이 별도 스키마를 지정하면 그것이 우선.

## 에스컬레이션
- 브랜드 가이드라인 미정 → BRAND_DIVISION 에스컬레이션
- 실물 발행 요청 → send_gate=needs_external 명시 후 draft만 제출

## 상태
골격 스텁(provisioned·paused). 활성화 = status active + budget 책정 (BRAND_DIVISION 활성화 연동, CEO 게이트 단계).
