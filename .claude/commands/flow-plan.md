---
description: Create or refresh an approval-ready implementation plan without coding.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py plan "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Do not auto-transition into implementation.
3. End by pointing to the saved plan artifact and approval gate.
