# so2x-flow

so2x-flow는 Claude Code에서 feature, QA, review, plan 작업을 문서 기준으로 굴리기 위한 docs-first 경량 하네스다.
대화에만 의존하지 않고, 작업 근거와 흐름을 문서로 남기게 만든다.

## 빠른 설치

준비물: Claude Code, Git, Python 3.10+
선택 실행기: `ccs` 또는 `claude` CLI

### 방법 A — Claude Code에 붙여넣기

Claude Code를 프로젝트 루트에서 열고 아래 문구를 그대로 붙여 넣으면 된다.
전역 `~/.claude/skills`가 아니라 현재 프로젝트 내부에 설치시키는 용도다.
긴 원샷 프롬프트로 몰아넣지 말고, 단계가 드러나게 시키는 쪽이 덜 멍청하다.

```text
현재 작업 디렉토리를 프로젝트 루트로 보고 so2x-flow를 설치해줘. 중간 확인 질문 없이 한국어로 진행하고, 새 설계 문서나 task 문서는 만들지 마.
중간 단계 성공만 보고하고 응답을 끝내지 말고, 아래 1~4단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해.
recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고, 실제 실행이 남아 있으면 계속 진행해.

1. `mkdir -p .tmp && git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .tmp/so2x-flow` 를 실행하고 성공/실패를 바로 보고해.
2. `python3 .tmp/so2x-flow/.workflow/scripts/install.py --target . --patch-claude-md` 를 실행하고, install.py가 출력하는 `step 1/4`부터 `step 4/4`까지 그대로 보고해.
3. `.claude/skills/flow-init.md`, `.claude/commands/flow-init.md`, `.workflow/scripts/execute.py`, `.workflow/config/ccs-map.yaml` 존재 여부를 각각 확인해.
4. `rm -rf .tmp/so2x-flow` 와 `rmdir .tmp 2>/dev/null || true` 를 실행해 정리하고, 마지막에 어떤 단계가 성공했고 실패한 단계가 있는지만 짧게 정리해.
5. 마지막 한 줄에는 반드시 다음 실행 안내를 넣어. 문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써.
```

### 방법 B — 셸 설치

Claude Code 말고 바로 설치하고 싶으면 프로젝트 루트에서 아래 순서로 실행하면 된다.
원라이너에 heredoc까지 우겨 넣는 건 복붙 사고 유발기라 뺐다.
검증 실패해도 찌꺼기 안 남기려면 `trap` 거는 게 맞다.

```bash
trap 'rm -rf .tmp/so2x-flow; rmdir .tmp 2>/dev/null || true' EXIT
mkdir -p .tmp
git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .tmp/so2x-flow
python3 .tmp/so2x-flow/.workflow/scripts/install.py --target .
test -f .claude/skills/flow-init.md
test -f .claude/commands/flow-init.md
test -f .workflow/scripts/execute.py
test -f .workflow/config/ccs-map.yaml
trap - EXIT
rm -rf .tmp/so2x-flow
rmdir .tmp 2>/dev/null || true
```

기존 `CLAUDE.md`에 so2x-flow 섹션까지 자동으로 붙이고 싶으면 아래처럼 실행하면 된다.

```bash
trap 'rm -rf .tmp/so2x-flow; rmdir .tmp 2>/dev/null || true' EXIT
mkdir -p .tmp
git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .tmp/so2x-flow
python3 .tmp/so2x-flow/.workflow/scripts/install.py --target . --patch-claude-md
test -f .claude/skills/flow-init.md
test -f .claude/commands/flow-init.md
test -f .workflow/scripts/execute.py
test -f .workflow/config/ccs-map.yaml
trap - EXIT
rm -rf .tmp/so2x-flow
rmdir .tmp 2>/dev/null || true
```

## 핵심 개념

### init vs install

- `install.py` — scaffold 파일을 프로젝트에 복사하고 설치 로그를 남기는 진짜 설치 단계
- `execute.py init` / `flow-init` — 이미 설치된 scaffold를 기준으로 질문 기반 init task를 만들고 dry-run/live 결과를 남기는 운영 단계
- init은 planner를 돌리지 않고 `.workflow/tasks/init/<slug>.json` 질문지만 유지/갱신한다.
- 즉, 설치와 운영 초기화는 일부러 분리돼 있다. 파일 배포는 install, 워크플로우 실행은 init 질문지 작성이다.

