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
- 가능하면 직전 `flow-plan` 산출물 또는 승인된 설계 메모

## Goal
- `flow-feature`는 설계가 덜 된 요청을 통째로 삼키는 명령이 아니다.
- 이미 합의된 방향에서 이번에 구현할 첫 slice를 작게 잘라 실행하는 단계다.
- planner와 implementer는 새 방향을 발명하는 역할이 아니라, 승인된 방향을 안전하게 실행하는 역할이다.

## Required flow
1. 입력 feature 요청을 task 문서로 정리한다
2. 관련 plan/설계 승인 맥락이 있는지 확인한다
3. 이번 실행 범위를 최소 구현 slice로 축소한다
4. `Proposed Steps`를 planner가 구체화한다
5. implementer는 planner 결과만 따라 최소 범위로 실행한다
6. 검증 결과와 남은 범위를 분리해서 적는다
7. 마지막은 다음 slice 진행 여부를 묻는 닫힌 질문으로 끝낸다

## Output contract
feature task와 응답에는 최소한 아래 항목이 있어야 한다.
- `Approved Direction`
- `Implementation Slice`
- `Out of Scope`
- `Proposed Steps`
- `Verification`
- `Follow-up Slice`
- `Next Step Prompt`

## Forbidden
- task 문서 없이 구현 시작 금지
- 설계 맥락 없이 planner/implementer가 범위를 새로 발명하는 것 금지
- implementer가 planner 없이 범위를 재정의하는 것 금지
- `runtime.allow_live_run` 없이 live 실행 금지

## Runtime policy
- 먼저 `.workflow/tasks/feature/<slug>.md`를 만든다
- task에는 승인된 방향과 이번 slice를 명시한다
- `Proposed Steps`를 planner가 채운 뒤 implementer를 실행한다
- 최신 `.workflow/outputs/plans/*.md` 중 canonical plan 문서를 찾고, 요청 슬러그/주제 토큰이 맞을 때만 feature에 연결한다
- 최신 plan이 있어도 요청과 안 맞으면 연결하지 않는다
- implementer는 planner 결과와 승인된 plan 문맥이 있을 때만 그 최소 범위로 실행한다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
