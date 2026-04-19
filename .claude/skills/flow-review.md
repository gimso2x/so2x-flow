---
validate_prompt: |
  Confirm the output still includes Spec Gap, Architecture Concern, Test Gap,
  QA Watchpoints, Security / Regression Risk, and Verdict.
  Keep the review fail-closed and do not turn it into an implementation patch.
---

# flow-review

Use this skill to review planned or implemented work against project documents.

## Input
- 리뷰 대상 요청
- 필요하면 관련 task/doc 경로

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- `.workflow/docs/QA.md`
- 필요 시 관련 task 문서

## Goal
- `flow-review`는 칭찬문이 아니라 independent verification 단계다.
- `requesting-code-review` 철학을 따라, 구현자 관점이 아니라 독립 reviewer 관점에서 gap과 regression risk를 찾는다.
- 가능하면 spec compliance와 code quality/security를 분리해 본다.

## Outputs
- `.workflow/tasks/review/<slug>.json`
- `Spec Gap`
- `Architecture Concern`
- `Test Gap`
- `QA Watchpoints`
- `Security / Regression Risk`
- `Verdict`

## Forbidden
- 코드 변경 금지
- 구현 계획 재작성 금지
- 근거 없는 장문 감상문 금지
- 구현자 의도를 추측해서 문제를 덮어주기 금지

## Runtime policy
- actionable finding 위주로 쓴다
- spec gap / quality risk / regression risk를 구분해서 쓴다
- reviewer는 구현을 스스로 정당화하지 말고 fail-closed에 가깝게 본다
- 기본은 `--dry-run`으로 빠르게 확인하고, live 실행은 `runtime.allow_live_run=true`일 때 실제 runner로 검증한다
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
