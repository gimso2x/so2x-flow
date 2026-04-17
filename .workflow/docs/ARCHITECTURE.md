# ARCHITECTURE

## Structure
- `.claude/skills/`: workflow definitions
- `.workflow/docs/`: source-of-truth workflow docs
- `DESIGN.md`: root design reference
- `.workflow/prompts/`: role prompt templates
- `.workflow/tasks/`: generated task documents
- `.workflow/scripts/execute.py`: thin orchestrator
- `.workflow/scripts/ccs_runner.py`: runner resolution and command construction
- `.workflow/outputs/`: run artifacts

## Core Rules
- Docs first.
- No implementation without a task or plan document.
- Keep orchestration thin.
- Feature and QA flows are equal.
- Use `DESIGN.md` as the primary design reference; only fall back to `.workflow/docs/UI_GUIDE.md` for legacy compatibility.

## Data Flow
1. User request enters a mode.
2. Relevant docs and optional design doc are collected.
3. A task or plan document is created if needed.
4. Prompt is built per role.
5. Runner is resolved (`ccs` or `claude`).
6. Role outputs are saved.
7. Run summary is written to `outputs/runs/` or `outputs/plans/`.

## Testing Notes
- v0 focuses on dry-run behavior.
- Each mode should produce stable artifacts.
- Feature and QA should both show planner/qa-planner -> implementer chaining.
- Dry-run output should show requested runner, selected runner, fallback state, and command preview.
