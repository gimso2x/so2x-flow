# Release Notes

## Summary
This branch adds release handoff documents for the workflow-contracts validation refactor that is already merged on `main`.

## Commits
- 8636e87 Add release handoff docs for workflow refactor

## Added files
- `RELEASE_NOTES.md`
- `RELEASE_BODY.md`

## Covers
These handoff docs summarize the already-landed workflow refactor work from `main`, including:
- workflow contract extraction and validation-hook refactor
- related README / CLAUDE / skill docs updates
- execute / hooks / install regression coverage

## Verification
```bash
python3 -m pytest -q
```
