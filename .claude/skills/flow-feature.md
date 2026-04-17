# flow-feature

Use this skill when an approved product or engineering slice is ready to execute.

## Input
- feature 요청 한 줄
- 필요하면 범위, 관련 문서, 제약
- 가능하면 직전 `flow-plan` 승인 산출물 또는 승인된 설계 메모

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 `DESIGN.md`
- 승인된 `flow-plan` 산출물 또는 승인된 설계 메모
- `--skip-plan`은 `approved: true` 또는 `status: approved`가 들어간 plan JSON이 있을 때만 허용한다

## Goal
- `flow-feature`는 설계/옵션 비교 단계가 아니라, 승인된 방향에서 이번에 구현할 최소 slice를 실행하는 단계다.
- planner와 implementer는 새 방향을 발명하는 역할이 아니라, 승인된 방향을 안전하게 실행하는 역할이다.
- brainstorming이나 writing-plans 성격의 작업은 여기서 하지 않고 `flow-plan`에서 끝낸다.
- 구현은 가능하면 `test-driven-development`를 따르고, slice 완료 뒤에는 independent review gate를 통과해야 한다.
- slice가 충분히 독립적이면 `subagent-driven-development`처럼 task 단위로 실행/검토를 분리할 수 있다.

## Required flow
1. 입력 feature 요청을 task 문서로 정리한다
2. 관련 plan/설계 승인 맥락이 있는지 확인한다
3. 승인된 방향이 없으면 구현으로 밀지 말고 여기서 멈춘다
4. 승인된 방향이 있을 때만 이번 실행 범위를 최소 구현 slice로 축소한다
5. `Proposed Steps`를 planner가 구체화한다
6. implementer는 planner 결과만 따라 최소 범위로 실행한다
7. 새 동작/버그 수정은 가능하면 failing test를 먼저 만들고 구현한다
8. slice 구현 후 spec/quality review gate를 통과시킨다
9. 검증 결과와 남은 범위를 분리해서 적는다
10. 마지막은 자동 다음 단계 제안이 아니라, 현재 slice 진행 여부 또는 plan 선행 여부를 묻는 닫힌 질문으로 끝낸다

## Output contract
feature task와 응답에는 최소한 아래 항목이 있어야 한다.
- `Approved Direction`
- `Implementation Slice`
- `Out of Scope`
- `Proposed Steps`
- `Verification`
- `Review Gate`
- `Follow-up Slice`
- `Next Step Prompt`

## Forbidden
- task 문서 없이 구현 시작 금지
- 설계 맥락 없이 planner/implementer가 범위를 새로 발명하는 것 금지
- 승인된 방향이 없는데도 바로 구현으로 밀어붙이는 것 금지
- 승인된 방향이 없으면 바로 구현으로 밀지 않는다
- brainstorming / writeplan / option comparison을 여기서 다시 수행하는 것 금지
- failing test 없이 바로 코드부터 쓰는 것 금지(예외는 명시적으로 제한)
- review gate 없이 끝났다고 처리하는 것 금지
- implementer가 planner 없이 범위를 재정의하는 것 금지
- `runtime.allow_live_run` 없이 live 실행 금지

## Runtime policy
- `.workflow/tasks/feature/<slug>.json`을 먼저 만든다
- task에는 승인된 방향과 이번 slice를 명시한다
- 승인된 plan이 없으면 여기서 멈추고 `flow-plan` 선행 여부를 먼저 묻는다
- `--skip-plan`은 matching plan JSON에 `approved: true` 또는 `status: approved`가 있을 때만 허용한다
- `Proposed Steps`를 planner가 채운 뒤 implementer를 실행한다
- canonical plan 후보는 `.workflow/tasks/plan/*.json`만 본다
- 최신 plan이 있어도 요청과 안 맞으면 연결하지 않는다
- implementer는 planner 결과와 승인된 plan 문맥이 있을 때만 그 최소 범위로 실행한다
- slice 완료 후에는 최소한 spec compliance와 code quality/review 관점을 다시 확인한다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
