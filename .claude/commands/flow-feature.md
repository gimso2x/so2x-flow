# /flow-feature

이 명령은 `.claude/skills/flow-feature.md`를 호출하는 얇은 진입점이다.

## 역할
- 승인된 feature slice 요청을 `flow-feature` skill로 넘긴다.
- 실제 절차, 규칙, task 문서 기준은 skill과 `.workflow/scripts/execute.py`가 기준이다.
- `flow-feature`는 thinking/planning 단계가 아니라 승인된 plan 실행 단계다.

## 입력
- feature 요청 한 줄
- 필요하면 관련 문서나 범위 힌트
- 가능하면 직전 flow-plan 승인 방향

## 출력
- `.workflow/tasks/feature/<slug>.json`
- planner -> implementer 흐름 결과 또는 dry-run 요약
- 매칭된 최신 승인 plan이 있으면 그 경로와 매칭 사유, 없으면 미연결 사유
- 승인된 plan이 없으면 여기서 멈추고 `flow-plan`으로 먼저 범위를 확정할지 묻는다
- 응답에는 가능하면 아래가 보여야 한다.
  - 승인된 방향
  - 이번 구현 slice
  - 이번에 안 하는 범위
  - 검증 기준
  - 마지막 한 줄의 승인 게이트 질문

## 응답 마감 규칙
- 설계 미확정 상태를 숨기고 바로 구현 확정한 척하지 않는다.
- 승인된 방향이 없으면 `flow-plan` 선행 여부를 먼저 묻고, 이미 plan이 있으면 이번 slice 진행 여부를 묻는다.
- 마지막은 즉답 가능한 닫힌 질문으로 끝낸다.
- 권장 형식:
  - 승인된 방향 없음: `이 요청은 아직 승인된 방향이 없으니, flow-plan으로 먼저 범위를 확정할까요? (y/n)`
  - 승인된 방향 있음: `승인된 방향이 있으니, 이번 slice를 진행할까요? (y/n)`

## 참고
- 본체: `.claude/skills/flow-feature.md`
- 실행기: `.workflow/scripts/execute.py`
