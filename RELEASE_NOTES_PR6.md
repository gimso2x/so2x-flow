# Release Notes — PR #6

## Summary
`so2x-flow` runtime orchestration was hardened across execution flow, runtime error handling, plan matching, artifact validation, and README contract sync.

Latest follow-up commit:
- `48e2796 refactor: harden flow runtime orchestration`

## What changed

### 1. Thinner execution orchestration
- Kept `.workflow/scripts/execute.py` focused on orchestration.
- Moved runtime/live execution concerns into a new helper module:
  - `.workflow/scripts/execution_runtime.py`
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
- Summary output also surfaces failure metadata directly.

### 3. Role-specific timeout and clearer subprocess diagnostics
- Added `runtime.role_timeouts.<role>` handling in `.workflow/scripts/ccs_runner.py`.
- Invalid timeout config is rejected early.
- Long subprocess stdout/stderr is truncated into readable snippets.
- Existing fallback reasons are preserved in surfaced failure messages.

### 4. More conservative approved-plan matching
- Tightened plan similarity threshold from a loose match to `0.75`.
- Switched similarity scoring to directional overlap:
  - `request_overlap * plan_overlap`
- Match reasoning now records:
  - request slug
  - candidate slug
  - shared tokens
  - score
  - threshold
- When no plan qualifies, the best below-threshold candidate is still reported for debugging.

### 5. Stronger artifact schema validation
- Expanded `.workflow/scripts/task_artifacts.py` validation beyond top-level field presence.
- Added nested validation for:
  - init question shape
  - init/plan allowed statuses
  - plan option payload shape
  - feature `approved_direction` shape
  - qa/review list contracts
- Persisted malformed rerun artifacts now fail fast instead of being silently healed.

### 6. README contract sync
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
72 passed
```

## Result
This update makes `so2x-flow` a sturdier docs-first thin harness by improving:
- orchestration clarity
- role runtime isolation
- live failure debuggability
- approved-plan gating accuracy
- artifact safety
- README/implementation alignment
