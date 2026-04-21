---
validate_prompt: |
  Confirm the output still includes Reproduction, Expected, Actual, Root Cause Hypothesis,
  Minimal Fix, Verification, and Residual Risk.
  The flow must stay root-cause-first and should not skip the QA task artifact.
---

# flow-qa

`flow-fix`는 이 bugfix workflow의 사용자-facing alias다. 기존 `flow-qa`, `qa-fix`도 계속 허용한다.

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

## Goal
- `flow-qa`는 임시 땜질이 아니라 재현 가능한 bugfix flow다.
- `systematic-debugging` 원칙을 따라 root cause를 먼저 찾고, 그 다음 최소 수정으로 해결한다.
- 가능하면 `test-driven-development`를 따라 failing reproduction/test를 먼저 만들고 fix 후 회귀 검증까지 끝낸다.

## Required flow
1. QA 이슈를 `.workflow/tasks/qa/<slug>.json`에 먼저 기록한다
2. error / reproduction / expected / actual을 명확히 적는다
3. 문제를 일관되게 재현하고 root cause 가설을 세운다
4. fix 전에 가능한 최소 failing reproduction 또는 failing test를 만든다
5. qa_planner가 minimal fix 범위를 정리한다
6. implementer는 root cause만 겨냥한 최소 수정만 한다
7. reviewer가 Code Reuse Review, Code Quality Review, Efficiency Review를 포함해 회귀 위험을 점검한다
8. 수정 후 failing test/reproduction과 전체 관련 검증을 다시 돌린다
9. 검증 결과와 남은 리스크를 분리해서 적는다

## Outputs
- `.workflow/tasks/qa/<slug>.json`
- `Reproduction`
- `Expected`
- `Actual`
- `Root Cause Hypothesis`
- `Minimal Fix`
- `Verification`
- `Residual Risk`

## Output contract
- `.workflow/tasks/qa/<slug>.json`
- `Reproduction`
- `Expected`
- `Actual`
- `Root Cause Hypothesis`
- `Minimal Fix`
- `Verification`
- `Residual Risk`

## Forbidden
- QA task 문서 없이 수정 시작 금지
- root cause 확인 전 추측성 patch 금지
- failing reproduction/test 없이 바로 수정하는 것 금지
- feature 작업으로 슬쩍 범위 확장 금지
- `runtime.allow_live_run` 없이 live 실행 금지

## Runtime policy
- `.workflow/tasks/qa/<slug>.json`을 먼저 만든다
- reproduction / expected / actual / root cause hypothesis / minimal fix를 명시한다
- qa_planner를 먼저 실행하고 implementer는 그 결과를 따른다
- implementer 뒤에는 reviewer가 회귀/품질/재사용 관점 gate를 남긴다
- 새 동작 또는 버그 수정은 가능하면 test-first로 진행한다
- fix 후에는 재현 케이스와 관련 테스트를 다시 돌린다
- 기본은 `--dry-run`으로 빠르게 확인하고, live 실행은 `runtime.allow_live_run=true`일 때 실제 runner로 검증한다
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
