## Summary
This handoff summarizes 2 commit(s) across workflow scripts, tests, README/release docs between `origin/main~2` and `HEAD`.

## Latest commits
- 67379c0 Tighten workflow docs and feature validation
- d71ef59 Refactor workflow contracts and validation hooks

## Highlights
- workflow scripts: `.workflow/scripts/artifact_renderers.py`, `.workflow/scripts/artifact_schema.py`, `.workflow/scripts/artifact_store.py` 외 15개
- claude workflow assets: `.claude/settings.json`, `.claude/skills/README.md`, `.claude/skills/flow-feature.md` 외 5개
- tests: `tests/test_execute.py`, `tests/test_hooks.py`, `tests/test_install.py`
- repo docs: `README.md`

## Verification
```bash
python3 -m pytest -q
```
