# so2x-flow

so2x-flow는 Claude Code에서 기능 구현, QA, 리뷰, 계획 작업을 문서 중심으로 굴리는 얇은 워크플로우 하네스다.
핵심은 간단하다. 대화에만 기대지 말고, 판단 근거와 다음 액션을 문서와 JSON 산출물로 남긴다.

## 빠른 설치

준비물
- Claude Code
- Git
- Python 3.10+
- 선택 실행기: `ccs` 또는 `claude` CLI

### 방법 A — Claude Code에 그대로 붙여넣기

프로젝트 루트에서 Claude Code를 열고 아래 문구를 그대로 붙여 넣으면 된다.
목표는 전역 `~/.claude/skills` 설치가 아니라 현재 프로젝트 내부 설치다.
원샷으로 대충 끝내기보다, 단계가 보이게 시키는 편이 안전하다.

```text
현재 작업 디렉토리를 프로젝트 루트로 보고 so2x-flow를 설치해줘. 중간 확인 질문 없이 한국어로 진행하고, 새 설계 문서나 task 문서는 만들지 마.
중간 단계 성공만 보고하고 응답을 끝내지 말고, 아래 1~5단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해.
recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고, 실제 실행이 남아 있으면 계속 진행해.

1. `mkdir -p .tmp && git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-flow.git .tmp/so2x-flow` 를 실행하고 성공/실패를 바로 보고해.
2. `python3 .tmp/so2x-flow/.workflow/scripts/install.py --target . --patch-claude-md` 를 실행하고, install.py가 출력하는 `step 1/4`부터 `step 4/4`까지 그대로 보고해.
3. `.claude/skills/flow-init.md`, `.claude/commands/flow-init.md`, `.workflow/scripts/execute.py`, `.workflow/config/ccs-map.yaml` 존재 여부를 각각 확인해.
4. `rm -rf .tmp/so2x-flow` 와 `rmdir .tmp 2>/dev/null || true` 를 실행해 정리하고, 마지막에 어떤 단계가 성공했고 실패한 단계가 있는지만 짧게 정리해.
5. 마지막 한 줄에는 반드시 다음 실행 안내를 넣어. 문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써.
```

### 방법 B — 셸에서 바로 설치

Claude Code 대신 셸에서 바로 설치해도 된다.
복붙 실수를 줄이려고 원라이너와 heredoc은 일부러 피했다.
검증 중 실패해도 임시 파일이 남지 않게 `trap`을 걸어 둔다.

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

기존 `CLAUDE.md`에 so2x-flow 섹션까지 같이 붙이고 싶으면 `--patch-claude-md`를 추가하면 된다.

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

- `install.py`: scaffold 파일을 프로젝트로 복사하는 설치 단계
- `execute.py init` / `flow-init`: 이미 설치된 scaffold를 바탕으로 init 질문지를 만드는 운영 단계
- init은 planner를 돌리지 않고 `.workflow/tasks/init/<slug>.json` 질문지만 유지/갱신한다.
- 설치와 운영 초기화는 분리돼 있다. 파일 배포는 install, 첫 질문지는 init이 맡는다.

### plan vs feature

- `flow-plan`: thinking + planning + approval
- `/flow-plan`: 구현 없이 계획만 수행
- `/flow-plan`은 `.workflow/tasks/plan/*.json` 하나를 canonical 계획 산출물로 남기는 docs-first 흐름이다.
- `flow-feature`는 생각/비교/재기획 단계가 아니다.
- 승인된 plan이 없으면 구현으로 밀지 않고 멈춘다.
- `--skip-plan`에 쓰려면 `approved: true` 또는 `status: approved`로 명시 승인되어 있어야 한다.

## 한 줄 워크플로우

```text
구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-qa -> GitHub PR 운영은 옵션
```

## 실사용 기본 경로

실제로는 아래 순서로 보면 된다.
`/simplify`는 별도 `flow-*` workflow가 아니라, `flow-feature` 완료 뒤나 승인된 plan 기준 구현이 끝난 뒤에 붙는 마감 루프다.

