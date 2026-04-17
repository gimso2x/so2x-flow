# flow-init

Use this skill to bootstrap a new so2x-flow workspace.

## Input
- 프로젝트 초기화 요청
- 필요하면 bootstrap 목적이나 운영 메모

## Required docs
- `CLAUDE.md`
- `.workflow/config/ccs-map.yaml`
- `.workflow/docs/PRD.md`
- `.workflow/docs/ARCHITECTURE.md`
- `.workflow/docs/ADR.md`
- `.workflow/docs/QA.md`

## Outputs
- 기존 scaffold 파일 존재 확인
- `.workflow/outputs/runs/` 아래 init 결과 요약
- 필요한 디렉터리 존재 보장

## Forbidden
- feature 구현 시작 금지
- branch/commit 자동화 금지
- live 실행 강제 금지

## Runtime policy
- v0 기본은 `--dry-run`
- live 실행은 `runtime.allow_live_run=true`일 때만 허용
