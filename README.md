# so2x-flow

Stop there. You'll know if this is for you.

so2x-flow is a docs-first lightweight harness for Claude Code.
It turns feature work, QA work, review, and planning into explicit markdown artifacts instead of hidden chat state.

If you want:
- feature and QA treated equally
- task docs before implementation
- review against docs, not vibes
- thin orchestration instead of a giant framework

this is for you.

## Install — 30 seconds

Requirements:
- Claude Code
- Git
- Python 3.10+
- `ccs` optional
- `claude` CLI optional as fallback runner

Step 1: Install on your machine

Open Claude Code in the target project and paste this. Claude does the rest.

```text
Install so2x-flow: run git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .so2x-flow && cd .so2x-flow && python3 scripts/execute.py init "so2x-flow bootstrap" --dry-run, then add a "so2x-flow" section to CLAUDE.md that says to use the skills flow-init, flow-feature, flow-qa, flow-review, and flow-plan for docs-first execution, to always create task docs before implementation, to treat DESIGN.md as the primary design reference with docs/UI_GUIDE.md as fallback only, and to use config/ccs-map.yaml for runner selection with auto -> ccs if available, otherwise claude -p. Then ask the user if they also want to add so2x-flow to the current project so teammates get the same workflow.
```

Step 2: Team mode — shared repo setup

Recommended project layout:

```text
<project-root>/
  CLAUDE.md
  DESIGN.md
  docs/
    PRD.md
    ARCHITECTURE.md
    ADR.md
    QA.md
  .so2x-flow/
```

Commit `.so2x-flow/`, `CLAUDE.md`, `DESIGN.md`, and the `docs/` skeleton if you want teammates to use the same workflow.

## What it gives you

Core workflow skills:
- `flow-init` — bootstrap workspace docs and config
- `flow-feature` — create feature task doc, then plan and implement
- `flow-qa` — create QA fix doc, then plan and implement
- `flow-review` — review against docs and tasks only
- `flow-plan` — planning only, no implementation

Core rules:
- docs first
- no implementation without a task or plan doc
- feature and QA are equal workflows
- `DESIGN.md` is preferred over `docs/UI_GUIDE.md`
- orchestration stays thin

## Runner policy

Configured in `config/ccs-map.yaml`.

Supported modes:
- `auto` — use `ccs` if installed, otherwise fall back to `claude -p`
- `ccs` — prefer `ccs`; if missing, fall back to `claude -p` and log it
- `claude` — always use `claude -p`

v0 is validated primarily through dry-run execution.

## Quick start

Bootstrap:

```bash
python3 scripts/execute.py init "new project bootstrap" --dry-run
```

Feature flow:

```bash
python3 scripts/execute.py feature "로그인 기능 구현" --dry-run
```

QA flow:

```bash
python3 scripts/execute.py qa "QA-001 홈 버튼 클릭 안됨" --qa-id QA-001 --dry-run
```

Review flow:

```bash
python3 scripts/execute.py review "이번 변경 QA 관점 점검" --dry-run
```

Plan flow:

```bash
python3 scripts/execute.py plan "결제 기능 작업 분해" --dry-run
```

## Repository contents

- `skills/` — workflow source of truth
- `docs/` — product, architecture, ADR, QA inputs
- `DESIGN.md` — design reference
- `prompts/` — role prompts
- `tasks/` — feature and QA task templates
- `scripts/execute.py` — thin orchestrator
- `scripts/ccs_runner.py` — runner resolution and command construction
- `tests/` — dry-run oriented test suite

## Validation

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```

Current baseline:
- 16 tests passing

## Not for you

Skip this if you want:
- heavy orchestration
- branch automation first
- hidden agent state over docs
- QA treated as a side quest
