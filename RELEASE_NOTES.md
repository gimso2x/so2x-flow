# Release Notes

## Summary
This handoff summarizes 2 commit(s) across workflow scripts, tests, README/release docs between `origin/main~2` and `HEAD`.

## Commits
- 67379c0 Tighten workflow docs and feature validation
- d71ef59 Refactor workflow contracts and validation hooks

## Changed files
### workflow scripts
- `.workflow/scripts/artifact_renderers.py`
- `.workflow/scripts/artifact_schema.py`
- `.workflow/scripts/artifact_store.py`
- `.workflow/scripts/ccs_runner.py`
- `.workflow/scripts/execute.py`
- `.workflow/scripts/hooks/edit-error-recovery.sh`
- `.workflow/scripts/hooks/tool-failure-tracker.sh`
- `.workflow/scripts/hooks/tool-output-truncator.sh`
- `.workflow/scripts/hooks/validate-output.sh`
- `.workflow/scripts/mode_handlers.py`
- `.workflow/scripts/payloads.py`
- `.workflow/scripts/prompt_builder.py`
- `.workflow/scripts/runner_commands.py`
- `.workflow/scripts/runner_execution.py`
- `.workflow/scripts/runner_resolution.py`
- `.workflow/scripts/task_artifacts.py`
- `.workflow/scripts/workflow_contracts.py`
- `.workflow/scripts/workflow_tasks.py`

### claude workflow assets
- `.claude/settings.json`
- `.claude/skills/README.md`
- `.claude/skills/flow-feature.md`
- `.claude/skills/flow-init.md`
- `.claude/skills/flow-plan.md`
- `.claude/skills/flow-qa.md`
- `.claude/skills/flow-review.md`
- `CLAUDE.md`

### tests
- `tests/test_execute.py`
- `tests/test_hooks.py`
- `tests/test_install.py`

### repo docs
- `README.md`

## Verification
```bash
python3 -m pytest -q
```
