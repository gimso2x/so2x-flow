# flow-qa

Use this skill when a QA issue or bug report needs a document-first fix flow.

## Required flow
1. Read `.workflow/docs/QA.md` first.
2. Create `.workflow/tasks/qa/<slug>.md` first.
3. Capture reproduction, expected, actual, minimal fix, and regression checklist.
4. Run QA planner first.
5. Pass QA planner output to implementer.
6. In v0, validate with `--dry-run` first and treat live execution as explicit opt-in.
7. Save outputs under `.workflow/outputs/runs/`.

## Rules
- QA is a first-class flow, not a sub-case of feature work.
- Prefer the smallest safe fix.
- Do not skip the QA task document.
- Keep regression notes explicit.
- If `runtime.allow_live_run` is not enabled, stay in dry-run mode.