1. 필요하면 `/flow-plan`으로 방향과 slice를 먼저 고정한다.
2. `/flow-feature`로 구현과 테스트를 끝낸다.
3. `/simplify`를 반복한다.
4. convergence가 `0`이 될 때까지 다시 `/simplify`를 돈다.
5. convergence `0`이 되면 squash commit으로 정리한다.
6. 필요하면 `flow-review`, `flow-qa`를 추가한다.
7. GitHub PR 생성/본문 반영/checks watch는 필요할 때만 붙인다.

## 처음 3단계

1. `/flow-init`으로 PRD/ARCHITECTURE/QA/DESIGN 질문지를 만든다.
2. 요구사항이 아직 크거나 애매하면 `/flow-plan`부터 돌린다.
3. 승인된 plan이 생긴 뒤에만 `/flow-feature`로 들어간다.

`flow-init`은 시작할 때 초기화 방식을 하나 고르게 하고, 기본은 질문부터 시작이다.
원하면 `지금 자동 초안 작성`으로 바로 채우고, `작업 진행 후 자동 채우기`로 init 질문을 뒤로 미룰 수도 있다.

## doctor/status surface

최근 상태만 빠르게 읽고 싶으면 아래 둘 중 하나를 쓰면 된다.

```bash
python3 .workflow/scripts/doctor.py --brief
python3 .workflow/scripts/execute.py doctor
```

- doctor는 read-only 상태 surface다.
- 상태 JSON은 `.workflow/outputs/doctor/status.json`에 남긴다.
- 기본 필드: `overall_status`, `exact_status`, `blocked_reason`, `latest_summary`, `latest_output_json`, `latest_outputs`, `latest_tasks`, `last_event`
- `waiting:init`은 init 질문 응답 대기, `waiting:approval`은 plan 승인 대기, `blocked:*`는 최신 실패 payload 기준이다.

마지막 한 줄 안내는 항상 이걸 기준으로 보면 된다.
- 다음 단계: /flow-init으로 프로젝트를 초기화하세요.

## 언제 무엇부터 시작하나

### `flow-plan`으로 시작

이럴 때 먼저 쓴다.
- 요구사항이 아직 뭉뚱그려져 있다
- 옵션 비교가 필요하다
- 범위를 먼저 고정해야 한다
- 구현 전에 slice와 검증 기준을 정리하고 싶다

`flow-plan`이 남기는 것
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

이 경우에만 바로 들어간다.
- 이미 승인된 plan이 있다
- 이번에 구현할 slice가 분명하다
- planner/implementer가 새 방향을 만들면 안 된다

`flow-feature`가 맡는 일
- 승인된 방향 확인
- 이번 최소 구현 slice 선택
- planner -> implementer 실행
- verification 정리

### `flow-qa`로 시작

이럴 때 쓴다.
- 버그 수정
- QA 이슈 재현/actual/expected가 이미 정리돼 있다

### `flow-review`로 시작

이럴 때 쓴다.
- 구현 또는 계획을 문서 기준으로 다시 점검하고 싶다
- Spec Gap / Test Gap / QA Watchpoints가 필요하다

## 포함된 흐름

- `flow-init` — PRD/ARCHITECTURE/QA/DESIGN 기준 질문지를 만들고 init task JSON을 남김
  - 채팅에서는 질문표 전체를 한 번에 던지지 않고, 자동 초안을 먼저 반영한 뒤 필요한 것만 순서대로 한 질문씩 확인
- `flow-feature` — 승인된 slice 실행 + 가능하면 TDD
- `flow-qa` — systematic debugging + test-first bugfix 흐름
- `flow-review` — 문서/태스크 기준 리뷰 흐름
- `flow-plan` — thinking + planning + approval
- `/flow-plan` — 구현 없이 계획만 수행

## 핵심 규칙

