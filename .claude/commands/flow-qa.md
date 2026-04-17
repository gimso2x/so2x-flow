# /flow-qa

이 명령은 `skills/flow-qa.md`를 호출하는 얇은 진입점이다.

## 역할
- QA 이슈 요청을 `flow-qa` skill로 넘긴다.
- 실제 절차, 규칙, QA task 문서 기준은 skill과 `scripts/execute.py`가 기준이다.

## 입력
- QA 이슈 설명
- 필요하면 QA ID, 재현 조건, 기대 동작

## 출력
- `tasks/qa/<slug>.md`
- qa-planner -> implementer 흐름 결과 또는 dry-run 요약

## 참고
- 본체: `skills/flow-qa.md`
- 실행기: `scripts/execute.py`
