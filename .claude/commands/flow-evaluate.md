---
description: Check implementation readiness after feature or review work.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py evaluate "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Keep the run focused on readiness gates, not new implementation.
3. Report the saved evaluate artifact and recommended next step briefly.
