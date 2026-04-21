---
validate_prompt: |
  Confirm the output still includes Reproduction, Expected, Actual, Root Cause Hypothesis,
  Minimal Fix, Verification, and Residual Risk.
  The flow must stay root-cause-first, keep the QA task artifact first, and pass through reviewer.
---

# flow-fix

`flow-fix`는 `flow-qa`와 같은 bugfix workflow의 사용자-facing 별칭이다.
핵심은 재현 → 최소 수정 → 회귀 검증 → reviewer gate 순서다.

## Input
- 버그/이슈 한 줄
- 필요하면 QA ID, 재현 조건, 기대 동작

## Required docs
- `.workflow/docs/QA.md`
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- 필요 시 관련 task 문서

## Required flow
1. `.workflow/tasks/qa/<slug>.json`에 먼저 기록한다
2. qa_planner가 재현/기대/실제/최소 수정 범위를 정리한다
3. implementer가 root cause만 겨냥한 최소 수정과 검증을 수행한다
4. reviewer가 Code Reuse Review, Code Quality Review, Efficiency Review를 포함해 회귀 위험을 점검한다

## Alias
- 실행 엔트리포인트 `flow-fix`는 내부적으로 QA mode를 사용한다
- 기존 `flow-qa`, `qa-fix` 호출도 계속 허용한다
