# flow-feature

Use this skill when a new product or engineering feature is requested.

## Input
- feature 요청 한 줄
- 필요하면 범위, 관련 문서, 제약

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 `DESIGN.md`

## Outputs
- `.workflow/tasks/feature/<slug>.md`
- `.workflow/outputs/runs/feature-<slug>-<timestamp>.json`
- `.workflow/outputs/runs/feature-<slug>-<timestamp>.md`

## Forbidden
- task 문서 없이 구현 시작 금지
- implementer가 planner 없이 범위를 재정의하는 것 금지
- `runtime.allow_live_run` 없이 live 실행 금지

## Runtime policy
- 먼저 `.workflow/tasks/feature/<slug>.md`를 만든다
- `Proposed Steps`를 채운 뒤 planner를 먼저 실행한다
- implementer는 planner 결과를 받아 최소 범위로 실행한다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
