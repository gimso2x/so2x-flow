# /flow-plan

이 명령은 `.claude/skills/flow-plan.md`를 호출하는 얇은 진입점이다.

## 역할
- 요구사항을 `flow-plan` skill로 넘긴다.
- 실제 계획 생성 규칙과 출력 형식은 skill과 `.workflow/scripts/execute.py`가 기준이다.
- 현재 v0 `/flow-plan`은 `.workflow/tasks/plan/<slug>.json` 생성이 기본 전제다.
- plan은 중복 산출물을 만들지 않고 `.workflow/tasks/plan/<slug>.json` 하나만 남긴다.
- `flow-plan` 안에서 brainstorming + writing-plans 성격을 함께 처리한다.

## 입력
- 요구사항/아이디어/문제 한 줄
- 필요하면 관련 범위나 제약

## 출력
- 계획 문서 또는 dry-run 요약
- 응답에는 가능하면 아래가 보여야 한다.
  - 옵션 2~3개 비교
  - 추천안 1개
  - 구현 slice 초안
  - 검증 기준
  - 승인 필요 여부
  - 마지막 한 줄의 설계 확정 질문

## 응답 마감 규칙
- `원하면 다음으로...` 같은 흐린 문장으로 끝내지 않는다.
- 승인 전에는 `/flow-feature`로 자동 전환하자는 식으로 몰아가지 않는다.
- 마지막은 즉답 가능한 닫힌 질문으로 끝낸다.
- 권장 형식:
  - `이 설계/구현 계획 방향으로 확정할까요? (y/n)`

## 주의
- `/flow-plan` dry-run도 canonical 계획 산출물 `.workflow/tasks/plan/<slug>.json`을 만든다.
- dry-run 뒤에 에이전트가 그 json 산출물을 다시 수동 수정하려고 들 필요는 없다. 기본 산출물을 우선 신뢰한다.
- markdown 계획 문서 없이 json만 남기는 것이 현재 v0 기본이다.

## 참고
- 본체: `.claude/skills/flow-plan.md`
- 실행기: `.workflow/scripts/execute.py`
