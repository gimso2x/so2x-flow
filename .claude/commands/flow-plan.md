# /flow-plan

이 명령은 `.claude/skills/flow-plan.md`를 호출하는 얇은 진입점이다.

## 역할
- plan 요청을 `flow-plan` skill로 넘긴다.
- 실제 계획 생성 규칙과 출력 형식은 skill과 `scripts/execute.py`가 기준이다.

## 입력
- 계획 요청 한 줄
- 필요하면 관련 범위나 제약

## 출력
- 계획 문서 또는 dry-run 요약

## 참고
- 본체: `.claude/skills/flow-plan.md`
- 실행기: `scripts/execute.py`