### plan vs feature

- `flow-plan` — thinking + planning + approval
- `/flow-plan` — 구현 없이 계획만 수행
- 현재 v0 `/flow-plan`은 `.workflow/tasks/plan/*.json` 하나를 canonical 계획 산출물로 남기는 docs-first 흐름이다.
- `flow-feature`는 생각/비교/재기획 단계가 아니다.
- 승인된 plan이 없으면 구현으로 밀지 않고 멈춘다.
- `--skip-plan`에 쓰려면 `approved: true` 또는 `status: approved`로 명시 승인되어 있어야 한다

## 한 줄 워크플로우

```text
요구사항 입력 -> flow-plan -> 승인 -> flow-feature -> flow-review 또는 flow-qa
```

## 처음 3단계

1. `/flow-init`으로 PRD/ARCHITECTURE/QA/DESIGN 질문지를 만든다.
2. 요구사항이 아직 크거나 애매하면 `/flow-plan`부터 돌린다.
3. 승인된 plan이 생긴 뒤에만 `/flow-feature`로 들어간다.

마지막 한 줄 안내는 항상 이걸 기준으로 보면 된다.
- 다음 단계: /flow-init으로 프로젝트를 초기화하세요.

## 언제 무엇부터 시작하나

### `flow-plan`으로 시작
이런 경우:
- 기능 요구사항이 아직 뭉뚱그려져 있음
- 옵션 비교가 필요함
- 어디까지 만들지 범위를 먼저 정해야 함
- 구현 전에 slice와 검증 기준을 먼저 고정하고 싶음

`flow-plan`이 하는 일:
- 옵션 2~3개 비교
- trade-off 정리
- 추천안 1개 선택
- 구현 slice 분해
- 검증 기준 작성
- canonical plan artifact 저장
- 승인 질문

즉 지금 구조에서 `flow-plan`은 아래를 내부적으로 흡수한다.
- brainstorming
- writing-plans

### `flow-feature`로 시작
이런 경우만:
- 이미 승인된 plan이 있음
- 이번에 구현할 slice가 명확함
- planner/implementer가 새 방향을 발명하면 안 됨

`flow-feature`가 하는 일:
- 승인된 방향 확인
- 이번 최소 구현 slice 선택
- planner -> implementer 실행
- verification 정리

### `flow-qa`로 시작
이런 경우:
- 버그 수정
- QA 이슈 재현/actual/expected가 이미 있음

### `flow-review`로 시작
이런 경우:
- 구현 또는 계획을 문서 기준으로 점검하고 싶음
- Spec Gap / Test Gap / QA Watchpoints를 보고 싶음

## 포함된 흐름

- `flow-init` — PRD/ARCHITECTURE/QA/DESIGN 기준 질문지를 만들고 init task JSON을 남김
- `flow-feature` — 승인된 slice 실행 + 가능하면 TDD + review gate
- `flow-qa` — systematic debugging + test-first bugfix 흐름
- `flow-review` — 문서와 태스크 기준 리뷰 JSON 생성 후 검토 수행
- `flow-plan` — thinking + planning + approval
- `/flow-plan` — 구현 없이 계획만 수행

## 핵심 규칙

- docs first
- Explore → Plan → Implement → Verify 순서 유지
- task/plan 문서 없이 구현하지 않음
- feature와 QA를 같은 급의 workflow로 다룸
- 새 동작/버그 수정은 가능하면 test-first로 진행
- bugfix는 root cause 파악 전 추측성 patch 금지
- 구현 완료는 review gate 통과 전까지 완료가 아님
- slice가 충분히 독립적이면 task 단위 실행/검토를 분리
- scaffold 자체를 수정할 때는 `DESIGN.md`보다 구조/실행 원칙을 먼저 본다
- orchestration은 얇게 유지
- hooks는 `.claude/settings.json`에서 결정론적으로 강제
- v0 기본 검증은 live 실행보다 `--dry-run` 우선

## runner 정책

`.workflow/config/ccs-map.yaml`에서 설정한다.

