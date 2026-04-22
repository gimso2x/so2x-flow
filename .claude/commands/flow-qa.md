---
description: Alias for flow-fix / QA bug workflow.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write,Edit
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py qa "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Keep the scope to reproduction and the smallest safe QA fix slice.
3. Report the saved QA artifact and verification result briefly.
