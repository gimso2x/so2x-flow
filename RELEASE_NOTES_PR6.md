# Release Notes — PR #6

## Summary
`so2x-flow` runtime orchestration and docs-first thin-harness structure were further hardened and thinned across execution flow, runtime error handling, plan matching, docs/task helper extraction, artifact validation, and README contract sync.

Latest follow-up commits:
- `48e2796 refactor: harden flow runtime orchestration`
- `18286c9 refactor: set output path only after persistence`
- `7fd7be7 refactor: split execution failure stages`
- `60cf8cd refactor: split workflow docs helpers`

## What changed

### 1. Thinner execution orchestration
- Kept `.workflow/scripts/execute.py` focused on orchestration.
- Moved runtime/live execution concerns into `.workflow/scripts/execution_runtime.py`.
- `execute.py` now mainly does:
  - args/config loading
  - mode context preparation
  - runtime validation
  - role execution dispatch
  - payload persistence/summary

### 2. Better live-run failure handling
- Added role-level runtime validation and execution flow in `execution_runtime.py`.
- Live failures now persist partial success state instead of dropping all prior role results.
- Payloads now record:
  - `failed_role`
  - `failed_stage`
  - `failure_message`
- Failure stage is now more precise:
  - `runner_resolution`
  - `prompt_build`
  - `role_execution`

### 3. Role-specific timeout and clearer subprocess diagnostics
- Added `runtime.role_timeouts.<role>` handling in `.workflow/scripts/ccs_runner.py`.
- Invalid timeout config is rejected early.
- Long subprocess stdout/stderr is truncated into readable snippets.
- Existing fallback reasons are preserved in surfaced failure messages.

### 4. More conservative approved-plan matching
- Tightened plan similarity threshold to `0.75`.
- Switched similarity scoring to directional overlap:
  - `request_overlap * plan_overlap`
- Match reasoning now records request slug, candidate slug, shared tokens, score, and threshold.
- When no plan qualifies, the best below-threshold candidate is still reported for debugging.

### 5. Stronger artifact schema validation and persistence contract
- Expanded `.workflow/scripts/task_artifacts.py` validation beyond top-level field presence.
- Added nested validation for init question shape, allowed statuses, plan option payload shape, feature approved-direction shape, and QA/review list contracts.
- `output_json` is now a post-persistence field only; payload construction no longer guesses the output path before save.

### 6. Smaller helper modules for clearer ownership
- Split docs/design selection and docs bundle assembly into:
  - `.workflow/scripts/workflow_docs.py`
- Split mode-specific task artifact writing into:
  - `.workflow/scripts/workflow_tasks.py`
- Left `.workflow/scripts/workflow_context.py` focused on plan discovery, approval checks, slug helpers, and similarity matching.

### 7. README contract sync
- Reordered and tightened README sections around:
  - `init` vs `install`
  - `plan` vs `feature`
  - one-line workflow
  - included flows
- Current README now better matches actual runner/artifact/runtime behavior.

## Verification
Full suite run:

```bash
pytest -q
```

Result:

```text
75 passed
```

## Result
This update makes `so2x-flow` a sturdier docs-first thin harness by improving:
- orchestration clarity
- helper ownership boundaries
- role runtime isolation
- live failure debuggability
- approved-plan gating accuracy
- artifact safety
- README/implementation alignment
