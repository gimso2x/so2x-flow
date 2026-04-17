# so2x-flow workspace guide

## Core workflow skills
- `flow-init`: bootstrap only
- `flow-feature`: create `.workflow/tasks/feature/<slug>.md` first, then execute
- `flow-qa`: create `.workflow/tasks/qa/<slug>.md` first, then execute
- `flow-review`: review against workflow docs and task artifacts
- `flow-plan`: planning only, no implementation

## Claude Code working style
- Follow Explore → Plan → Implement → Verify.
- Read relevant docs and files before editing.
- Use Plan Mode for ambiguous, multi-file, or architectural work.
- Keep context clean and goals explicit.
- Verify with tests, dry-runs, or concrete output evidence before trusting results.

## Principles
- Docs first. Do not implement without a task or plan document.
- Treat feature work and QA work as first-class flows.
- Keep orchestration thin.
- Prefer small explicit documents over hidden state.
- `.claude/skills/` is the workflow source of truth; `.claude/commands/` are thin slash-command wrappers.

## Workflow home
- Shared workflow assets live under `.workflow/`.
- Keep product code at the root. Keep config, docs, prompts, scripts, tasks, and outputs under `.workflow/`.

## Required docs
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- `.workflow/docs/QA.md`
- `DESIGN.md` (target-project UI reference, optional for scaffold-only work)
- `.workflow/docs/UI_GUIDE.md` (legacy fallback only; ignore it if the file does not exist)

## Execution rules
- For feature work, create `.workflow/tasks/feature/<slug>.md` first.
- For QA work, create `.workflow/tasks/qa/<slug>.md` first.
- `Proposed Steps` must exist before implementation.
- Use `.workflow/config/ccs-map.yaml` to select `auto`, `ccs`, or `claude` runner.
- In v0, `.workflow/scripts/execute.py` is validated primarily in `--dry-run` mode.
- `runtime.allow_live_run` stays `false` by default. Live execution is opt-in.
- Use `.claude/settings.json` hooks as deterministic guardrails; do not rely on CLAUDE.md text alone for enforcement.
