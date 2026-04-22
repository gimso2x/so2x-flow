---
description: Run an independent review against docs and task artifacts.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py review "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Keep the review independent; do not silently fix code here.
3. Report the saved review artifact and major findings briefly.
