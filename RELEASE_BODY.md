## Summary
This PR adds release handoff documents for the workflow-contracts validation refactor that is already merged on `main`.

## Commits in this branch
- 8636e87 Add release handoff docs for workflow refactor
- 53da8c6 docs: align release handoff with current PR

## Added files
- `RELEASE_NOTES.md`
- `RELEASE_BODY.md`

## Context covered by the handoff
The handoff documents summarize the already-landed workflow refactor work on `main`, including workflow contract extraction, validation hook tightening, related workflow docs updates, and regression coverage.

## Verification
```bash
python3 -m pytest -q
```
