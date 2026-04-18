## Summary
`so2x-flow` runtime orchestration was hardened across execution flow, runtime error handling, plan matching, artifact validation, and README contract sync.

Latest follow-up commit:
- `48e2796 refactor: harden flow runtime orchestration`

## Highlights
- `execute.py`를 orchestration 중심으로 더 얇게 유지하고 `execution_runtime.py`로 runtime/live role loop를 분리
- live 실패 시 partial role result를 보존하고 `failed_role`, `failed_stage`, `failure_message`를 payload/summary에 기록
- `runtime.role_timeouts.<role>` 지원 및 잘못된 timeout 설정 조기 검증
- subprocess 실패 메시지에서 stdout/stderr를 길이 제한해 더 읽기 쉽게 정리
- plan similarity threshold를 `0.75`로 높이고 구조화된 match reason / `best_candidate` 보고 추가
- init / plan / feature / qa / review artifact validation 강화
- README를 현재 init/install/plan/feature 계약 기준으로 재정렬

## Verification
```bash
pytest -q
```

Result: `72 passed`