- `auto` — `ccs`가 있으면 우선 사용
- role별 `ccs_profile` preflight 실패 시 해당 role만 `claude -p`로 fallback
- fallback 이유는 `fallback_reason`에 기록
- `claude` — 항상 `claude -p`
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
- `allow_live_run: false` 가 기본값이다. 실실행은 명시적으로 켜기 전까지 막는다.
- `allow_live_run`은 반드시 YAML boolean `true`/`false` 값이어야 한다. 문자열 `"true"`, `"false"` 같은 값은 허용하지 않는다.

`ccs` shortcut 호출 규약:

```text
ccs <profile> "prompt"
```

주의:
- shortcut 실행에 `-p` 전제 금지
- shortcut 실행에 `--model <same-profile>` 전제 금지
- v0는 실실행보다 dry-run 검증을 우선한다
- `runtime.allow_live_run`은 YAML boolean `true` / `false` 여야 한다

## hooks

`.claude/settings.json`에 들어 있는 guardrail은 말뿐인 훈수가 아니라 실제 hook 연결이다.

- `PreToolUse` + `dangerous-cmd-guard.sh` — 위험한 Bash 명령을 치기 전에 가드
  - 예: `rm -rf`, 무차별 삭제/이동 같은 명령 차단
- `UserPromptSubmit` + `tdd-guard.sh` — task 문서/계획 없이 바로 구현으로 튀는 흐름을 견제
  - 예: task 문서 없이 바로 구현부터 하려는 프롬프트 견제
- `Stop` + `circuit-breaker.sh` — 종료 직전 최소한의 브레이크 포인트 제공
  - 예: 종료 전에 빠진 검증이나 다음 액션 누락 방지

즉, `CLAUDE.md`에 적힌 규칙은 설명이고, 실제 강제는 여기서 한다.

## design 문서 정책

- `DESIGN.md`는 기본적으로 타깃 프로젝트 UI/UX 기준 문서다.
- so2x-flow scaffold 자체를 손볼 때는 이 파일을 억지로 주 참고 문서로 삼지 않는다.
- `.workflow/docs/UI_GUIDE.md`는 legacy fallback이다. 파일이 없으면 그냥 무시하면 된다.

## 바로 써보는 문구

아래는 셸 명령이 아니라 Claude Code에 그대로 붙여 넣는 예시다.

```text
flow-plan으로 "결제 기능 작업 분해" 계획 문서를 만들어줘.
이 flow-plan 방향을 승인한다. 다음 slice 진행 준비해줘.
flow-feature로 "결제 기능 1차 slice"를 승인된 방향 기준으로 진행해줘.
flow-qa로 "QA-001 홈 버튼 클릭 안됨" 이슈 문서를 만들고 dry-run 기준으로 수정 흐름을 준비해줘.
flow-review로 "이번 변경 QA 관점 점검" 리뷰 JSON을 만들어줘.
/flow-plan으로 "결제 기능 작업 분해" 계획 산출물을 만들어줘.
```

## 구성

- `.claude/skills/` — workflow 본체
- `.claude/commands/` — slash command 진입점
- `.claude/settings.json` — Claude hooks / guardrails
- `.workflow/docs/` — PRD / ARCHITECTURE / ADR / QA 문서
- `DESIGN.md` — 타깃 프로젝트용 기본 디자인 기준 문서
- `.workflow/docs/UI_GUIDE.md` — 구버전 호환용 fallback 문서, 없으면 무시 가능
- `.workflow/prompts/` — role prompt 템플릿
- `.workflow/tasks/` — feature / plan / QA / review JSON 템플릿과 생성 산출물
- `.workflow/scripts/execute.py` — orchestrator
- `.workflow/scripts/install.py` — 설치 + 단계 로그 출력
- `.workflow/scripts/patch_claude_md.py` — CLAUDE.md 섹션 패치 스크립트
- `.workflow/scripts/ccs_runner.py` — runner 결정과 command 구성
- `tests/` — dry-run 테스트

## artifact naming

- init 결과: `.workflow/tasks/init/<slug>.json`
- feature 결과: `.workflow/tasks/feature/<slug>.json`
- qa 결과: `.workflow/tasks/qa/<slug>.json`
- plan 결과: `.workflow/tasks/plan/<slug>.json`
  - 기본값: `status: draft`, `approved: false`
- review 결과: `.workflow/tasks/review/<slug>.json`
- run 이력 JSON은 따로 남기지 않는다. 각 task JSON이 canonical 산출물이다.

## 검증

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```
