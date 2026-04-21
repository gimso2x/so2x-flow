---
validate_prompt: |
  Confirm the output still includes Mechanical Status, Semantic Status,
  Release Readiness, Regression Risks, and Recommended Next Step.
  The flow must stay evaluation-only and should not silently turn into implementation.
---

# flow-evaluate

Use this skill when a completed or in-progress slice needs an independent readiness check.

## Input
- 평가할 변경/슬라이스 한 줄
- 필요하면 관련 task artifact 경로

## Required docs
- `.workflow/docs/QA.md`
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 관련 task 문서

## Goal
- `flow-evaluate`는 구현이 아니라 readiness gate다.
- 먼저 mechanical 상태를 보고, 그 다음 semantic 정합성을 본다.
- 결과는 release 여부와 다음 액션으로 짧게 닫는다.

## Output contract
- `Mechanical Status`
- `Semantic Status`
- `Release Readiness`
- `Regression Risks`
- `Recommended Next Step`
- `.workflow/tasks/evaluate/<slug>.json`

## Forbidden
- evaluate 결과를 핑계로 바로 구현 시작 금지
- task artifact 없이 막연한 평가 금지
- mechanical/semantic 구분 없이 뭉뚱그린 평가 금지

## Runtime policy
- `.workflow/tasks/evaluate/<slug>.json`을 먼저 만든다
- reviewer가 단독으로 readiness gate를 남긴다
- related task가 있으면 docs bundle에 포함한다
- 기본은 `--dry-run`으로 빠르게 확인한다
- 후속 액션은 `/flow-review`, `/flow-fix`, `/simplify` 중 하나로 닫는다
