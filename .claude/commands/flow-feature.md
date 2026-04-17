# /flow-feature

이 명령은 `.claude/skills/flow-feature.md`를 호출하는 얇은 진입점이다.

## 역할
- feature 요청을 `flow-feature` skill로 넘긴다.
- 실제 절차, 규칙, task 문서 기준은 skill과 `scripts/execute.py`가 기준이다.

## 입력
- feature 요청 한 줄
- 필요하면 관련 문서나 범위 힌트

## 출력
- `tasks/feature/<slug>.md`
- planner -> implementer 흐름 결과 또는 dry-run 요약

## 참고
- 본체: `.claude/skills/flow-feature.md`
- 실행기: `scripts/execute.py`
