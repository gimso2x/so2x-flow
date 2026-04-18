# Release Notes — PR #6

## Summary
`so2x-flow` thin harness contracts were tightened across execution, validation, docs, and onboarding.

Merged PR:
- `#6 refactor: harden so2x-flow thin harness contracts`

Included issues:
- #1 execute.py 분해
- #2 live execution failure diagnostics 강화
- #3 workflow task artifact schema validation 추가
- #4 README / CLAUDE / flow docs 공통 계약 drift 테스트 강화
- #5 install / first-run UX 개선

## What changed

### 1. Thinner execution orchestration
- Split `.workflow/scripts/execute.py` responsibilities into helper modules:
  - `.workflow/scripts/mode_handlers.py`
  - `.workflow/scripts/payloads.py`
  - `.workflow/scripts/prompt_builder.py`
- Kept `execute.py` as a thinner entrypoint/orchestrator.

### 2. Better live-run diagnostics
- Improved live runner subprocess failures in `.workflow/scripts/ccs_runner.py`.
- Failure messages now include:
  - stdout
  - stderr
  - fallback reason when relevant
- Timeout paths can now surface fallback context too.

### 3. Stronger artifact contracts
- Added explicit workflow task artifact validation in `.workflow/scripts/task_artifacts.py`.
- Validation now covers generated artifacts for:
  - init
  - plan
  - feature
  - qa
  - review
- Required fields and basic types are now enforced before write/finalization.

### 4. Doc contract locking
- Added tests to keep shared workflow rules aligned across:
  - `README.md`
  - `CLAUDE.md`
  - `.claude/commands/*`
  - `.claude/skills/*`
- Locked contracts include:
  - role-level `ccs_profile` fallback behavior
  - approved-plan gating before feature execution
  - canonical plan artifact path expectations
  - install/init separation

### 5. Clearer install and first-run path
- Improved install output with explicit next-step guidance:
  - `next_step_cli: /flow-init`
  - `first_run_path: /flow-init -> /flow-plan -> /flow-feature`
- Added a `README` section documenting the first 3 steps after install.

## Verification
Test suite run:

```bash
pytest tests/test_execute.py tests/test_ccs_runner.py tests/test_install.py -q
```

Result:

```text
57 passed
```

## Result
This release makes the harness more reliable as a docs-first thin-core workflow scaffold by improving:
- orchestration clarity
- live failure debuggability
- artifact safety
- cross-doc consistency
- first-run usability
