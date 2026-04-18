# flow commands

이 디렉토리의 command 문서는 so2x-flow skill을 호출하는 얇은 wrapper다.
skill만 있어도 workflow 정의는 성립하고, command는 `/flow-*` 슬래시 UX가 필요할 때만 붙이면 된다.

명령 목록
- `flow-init`
- `flow-feature`
- `flow-qa`
- `flow-review`
- `flow-plan`

원칙
- command는 진입점만 담당한다.
- 실제 절차와 규칙은 `.claude/skills/*.md`가 기준이다.
- 실제 실행은 `.workflow/scripts/execute.py`가 담당한다.
- command 문서에 workflow 로직을 중복해서 넣지 않는다.
