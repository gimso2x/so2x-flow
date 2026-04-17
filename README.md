# so2x-flow

여기서 멈춰도 된다.
이게 필요한 사람은 보면 바로 안다.

so2x-flow는 Claude Code용 docs-first 경량 하네스다.
feature, QA, review, plan 작업을 채팅 안에 묻히지 않고 명시적인 markdown 문서로 남기게 만든다.

이런 쪽이면 맞다.
- feature와 QA를 같은 급으로 다루고 싶다
- 구현 전에 task 문서를 먼저 만들고 싶다
- 리뷰를 감이 아니라 문서 기준으로 하고 싶다
- 거대한 프레임워크 말고 얇은 orchestration만 원한다

## 설치 — 30초

준비물
- Claude Code
- Git
- Python 3.10+
- `ccs` 있으면 좋음
- fallback용 `claude` CLI 있으면 좋음

### 1단계: 내 환경에 설치

대상 프로젝트에서 Claude Code를 열고 아래 문구를 그대로 붙여 넣으면 된다.
Claude가 나머지를 처리하게 하면 된다.

```text
so2x-flow를 설치해줘: git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .so2x-flow && cd .so2x-flow && python3 scripts/execute.py init "so2x-flow bootstrap" --dry-run 을 실행하고, 그다음 CLAUDE.md에 "so2x-flow" 섹션을 추가해서 docs-first 실행에는 flow-init, flow-feature, flow-qa, flow-review, flow-plan 스킬을 사용하고, 구현 전에 항상 task 문서를 먼저 만들고, 디자인 기준 문서는 DESIGN.md를 우선으로 쓰되 docs/UI_GUIDE.md는 fallback으로만 쓰고, runner 선택은 config/ccs-map.yaml을 따르며 auto면 ccs가 있으면 ccs, 없으면 claude -p를 쓰도록 적어줘. 그리고 마지막에 이 프로젝트에도 so2x-flow를 같이 넣어서 팀원들이 같은 workflow를 쓰게 할지 물어봐줘.
```

### 2단계: 팀 모드 — 공유 레포에 넣기

추천 구조는 이렇다.

```text
<project-root>/
  CLAUDE.md
  DESIGN.md
  docs/
    PRD.md
    ARCHITECTURE.md
    ADR.md
    QA.md
  .so2x-flow/
```

팀원도 같은 흐름을 쓰게 하려면 아래를 같이 커밋하면 된다.
- `.so2x-flow/`
- `CLAUDE.md`
- `DESIGN.md`
- `docs/` 기본 문서들

## 이걸로 얻는 것

핵심 workflow skill
- `flow-init` — 워크스페이스 문서/설정 bootstrap
- `flow-feature` — feature task 문서 생성 후 계획/구현
- `flow-qa` — QA 수정 문서 생성 후 계획/구현
- `flow-review` — 문서/태스크 기준 리뷰만 수행
- `flow-plan` — 구현 없이 계획만 수행

핵심 규칙
- docs first
- task/plan 문서 없이 구현하지 않음
- feature와 QA는 같은 급의 workflow
- `DESIGN.md`를 `docs/UI_GUIDE.md`보다 우선 사용
- orchestration은 얇게 유지

## runner 정책

`config/ccs-map.yaml`에서 설정한다.

지원 모드
- `auto` — `ccs`가 있으면 쓰고, 없으면 `claude -p`로 fallback
- `ccs` — `ccs`를 우선 쓰고, 없으면 `claude -p`로 fallback하고 로그에 남김
- `claude` — 항상 `claude -p` 사용

v0는 실실행보다 dry-run 검증을 우선한다.

## 빠른 시작

초기화

```bash
python3 scripts/execute.py init "new project bootstrap" --dry-run
```

feature 흐름

```bash
python3 scripts/execute.py feature "로그인 기능 구현" --dry-run
```

QA 흐름

```bash
python3 scripts/execute.py qa "QA-001 홈 버튼 클릭 안됨" --qa-id QA-001 --dry-run
```

review 흐름

```bash
python3 scripts/execute.py review "이번 변경 QA 관점 점검" --dry-run
```

plan 흐름

```bash
python3 scripts/execute.py plan "결제 기능 작업 분해" --dry-run
```

## 레포 구성

- `skills/` — workflow 본체
- `docs/` — PRD / ARCHITECTURE / ADR / QA 문서
- `DESIGN.md` — 디자인 기준 문서
- `prompts/` — role prompt 템플릿
- `tasks/` — feature / QA task 템플릿
- `scripts/execute.py` — 얇은 orchestrator
- `scripts/ccs_runner.py` — runner 결정과 command 구성
- `tests/` — dry-run 중심 테스트

## 검증

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```

현재 기준
- 16 tests passing

## 이런 경우엔 안 맞다

이런 걸 원하면 안 맞을 수 있다.
- 무거운 orchestration
- 브랜치/배포 자동화가 먼저인 구조
- 문서보다 숨겨진 agent state 중심 흐름
- QA를 부가 작업 정도로만 다루는 방식
