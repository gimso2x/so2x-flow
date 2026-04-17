# flow-plan

Use this skill to turn a rough requirement into an approved implementation plan without implementation.

## Input
- 요구사항/문제/아이디어 한 줄
- 필요하면 범위, 제약, 우선순위, 관련 문서

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 `DESIGN.md`

## Goal
- `flow-plan`은 단순 메모가 아니라, brainstorming + implementation planning + approval gate를 한 번에 처리하는 단계다.
- 방향이 흐린 요구사항을 선택지 비교와 추천안으로 좁히고, 바로 실행 가능한 slice 계획으로 고정한다.
- 최종 출력은 "생각 정리"가 아니라 "승인 가능한 설계 + 구현 계획"이어야 한다.

## Built-in capability
- superpowers `brainstorming` 역할을 내부적으로 흡수한다: 옵션 2~3개 비교, trade-off 정리, 추천안 1개 선택
- `writing-plans` 역할을 내부적으로 흡수한다: 구현 slice 분해, 검증 기준 정리, 다음 실행 단위 명시
- 별도 planning skill로 튕기지 말고 `flow-plan` 안에서 끝낸다

## Required flow
1. 현재 프로젝트 컨텍스트와 관련 문서를 확인한다
2. 요구사항이 크거나 모호하면 먼저 문제를 분해한다
3. 질문은 한 번에 하나씩 정리한다
4. 접근안 2~3개를 비교하고 trade-off를 적는다
5. 추천안 1개를 명시한다
6. 추천안을 기준으로 구현 가능한 최소 slice들로 계획을 쪼갠다
7. 각 slice마다 목표, 범위, 검증 기준을 적는다
8. 설계 초안 + 구현 계획을 canonical plan artifact로 저장한다
9. 마지막은 `/flow-feature`로 자동 전환하자는 문장이 아니라, 이 설계/계획 방향 자체를 확정할지 묻는 닫힌 질문으로 끝낸다

## Output contract
계획 응답과 산출물에는 최소한 아래 항목이 있어야 한다.
- `Context Snapshot`
- `Open Questions`
- `Options`
- `Recommendation`
- `Implementation Slices`
- `Verification Gates`
- `Draft Plan`
- `Approval Gate`
- `Next Step Prompt`

## Outputs
- `.workflow/tasks/plan/<slug>.json`
- planner 결과 요약 또는 dry-run 출력

## Forbidden
- 코드 수정 금지
- implementer 실행 금지
- 질문 없이 바로 단일안으로 확정 금지
- 추천안 없이 오픈 이슈만 나열하고 끝내기 금지
- slice/검증 기준 없이 추상적 계획만 남기고 끝내기 금지
- 승인 요청 없이 구현 단계로 밀어넣기 금지
- 승인 전에는 `/flow-feature`로 자동 전환하거나 다음 실행을 기정사실화하지 않는다

## Runtime policy
- decomposition은 명시적으로 남긴다
- canonical 계획 산출물은 `.workflow/tasks/plan/` 아래 JSON으로 남긴다
- plan은 중복 출력 경로를 만들지 않고 `.workflow/tasks/plan/` JSON 하나만 남긴다
- `flow-feature`는 `.workflow/tasks/plan/*.json` 중 승인된 artifact만 canonical plan으로 참조한다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- 현재 v0 `/flow-plan`은 markdown 계획 문서를 만들지 않는다.
