# flow-qa

Use this skill when a QA issue or bug report needs a document-first fix flow.

## Input
- QA 이슈 한 줄
- 필요하면 QA ID, 재현 조건, 기대 동작

## Required docs
- `.workflow/docs/QA.md`
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 관련 task 문서

## Outputs
- `.workflow/tasks/qa/<slug>.md`
- `.workflow/outputs/runs/qa-<slug>-<timestamp>.json`
- `.workflow/outputs/runs/qa-<slug>-<timestamp>.md`

## Forbidden
- QA task 문서 없이 수정 시작 금지
- feature 작업으로 슬쩍 범위 확장 금지
- `runtime.allow_live_run` 없이 live 실행 금지

## Runtime policy
- 먼저 `.workflow/tasks/qa/<slug>.md`를 만든다
- reproduction / expected / actual / minimal fix를 명시한다
- qa_planner를 먼저 실행하고 implementer는 그 결과를 따른다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
