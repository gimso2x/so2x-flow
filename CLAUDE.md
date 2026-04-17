# so2x-flow workspace guide

## Core workflow skills
- `flow-init`: bootstrap only
- `flow-feature`: create feature task doc first, then execute
- `flow-qa`: create QA task doc first, then execute
- `flow-review`: review against docs/tasks
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

## Required docs
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/QA.md`
- `DESIGN.md` (primary design reference)
- `docs/UI_GUIDE.md` (legacy fallback only)

## Execution rules
- For feature work, create `tasks/feature/<slug>.md` first.
- For QA work, create `tasks/qa/<slug>.md` first.
- `Proposed Steps` must exist before implementation.
- Use `config/ccs-map.yaml` to select `auto`, `ccs`, or `claude` runner.
- In v0, `scripts/execute.py` is validated primarily in `--dry-run` mode.
- Use `.claude/settings.json` hooks as deterministic guardrails; do not rely on CLAUDE.md text alone for enforcement.
