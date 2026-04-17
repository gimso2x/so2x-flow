# flow-init

Use this skill to bootstrap a new so2x-flow workspace.

## Input
- 프로젝트 초기화 요청
- 필요하면 bootstrap 목적이나 운영 메모

## Required docs
- `CLAUDE.md`
- `.workflow/config/ccs-map.yaml`
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- `.workflow/docs/QA.md`
- `DESIGN.md`

## Outputs
- `.workflow/tasks/init/<slug>.json` canonical init artifact
- PRD/ARCHITECTURE/QA/DESIGN 기준 질문 세트
- 사용자 답변 전까지 `needs_user_input` 상태 유지
- 답변(`answers`)이 없으면 재실행 시 `needs_user_input`로 되돌린다

## Question flow
- 첫 실행에서는 구현으로 넘어가지 않고 질문부터 정리한다.
- init은 planner/implementer를 호출하지 않고 질문지 산출물만 갱신한다.
- 질문은 문서 target과 함께 남긴다.
- 기본 질문 축은 프로젝트명, 목표, 사용자, 범위, 제외 범위, 구조 제약, 초기 QA, 디자인 기준이다.
- 답을 받기 전에는 문서를 임의로 확정하지 않는다.

## Forbidden
- feature 구현 시작 금지
- branch/commit 자동화 금지
- live 실행 강제 금지
- 질문 없이 PRD/ARCHITECTURE/DESIGN 내용을 지어내기 금지

## Runtime policy
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- 문자열 `"true"` 같은 값은 허용하지 않는다. `ccs-map.yaml`에는 YAML boolean `true`/`false`만 넣는다.