- docs first
- Explore → Plan → Implement → Verify 순서 유지
- task/plan 문서 없이 구현하지 않음
- feature와 QA를 같은 급의 workflow로 다룸
- 새 동작/버그 수정은 가능하면 test-first로 진행
- bugfix는 root cause 파악 전 추측성 patch 금지
- 구현 완료 뒤 기본 PR 전 루프는 `/simplify` 반복 → convergence `0` → squash다
- GitHub PR 생성/본문 반영/checks watch는 필요할 때만 추가로 사용한다
- scaffold 자체를 수정할 때는 `DESIGN.md`보다 구조/실행 원칙을 먼저 본다
- orchestration은 얇게 유지
- hooks는 `.claude/settings.json`에서 결정론적으로 강제
- 기본 회귀 검증은 `--dry-run`과 자동 테스트로 빠르게 확인하고, live 실행은 명시 opt-in 뒤 실제 runner로 검증한다

## runner 정책

설정 파일은 `.workflow/config/ccs-map.yaml`이다.

- `auto` — `ccs`가 있으면 우선 사용
- role별 `ccs_profile` preflight 실패 시 해당 role만 `claude -p`로 fallback
- fallback 이유는 `fallback_reason`에 기록
- `claude` — 항상 `claude -p`
- role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다.
- `allow_live_run: false` 가 기본값이다. 실실행은 명시적으로 켜기 전까지 막는다.
- `allow_live_run`은 반드시 YAML boolean `true`/`false` 값이어야 한다. 문자열 `"true"`, `"false"` 같은 값은 허용하지 않는다.

`ccs` shortcut 호출 규약

```text
ccs <profile> "prompt"
```

주의
- shortcut 실행에 `-p` 전제 금지
- shortcut 실행에 `--model <same-profile>` 전제 금지
- 기본 확인은 `--dry-run`으로 빠르게 돌리고, 실실행은 `runtime.allow_live_run=true`에서 실제 runner로 검증한다
- `runtime.allow_live_run`은 YAML boolean `true` / `false` 여야 한다

## hooks

`.claude/settings.json`에 들어 있는 guardrail은 설명용 문구가 아니라 실제 hook 연결이다.

- `PreToolUse` + `dangerous-cmd-guard.sh`
  - 위험한 Bash 명령을 치기 전에 가드
  - 예: `rm -rf`, 무차별 삭제/이동 같은 명령 차단
- `PostToolUse` + `validate-output.sh`
  - `flow-*` skill contract를 읽고 완료 직후 필수 섹션/구조를 다시 검사
  - 예: 필수 섹션, verification, 승인 게이트 질문, `Proposed Steps` 개수(3~7), 닫힌 next-step 질문 누락 방지
- `PostToolUse` + `tool-output-truncator.sh`
  - 큰 도구 출력이 나오면 후속 컨텍스트용 요약을 붙이고 에러 라인은 보존
  - 예: 긴 dry-run/grep/bash 출력은 요약본을 추가하고 error/traceback 라인은 유지
- `PostToolUseFailure` + `edit-error-recovery.sh`
  - Edit/Write 실패 패턴별 복구 가이드를 즉시 제공
  - 예: old_string mismatch, ambiguous match, permission 문제 재시도 가이드
- `PostToolUseFailure` + `tool-failure-tracker.sh`
  - 같은 도구 실패가 짧은 시간에 반복되면 전략 전환 유도
  - 예: 같은 patch/edit 실패 3회 이상이면 파일 재읽기나 다른 접근 유도
- `UserPromptSubmit` + `tdd-guard.sh`
  - task 문서/계획 없이 바로 구현으로 튀는 흐름 견제
  - 예: task 문서 없이 바로 구현부터 하려는 프롬프트 견제
- `Stop` + `circuit-breaker.sh`
  - 종료 직전 최소한의 브레이크 포인트 제공
  - 예: 종료 전에 빠진 검증이나 다음 액션 누락 방지

## design 문서 정책

- `DESIGN.md`는 기본적으로 타깃 프로젝트 UI/UX 기준 문서다.
- so2x-flow scaffold 자체를 손볼 때는 이 파일을 억지로 주 참고 문서로 삼지 않는다.
- `.workflow/docs/UI_GUIDE.md`는 legacy fallback이다. 파일이 없으면 무시하면 된다.

## 바로 써보는 문구

아래는 셸 명령이 아니라 Claude Code에 그대로 붙여 넣는 예시다.

