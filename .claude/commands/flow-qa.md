# /flow-qa

이 명령은 `.claude/skills/flow-qa.md`를 호출하는 얇은 진입점이다.

## 역할
- QA 이슈 요청을 `flow-qa` skill로 넘긴다.
- 실제 절차, 규칙, QA task 문서 기준은 skill과 `.workflow/scripts/execute.py`가 기준이다.
- `flow-qa`는 systematic debugging + TDD 성격을 가진 bugfix 흐름이다.

## 입력
- QA 이슈 설명
- 필요하면 QA ID, 재현 조건, 기대 동작

## 출력
- `.workflow/tasks/qa/<slug>.json`
- qa-planner -> implementer 흐름 결과 또는 dry-run 요약
- 가능하면 root cause hypothesis / minimal fix / verification이 함께 보여야 한다

## 응답 마감 규칙
- 재현 없이 바로 고쳤다고 하지 않는다.
- root cause를 모르면 모른다고 적고 재현/조사 결과를 먼저 남긴다.
- 가능하면 failing reproduction 또는 failing test를 먼저 잡고 진행한다.

## 참고
- 본체: `.claude/skills/flow-qa.md`
- 실행기: `.workflow/scripts/execute.py`
