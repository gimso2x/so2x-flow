# so2x-flow

so2x-flow는 Claude Code용 docs-first 경량 하네스다.
feature, QA, review, plan 작업을 채팅에 묻히지 않고 명시적인 markdown 문서로 남기게 만든다.

## Install — 30 seconds

Requirements: Claude Code, Git, Python 3.10+, `ccs` optional, `claude` CLI optional

### Step 1: Install on your machine

Open Claude Code and paste this. Claude does the rest.

```text
Install so2x-flow: run git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .so2x-flow && cd .so2x-flow && python3 scripts/execute.py init "so2x-flow bootstrap" --dry-run then add a "so2x-flow" section to CLAUDE.md that says to use the flow-init, flow-feature, flow-qa, flow-review, and flow-plan skills for docs-first execution, always create task docs before implementation, use DESIGN.md as the primary design reference and docs/UI_GUIDE.md only as fallback, and use config/ccs-map.yaml for runner selection with auto -> ccs when available, otherwise claude -p. Then ask the user if they also want to add so2x-flow to the current project.
```

## Included workflows

- `flow-init` — 워크스페이스 문서/설정 초기화
- `flow-feature` — feature task 문서 생성 후 계획/구현
- `flow-qa` — QA 수정 문서 생성 후 계획/구현
- `flow-review` — 문서/태스크 기준 리뷰만 수행
- `flow-plan` — 구현 없이 계획만 수행

## Core rules

- docs first
- task/plan 문서 없이 구현하지 않음
- feature와 QA를 같은 급의 workflow로 다룸
- `DESIGN.md`를 우선 사용
- orchestration은 얇게 유지

## Runner policy

`config/ccs-map.yaml`에서 설정한다.

- `auto` — `ccs`가 있으면 사용, 없으면 `claude -p`
- `ccs` — `ccs` 사용, 없으면 `claude -p`로 fallback
- `claude` — 항상 `claude -p`

v0는 dry-run 검증을 우선한다.

## Quick commands

아래는 셸 명령이 아니라 Claude Code에 그대로 붙여 넣는 예시다.

```text
flow-init으로 이 프로젝트를 초기화해줘.
flow-feature로 "로그인 기능 구현" 작업 문서를 만들고 dry-run 기준으로 계획/구현 흐름까지 준비해줘.
flow-qa로 "QA-001 홈 버튼 클릭 안됨" 이슈 문서를 만들고 dry-run 기준으로 수정 흐름을 준비해줘.
flow-review로 "이번 변경 QA 관점 점검" 리뷰 문서를 만들어줘.
flow-plan으로 "결제 기능 작업 분해" 계획 문서를 만들어줘.
```

## Layout

- `skills/` — workflow 본체
- `docs/` — PRD / ARCHITECTURE / ADR / QA 문서
- `DESIGN.md` — 디자인 기준 문서
- `prompts/` — role prompt 템플릿
- `tasks/` — feature / QA task 템플릿
- `scripts/execute.py` — orchestrator
- `scripts/ccs_runner.py` — runner 결정과 command 구성
- `tests/` — dry-run 테스트

## Validation

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```
