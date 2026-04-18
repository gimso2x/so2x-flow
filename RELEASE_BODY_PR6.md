## Summary
so2x-flow thin harness contracts were tightened across execution, validation, docs, and onboarding.

## Included
- #1 execute.py 분해
- #2 live execution failure diagnostics 강화
- #3 workflow task artifact validation 추가
- #4 README / CLAUDE / flow docs 공통 계약 drift 테스트 강화
- #5 install / first-run UX 개선

## Highlights
- `execute.py`를 더 얇게 유지하도록 helper 모듈 분리
- live runner 실패 메시지에 `stdout`, `stderr`, `fallback_reason` 포함
- init / plan / feature / qa / review artifact validation 추가
- README / CLAUDE / flow docs 간 공통 workflow 계약 테스트 강화
- install 출력에 `/flow-init -> /flow-plan -> /flow-feature` 첫 사용 경로 명시

## Verification
```bash
pytest tests/test_execute.py tests/test_ccs_runner.py tests/test_install.py -q
```

Result: `57 passed`
