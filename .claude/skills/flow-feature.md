---
validate_prompt: |
  Confirm the output still includes Approved Direction, Implementation Slice, Out of Scope,
  Proposed Steps, Verification, Review Gate, Follow-up Slice, and Next Step Prompt.
  If no approved plan exists, the response must clearly stop and ask whether to run flow-plan first.
  End with a closed approval question rather than an open-ended suggestion.
---

# flow-feature

Use this skill when an approved product or engineering slice is ready to execute.

## Position in real workflow
- `flow-feature`는 구현 단계 본체다.
- 실사용 기본 루프는 보통 `flow-plan` → `flow-feature` → `/simplify` 반복 → convergence `0` → squash 순서다.
- `/simplify`는 별도 `flow-*` workflow가 아니라 `flow-feature` 뒤에 붙는 기본 마감 루프다.
- `flow-review`, `flow-qa`는 필요할 때 추가하고, GitHub PR 운영은 선택 사항이다.

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
8. 구현/테스트가 끝나면 `/simplify` 반복 대상으로 넘길 수 있게 변경 범위와 검증 결과를 정리한다
9. 실사용 기본 마감 루프는 `/simplify` 반복 → convergence `0` → squash다
10. `flow-review`, `flow-qa`, GitHub PR 운영은 필요할 때만 뒤에 붙인다
11. 마지막은 자동 다음 단계 제안이 아니라, 현재 slice 진행 여부 또는 plan 선행 여부를 묻는 닫힌 질문으로 끝낸다

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
- 구현/테스트가 끝난 뒤 기본 마감 루프는 `/simplify` 반복 → convergence `0` → squash다
- `/simplify`는 가능하면 현재 diff / 현재 slice 범위로만 돌린다
- 매회 `/simplify`는 최대 2~3개 개선만 처리하고, convergence 요약은 짧게 남긴다
- convergence가 `0`이면 바로 종료하고 squash한다
- convergence가 작더라도 반복은 보통 2~3회를 넘기지 않는다
- `flow-review`, `flow-qa`는 필요할 때만 추가하고, GitHub PR 운영은 선택 사항이다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
