# so2x-flow skills

This directory contains the workflow source of truth for so2x-flow.

Skills:
- `flow-init`
- `flow-feature`
- `flow-qa`
- `flow-review`
- `flow-plan`

핵심 실사용 루프도 skill 기준으로 본다.
- 구현/테스트 완료
- `/simplify` 반복
- convergence `0`
- squash
- 필요하면 `flow-review` / `flow-qa`
- GitHub PR 운영은 선택 사항

`/simplify`는 별도 `flow-*` skill이 아니라, 보통 `flow-feature` 완료 뒤 또는 승인된 plan 기준 구현이 끝난 뒤에 도는 마감 루프다.

These skills define behavior. Optional slash commands, if added later, should only be thin wrappers around these skill docs.
