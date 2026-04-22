---
description: Reproduce and fix the smallest safe bug slice with so2x-flow.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write,Edit
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py flow-fix "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Keep the scope to reproduction and the smallest safe fix.
3. Report the saved QA/fix artifact and verification result briefly.
