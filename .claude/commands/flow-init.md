---
description: Bootstrap the project with so2x-flow init questions and save the canonical init artifact.
allowed-tools: Bash(python3 .workflow/scripts/execute.py:*),Read,Write
argument-hint: [request]
---

Run `python3 .workflow/scripts/execute.py init "$ARGUMENTS"`.

Requirements:
1. Confirm `.workflow/scripts/execute.py` exists first.
2. Keep the run docs-first. Do not start implementation.
3. Report the created init artifact path and the next missing question briefly.
