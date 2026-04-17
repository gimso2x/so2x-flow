# flow-feature

Use this skill when a new product or engineering feature is requested.

## Required flow
1. Read project docs first.
2. Create `.workflow/tasks/feature/<slug>.md` first.
3. Fill `Proposed Steps` with explicit implementation steps.
4. Run planner first.
5. Pass planner output to implementer.
6. In v0, validate with `--dry-run` first and treat live execution as explicit opt-in.
7. Save outputs under `.workflow/outputs/runs/`.

## Rules
- No implementation without a task document.
- `Proposed Steps` is mandatory.
- Planner defines the work.
- Implementer executes the work.
- Do not let implementer re-plan the feature from scratch.
- If `runtime.allow_live_run` is not enabled, stay in dry-run mode.
