---
validate_prompt: |
  Confirm the output still keeps the init artifact as .workflow/tasks/init/<slug>.json,
  includes PRD/ARCHITECTURE/QA/DESIGN question coverage, auto-fills any values that are already clear from the repo/request,
  and only asks follow-up questions when information is still missing. Do not fabricate project docs beyond what the repo/request supports.
---

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
- repo/최근 요청만으로 확실한 값은 먼저 `answers`에 자동 반영
- 시작 시 선택 가능한 초기화 방식: `1. 자동채우기`, `2. 질문`
- 남은 질문이 있으면 `draft_auto_filled` 또는 `needs_user_input`, 다 채워지면 `ready_for_review`

## Question flow
- 첫 실행에서는 구현으로 넘어가지 않고 init 초안부터 정리한다.
- init은 planner/implementer를 호출하지 않고 질문지 산출물만 갱신한다.
- 질문은 문서 target과 함께 남긴다.
- 기본 질문 축은 프로젝트명, 목표, 사용자, 범위, 제외 범위, 구조 제약, 초기 QA, 디자인 기준이다.
- 시작할 때 초기화 방식을 고를 수 있다: `1. 자동채우기`(`auto-fill-now`), `2. 질문`(`ask-first`).
- 답을 받기 전에는 문서를 임의로 확정하지 않는다.
- 가능한 값은 먼저 자동으로 채운다.
- 질문은 항상 한 번에 하나씩만 한다.
- 첫 응답에서는 질문표 전체를 채팅에 다시 풀어쓰지 말고, 방금 저장한 init artifact 경로와 mode 선택지부터 짧게 알린다.
- 사용자가 답하면 init artifact의 `answers`에 반영한 뒤 다음 질문으로 넘어간다.
- 여러 답을 한 번에 주면 받은 범위만 반영하고, 남은 질문도 한 번에 하나씩 이어간다.

## Forbidden
- feature 구현 시작 금지
- branch/commit 자동화 금지
- live 실행 강제 금지
- 질문 없이 PRD/ARCHITECTURE/DESIGN 내용을 지어내기 금지

## Runtime policy
- 기본은 `--dry-run`으로 빠르게 확인하고, live 실행은 `runtime.allow_live_run=true`일 때 실제 runner로 검증한다
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
- 문자열 `"true"` 같은 값은 허용하지 않는다. `ccs-map.yaml`에는 YAML boolean `true`/`false`만 넣는다.
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
