## Summary
`so2x-flow` runtime orchestration and docs-first thin-harness structure were further hardened and thinned across execution flow, runtime error handling, plan matching, docs/task helper extraction, artifact validation, and README contract sync.

Latest follow-up commits:
- `48e2796 refactor: harden flow runtime orchestration`
- `18286c9 refactor: set output path only after persistence`
- `7fd7be7 refactor: split execution failure stages`
- `60cf8cd refactor: split workflow docs helpers`
- `1368bfd refactor: extract workflow task writers`

## Highlights
- `execute.py`를 orchestration 중심으로 유지하고 runtime/live role loop를 `execution_runtime.py`로 분리
- live 실패 시 partial role result를 보존하고 `failed_role`, `failed_stage`, `failure_message`를 payload/summary에 기록
- failure stage를 `runner_resolution`, `prompt_build`, `role_execution`으로 세분화
- `runtime.role_timeouts.<role>` 지원 및 잘못된 timeout 설정 조기 검증
- subprocess 실패 메시지에서 stdout/stderr를 길이 제한해 더 읽기 쉽게 정리
- plan similarity threshold를 `0.75`로 높이고 구조화된 match reason / `best_candidate` 보고 추가
- `output_json`은 저장 후에만 채우도록 contract 정리
- docs/design selection과 docs bundle assembly를 `workflow_docs.py`로 분리
- mode별 canonical task artifact write helper를 `workflow_tasks.py`로 분리
- init / plan / feature / qa / review artifact validation 강화
- README를 현재 init/install/plan/feature 계약 기준으로 재정렬

## Verification
```bash
pytest -q
```

Result: `75 passed`
