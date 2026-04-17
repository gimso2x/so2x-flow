# flow-plan

Use this skill to create a plan or task document without implementation.

## Input
- 계획 요청 한 줄
- 필요하면 범위, 제약, 우선순위

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 `DESIGN.md`

## Outputs
- `.workflow/outputs/plans/<slug>.md`
- planner 결과 요약 또는 dry-run 출력

## Forbidden
- 코드 수정 금지
- implementer 실행 금지
- 계획 없는 범위 확장 금지

## Runtime policy
- decomposition은 명시적으로 남긴다
- 결과 산출물은 `.workflow/outputs/plans/` 아래에 남긴다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
