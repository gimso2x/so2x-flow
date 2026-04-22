# PRD

## Goal
- Build a docs-first lightweight harness for feature, QA, review, and planning workflows.

## Users
- Primary user: solo builder using Claude Code and lightweight agent workflows.
- Additional surface: Codex or another coding agent reading the same workflow through `AGENTS.md` and `.workflow/`.
- Secondary user: future maintainer who needs explicit docs.

## Scope
- Skill-based lightweight harness.
- Portable root guide via `AGENTS.md` while keeping `.claude/` as an optional Claude-specific surface.
- Docs-first task and plan generation.
- Dry-run orchestration for init, feature, qa, review, and plan modes.
- Config-driven runner selection with `ccs`/`claude` fallback.

## Out of Scope
- Git branch/commit/push automation.
- Heavy orchestration or phase state machines.
- Mandatory live provider integration in v0.

## Acceptance
- All skill files and templates exist.
- `.workflow/scripts/execute.py` runs in `--dry-run` for all supported modes.
- Feature and QA flows both create task docs and run planner -> implementer chaining.
- Design context uses `DESIGN.md` as the default source of truth and only falls back to `.workflow/docs/UI_GUIDE.md` for legacy compatibility.
