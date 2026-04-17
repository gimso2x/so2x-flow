# /flow-review

이 명령은 `.claude/skills/flow-review.md`를 호출하는 얇은 진입점이다.

## 역할
- review 요청을 `flow-review` skill로 넘긴다.
- 실제 리뷰 기준과 출력 형식은 skill과 `.workflow/scripts/execute.py`가 기준이다.
- `flow-review`는 requesting-code-review 성격의 independent verification 단계다.

## 입력
- 리뷰 대상 요청
- 필요하면 관련 task/doc 경로

## 출력
- `.workflow/tasks/review/<slug>.json`
- review 결과 또는 dry-run 요약
- 가능하면 Spec Gap / Test Gap / Security or Regression Risk / Verdict가 함께 보여야 한다

## 응답 마감 규칙
- 막연한 칭찬보다 blocking issue를 먼저 적는다.
- spec mismatch와 quality risk를 섞지 말고 구분한다.
- 구현자가 의도했을 것 같다는 이유로 문제를 덮지 않는다.

## 참고
- 본체: `.claude/skills/flow-review.md`
- 실행기: `.workflow/scripts/execute.py`
