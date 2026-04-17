# /flow-review

이 명령은 `skills/flow-review.md`를 호출하는 얇은 진입점이다.

## 역할
- review 요청을 `flow-review` skill로 넘긴다.
- 실제 리뷰 기준과 출력 형식은 skill과 `scripts/execute.py`가 기준이다.

## 입력
- 리뷰 대상 요청
- 필요하면 관련 task/doc 경로

## 출력
- review 결과 또는 dry-run 요약

## 참고
- 본체: `skills/flow-review.md`
- 실행기: `scripts/execute.py`
