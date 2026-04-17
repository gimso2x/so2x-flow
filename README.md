# so2x-flow

so2x-flow는 Claude Code용 docs-first 경량 하네스다.
feature, QA, review, plan 작업을 채팅에 묻히지 않고 명시적인 markdown 문서로 남기게 만든다.

## 설치

준비물
- Claude Code
- Git
- Python 3.10+
- `ccs` 선택
- `claude` CLI 선택

Claude Code에서 대상 프로젝트를 연 다음 아래 문구를 그대로 붙여 넣으면 된다.

```text
so2x-flow를 설치해줘: git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .so2x-flow && cd .so2x-flow && python3 scripts/execute.py init "so2x-flow bootstrap" --dry-run 을 실행하고, CLAUDE.md에 "so2x-flow" 섹션을 추가해서 docs-first 실행에는 flow-init, flow-feature, flow-qa, flow-review, flow-plan 스킬을 사용하고, 구현 전에 항상 task 문서를 먼저 만들고, DESIGN.md를 기본 디자인 기준 문서로 쓰고 docs/UI_GUIDE.md는 fallback으로만 쓰고, runner 선택은 config/ccs-map.yaml을 따르며 auto면 ccs가 있으면 ccs, 없으면 claude -p를 쓰도록 적어줘.
```

## 포함된 흐름

- `flow-init` — 워크스페이스 문서/설정 초기화
- `flow-feature` — feature task 문서 생성 후 계획/구현
- `flow-qa` — QA 수정 문서 생성 후 계획/구현
- `flow-review` — 문서/태스크 기준 리뷰만 수행
- `flow-plan` — 구현 없이 계획만 수행

## 핵심 규칙

- docs first
- task/plan 문서 없이 구현하지 않음
- feature와 QA를 같은 급의 workflow로 다룸
- `DESIGN.md`를 우선 사용
- orchestration은 얇게 유지

## runner 정책

`config/ccs-map.yaml`에서 설정한다.

- `auto` — `ccs`가 있으면 사용, 없으면 `claude -p`
- `ccs` — `ccs` 사용, 없으면 `claude -p`로 fallback
- `claude` — 항상 `claude -p`

v0는 dry-run 검증을 우선한다.

## 빠른 실행 예시

```bash
python3 scripts/execute.py init "new project bootstrap" --dry-run
python3 scripts/execute.py feature "로그인 기능 구현" --dry-run
python3 scripts/execute.py qa "QA-001 홈 버튼 클릭 안됨" --qa-id QA-001 --dry-run
python3 scripts/execute.py review "이번 변경 QA 관점 점검" --dry-run
python3 scripts/execute.py plan "결제 기능 작업 분해" --dry-run
```

## 구성

- `skills/` — workflow 본체
- `docs/` — PRD / ARCHITECTURE / ADR / QA 문서
- `DESIGN.md` — 디자인 기준 문서
- `prompts/` — role prompt 템플릿
- `tasks/` — feature / QA task 템플릿
- `scripts/execute.py` — orchestrator
- `scripts/ccs_runner.py` — runner 결정과 command 구성
- `tests/` — dry-run 테스트

## 검증

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```
