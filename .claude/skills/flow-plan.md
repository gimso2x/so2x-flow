# flow-plan

Use this skill to create a validated plan document without implementation.

## Input
- 계획 요청 한 줄
- 필요하면 범위, 제약, 우선순위

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 `DESIGN.md`

## Goal
- 바로 구현으로 달리지 말고, 먼저 설계 방향을 확정한다.
- 오픈 이슈를 뒤에 메모처럼 남기지 말고, 질문과 추천안으로 앞에서 소진한다.
- 최종 출력은 "생각 정리"가 아니라 "승인 가능한 설계 초안"이어야 한다.

## Required flow
1. 현재 프로젝트 컨텍스트 확인
2. 범위가 크면 먼저 분해
3. 질문은 한 번에 하나씩 정리
4. 접근안 2~3개 비교
5. 추천안 1개 명시
6. 설계 초안 제시
7. 승인 필요 여부 명시
8. 계획 산출물 저장
9. 마지막은 `/flow-feature ... 진행하시겠습니까? (y/n)`처럼 닫힌 질문으로 끝낸다

## Output contract
계획 응답과 산출물에는 최소한 아래 항목이 있어야 한다.
- `Context Snapshot`
- `Open Questions`
- `Options`
- `Recommendation`
- `Draft Plan`
- `Approval Gate`
- `Next Step Prompt`

## Outputs
- `.workflow/outputs/plans/<slug>.md`
- planner 결과 요약 또는 dry-run 출력

## Forbidden
- 코드 수정 금지
- implementer 실행 금지
- 질문 없이 바로 단일안으로 확정 금지
- 추천안 없이 오픈 이슈만 나열하고 끝내기 금지
- 승인 요청 없이 구현 단계로 밀어넣기 금지

## Runtime policy
- decomposition은 명시적으로 남긴다
- 결과 산출물은 `.workflow/outputs/plans/` 아래에 남긴다
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
