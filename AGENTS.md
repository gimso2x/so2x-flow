# so2x-flow workspace guide

## Cross-agent surface
- This file is the portable entrypoint for Codex and other coding agents.
- Claude Code users can additionally use `.claude/skills/*` and `.claude/settings.json`, but the workflow contract still lives under `.workflow/`.

## Core workflow
- `flow-init`: bootstrap questions and init artifact only
- `flow-plan`: compare options, lock the approved direction, and save a canonical plan artifact
- `flow-feature`: implement only an approved slice and then close with verification
- `flow-fix` (`flow-qa` alias): reproduce, scope, and repair the smallest safe bug fix
- `flow-review`: run an independent review against docs and task artifacts
- `flow-evaluate`: check readiness after implementation or review

## Rules
- Docs first. Do not implement without a task or plan artifact.
- Create artifacts under `.workflow/tasks/` before coding.
- Keep orchestration thin and keep context explicit.
- Use `DESIGN.md` as the primary design reference and only fall back to `.workflow/docs/UI_GUIDE.md` when it exists.
- Use `.workflow/config/ccs-map.yaml` for runner selection. `auto` prefers `ccs` and falls back to `claude -p`.
- Prefer `--dry-run` and automated tests before any live runner path.

## Agent notes
- Claude Code: use `.claude/skills/flow-init.md`, `.claude/skills/flow-plan.md`, `.claude/skills/flow-feature.md`, `.claude/skills/flow-fix.md`, `.claude/skills/flow-review.md`, `.claude/skills/flow-evaluate.md`.
- Codex and other agents: follow this `AGENTS.md`, inspect `.workflow/docs/*`, and use `.workflow/scripts/execute.py` and `.workflow/scripts/doctor.py` as the canonical workflow surface.
