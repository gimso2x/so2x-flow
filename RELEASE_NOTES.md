# Release Notes

## Summary
This handoff summarizes 1 commit(s) across workflow scripts, tests between `0f6cf44` and `HEAD`.

## Commits
- 3f8ff7a test: harden workflow contracts

## Changed files
### workflow scripts
- `.workflow/scripts/hooks/validate-output.sh`
- `.workflow/scripts/workflow_contracts.py`

### tests
- `tests/test_execute.py`
- `tests/test_hooks.py`
- `tests/test_install.py`

## Verification
```bash
python3 -m pytest -q
```