```text
flow-plan으로 "결제 기능 작업 분해" 계획 문서를 만들어줘.
이 flow-plan 방향을 승인한다. 다음 slice 진행 준비해줘.
flow-feature로 "결제 기능 1차 slice"를 승인된 방향 기준으로 진행해줘.
이 변경 기준으로 /simplify를 한 번 돌려줘.
convergence가 0이 아니면 /simplify를 다시 반복해줘.
convergence 0이 되면 squash commit 기준으로 정리해줘.
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
- `.workflow/scripts/doctor.py` — read-only latest status surface
- `.workflow/scripts/install.py` — 설치 + 단계 로그 출력
- `.workflow/scripts/patch_claude_md.py` — CLAUDE.md 섹션 패치 스크립트
- `.workflow/scripts/ccs_runner.py` — runner 호환 facade
- `.workflow/scripts/runner_resolution.py` — runner/role fallback 결정
- `.workflow/scripts/runner_commands.py` — ccs/claude command build
- `.workflow/scripts/runner_execution.py` — dry-run/live 실행과 subprocess 오류 처리
- `.workflow/scripts/workflow_contracts.py` — mode별 artifact/roles/output contract 단일 소스
- `tests/` — dry-run 테스트

## artifact naming

- init 결과: `.workflow/tasks/init/<slug>.json`
- feature 결과: `.workflow/tasks/feature/<slug>.json`
- qa 결과: `.workflow/tasks/qa/<slug>.json`
- plan 결과: `.workflow/tasks/plan/<slug>.json`
  - 기본값: `status: draft`, `approved: false`
- review 결과: `.workflow/tasks/review/<slug>.json`
- canonical task 산출물은 계속 `.workflow/tasks/...` 아래에 둔다.
- 실행 결과 payload는 별도로 `.workflow/outputs/<mode>/<slug>.json`에 남긴다.

## 검증

빠른 확인용

```bash
python3 -m pytest tests/test_ccs_runner.py tests/test_execute.py -q
```

docs-first canonical 흐름만 따로 보고 싶으면 smoke test 하나만 찍어도 된다.

```bash
python3 -m pytest tests/test_execute.py -q -k docs_first_smoke_plan_feature_qa_sequence
```

release/handoff 문서 초안은 git diff 기준으로 바로 생성할 수 있다.

```bash
python3 .workflow/scripts/release_handoff.py --base-ref origin/main --head-ref HEAD --pr-number 7 --output-dir .
```

생성한 PR 본문을 현재 PR에 바로 반영하려면 `gh`를 붙이면 된다.

```bash
python3 .workflow/scripts/release_handoff.py --base-ref origin/main --head-ref HEAD --output-dir . --publish-pr-body
```

PR 생성부터 본문 반영, checks watch까지 한 번에 돌리려면 아래처럼 쓰면 된다.

```bash
python3 .workflow/scripts/release_handoff.py \
  --base-ref origin/main \
  --head-ref HEAD \
  --output-dir . \
  --create-pr \
  --draft \
  --base-branch main \
  --watch-checks
```

위 흐름은 내부적으로 `gh pr create`, `gh pr edit`(필요 시), `gh pr checks --watch`에 대응한다.

위 명령은 아래 파일을 만든다.
- `RELEASE_NOTES_PR7.md`
- `RELEASE_BODY_PR7.md`

설치까지 포함한 real-world smoke는 빈 프로젝트 하나를 만들어 직접 install 결과를 보는 방식이 가장 빠르다.
외부 샘플 target repo 기준 e2e smoke는 `tests/test_execute.py::test_external_sample_repo_install_init_plan_e2e_smoke`로 고정돼 있다.

```bash
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/app"
python3 .workflow/scripts/install.py --target "$tmpdir/app" --patch-claude-md
test -f "$tmpdir/app/.claude/skills/flow-init.md"
test -f "$tmpdir/app/.claude/commands/flow-init.md"
test -f "$tmpdir/app/.workflow/scripts/execute.py"
python3 "$tmpdir/app/.workflow/scripts/execute.py" init "샘플 앱 초기 설정" --dry-run
python3 "$tmpdir/app/.workflow/scripts/execute.py" plan "로그인 기능 작업 분해" --dry-run
trap - EXIT
rm -rf "$tmpdir"
```
