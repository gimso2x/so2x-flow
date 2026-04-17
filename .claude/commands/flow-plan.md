# /flow-plan

이 명령은 `.claude/skills/flow-plan.md`를 호출하는 얇은 진입점이다.

## 역할
- plan 요청을 `flow-plan` skill로 넘긴다.
- 실제 계획 생성 규칙과 출력 형식은 skill과 `.workflow/scripts/execute.py`가 기준이다.

## 입력
- 계획 요청 한 줄
- 필요하면 관련 범위나 제약

## 출력
- 계획 문서 또는 dry-run 요약
- 응답에는 가능하면 아래가 보여야 한다.
  - 추천안 1개
  - 남아 있는 확인 질문
  - 승인 필요 여부
  - 마지막 한 줄의 다음 단계 질문

## 응답 마감 규칙
- `원하면 다음으로...` 같은 흐린 문장으로 끝내지 않는다.
- 마지막은 즉답 가능한 닫힌 질문으로 끝낸다.
- 권장 형식:
  - `다음으로 /flow-feature <요청 요약> 구현 계획까지 이어가시겠습니까? (y/n)`

## 참고
- 본체: `.claude/skills/flow-plan.md`
- 실행기: `.workflow/scripts/execute.py`
