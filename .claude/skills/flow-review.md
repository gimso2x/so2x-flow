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

## Outputs
- `.workflow/tasks/review/<slug>.json`
- Spec Gap
- Architecture Concern
- Test Gap
- QA Watchpoints

## Forbidden
- 코드 변경 금지
- 구현 계획 재작성 금지
- 근거 없는 장문 감상문 금지

## Runtime policy
- actionable finding 위주로 쓴다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
