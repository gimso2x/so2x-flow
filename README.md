# so2x-flow

so2x-flow는 Claude Code에서 feature, QA, review, plan 작업을 문서 기준으로 굴리기 위한 docs-first 경량 하네스다.
대화에만 의존하지 않고, 작업 근거와 흐름을 markdown으로 남기게 만든다.

## 설치 — 30초

준비물: Claude Code, Git, Python 3.10+, `ccs` 선택, `claude` CLI 선택

### 1단계: 내 환경에 설치

Claude Code를 열고 아래 문구를 그대로 붙여 넣으면 된다. 나머지는 Claude가 처리하게 하면 된다.

```text
Install so2x-flow: run git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .so2x-flow && cd .so2x-flow && python3 scripts/execute.py init "so2x-flow bootstrap" --dry-run then add a "so2x-flow" section to CLAUDE.md that says to use the flow-init, flow-feature, flow-qa, flow-review, and flow-plan skills for docs-first execution, always create task docs before implementation, use DESIGN.md as the primary design reference and docs/UI_GUIDE.md only as fallback, and use config/ccs-map.yaml for runner selection with auto -> ccs when available, otherwise claude -p.
```

## 포함된 흐름

- `flow-init` — 워크스페이스 문서와 설정 초기화
- `flow-feature` — feature task 문서 생성 후 계획/구현
- `flow-qa` — QA 수정 문서 생성 후 계획/구현
- `flow-review` — 문서와 태스크 기준 리뷰만 수행
- `flow-plan` — 구현 없이 계획만 수행

## 핵심 규칙

- docs first
- task/plan 문서 없이 구현하지 않음
- feature와 QA를 같은 급의 workflow로 다룸
- `DESIGN.md`를 기본 디자인 기준 문서로 사용
- orchestration은 얇게 유지

## runner 정책

`config/ccs-map.yaml`에서 설정한다.

- `auto` — `ccs`가 있으면 사용, 없으면 `claude -p`
- `ccs` — `ccs` 사용, 없으면 `claude -p`로 fallback
- `claude` — 항상 `claude -p`

v0는 실실행보다 dry-run 검증을 우선한다.

## 바로 써보는 문구

아래는 셸 명령이 아니라 Claude Code에 그대로 붙여 넣는 예시다.

```text
flow-init으로 이 프로젝트를 초기화해줘.
flow-feature로 "로그인 기능 구현" 작업 문서를 만들고 dry-run 기준으로 계획/구현 흐름까지 준비해줘.
flow-qa로 "QA-001 홈 버튼 클릭 안됨" 이슈 문서를 만들고 dry-run 기준으로 수정 흐름을 준비해줘.
flow-review로 "이번 변경 QA 관점 점검" 리뷰 문서를 만들어줘.
flow-plan으로 "결제 기능 작업 분해" 계획 문서를 만들어줘.
```

## 구성

- `skills/` — workflow 본체
- `docs/` — PRD / ARCHITECTURE / ADR / QA 문서
- `DESIGN.md` — 기본 디자인 기준 문서
- `docs/UI_GUIDE.md` — 구버전 호환용 fallback 문서
- `prompts/` — role prompt 템플릿
- `tasks/` — feature / QA task 템플릿
- `scripts/execute.py` — orchestrator
- `scripts/ccs_runner.py` — runner 결정과 command 구성
- `tests/` — dry-run 테스트

## 검증

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```
