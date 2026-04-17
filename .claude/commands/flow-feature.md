# /flow-feature

이 명령은 `.claude/skills/flow-feature.md`를 호출하는 얇은 진입점이다.

## 역할
- feature 요청을 `flow-feature` skill로 넘긴다.
- 실제 절차, 규칙, task 문서 기준은 skill과 `.workflow/scripts/execute.py`가 기준이다.

## 입력
- feature 요청 한 줄
- 필요하면 관련 문서나 범위 힌트
- 가능하면 직전 flow-plan 승인 방향

## 출력
- `.workflow/tasks/feature/<slug>.md`
- planner -> implementer 흐름 결과 또는 dry-run 요약
- 매칭된 최신 plan이 있으면 그 경로와 매칭 사유, 없으면 미연결 사유
- 응답에는 가능하면 아래가 보여야 한다.
  - 승인된 방향
  - 이번 구현 slice
  - 이번에 안 하는 범위
  - 검증 기준
  - 마지막 한 줄의 다음 slice 질문

## 응답 마감 규칙
- 설계 미확정 상태를 숨기고 바로 구현 확정한 척하지 않는다.
- 마지막은 즉답 가능한 닫힌 질문으로 끝낸다.
- 권장 형식:
  - `다음으로 <남은 slice 요약>까지 이어서 진행하시겠습니까? (y/n)`

## 참고
- 본체: `.claude/skills/flow-feature.md`
- 실행기: `.workflow/scripts/execute.py`
