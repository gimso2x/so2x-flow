# so2x-flow workspace guide

## Core workflow skills
- `flow-init`: bootstrap only
- `flow-feature`: execute only after an approved plan exists
- `flow-qa`: create `.workflow/tasks/qa/<slug>.json` first, then execute
- `flow-review`: review against workflow docs and task artifacts
- `flow-plan`: thinking + planning + approval, no implementation

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
- Start ambiguous or new requirements with `flow-plan` first.
- `flow-plan` absorbs brainstorming + writing-plans and leaves an approved canonical plan artifact.
- For feature work, only execute `flow-feature` after an approved plan exists, then create the feature task document first.
- For QA work, create `.workflow/tasks/qa/<slug>.json` first.
- `Proposed Steps` must exist before implementation.
- New behavior or bugfix work should prefer TDD: failing reproduction/test first, then minimal code.
- QA/debug work should follow root-cause-first debugging; do not guess-fix before reproduction and investigation.
- Slice completion should pass a review gate (spec compliance / quality / regression risk) before being treated as done.
- If work splits cleanly, prefer subagent-style task isolation per slice rather than one giant mixed execution context.
- Use `.workflow/config/ccs-map.yaml` to select `auto`, `ccs`, or `claude` runner.
- In v0, `.workflow/scripts/execute.py` is validated primarily in `--dry-run` mode.
- `runtime.allow_live_run` must be a real YAML boolean (`true` or `false`), not a string.
- `ccs` shortcut roles run as `ccs <profile> "prompt"`; do not assume `-p` or `--model` for shortcut execution.
- If a configured `ccs_profile` is missing, execute-level preflight falls back that role to `claude -p` when Claude is available; the reason is printed in `fallback_reason`.
- Use `.claude/settings.json` hooks as deterministic guardrails; do not rely on CLAUDE.md text alone for enforcement.
