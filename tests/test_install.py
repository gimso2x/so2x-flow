import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / ".workflow" / "scripts" / "install.py"


def run_install(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(target), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def test_install_copies_flow_scaffold_into_target_project(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target)
    assert "step 1/4: copy scaffold files" in result.stdout
    assert "step 4/4: install complete" in result.stdout
    assert "next_step: flow-init으로 이 프로젝트를 초기화해줘." in result.stdout
    assert "copied_count:" in result.stdout
    assert (target / ".claude" / "commands" / "flow-init.md").exists()
    assert (target / ".claude" / "skills" / "flow-feature.md").exists()
    assert (target / ".workflow" / "config" / "ccs-map.yaml").exists()
    assert (target / ".workflow" / "docs" / "PRD.md").exists()
    assert (target / ".workflow" / "prompts" / "planner.md").exists()
    assert (target / ".workflow" / "tasks" / "feature" / "_template.json").exists()
    assert (target / ".workflow" / "scripts" / "execute.py").exists()
    assert (target / ".workflow" / "scripts" / "doctor.py").exists()
    assert (target / "DESIGN.md").exists()
    settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert settings["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["type"] == "command"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == ".workflow/scripts/hooks/dangerous-cmd-guard.sh"
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Skill"
    assert settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == ".workflow/scripts/hooks/validate-output.sh"
    assert settings["hooks"]["PostToolUse"][1]["hooks"][0]["command"] == ".workflow/scripts/hooks/tool-output-truncator.sh"
    assert settings["hooks"]["PostToolUseFailure"][0]["matcher"] == "Edit|Write"
    assert settings["hooks"]["PostToolUseFailure"][0]["hooks"][0]["command"] == ".workflow/scripts/hooks/edit-error-recovery.sh"
    assert settings["hooks"]["PostToolUseFailure"][1]["hooks"][0]["command"] == ".workflow/scripts/hooks/tool-failure-tracker.sh"
    assert (target / ".workflow" / "scripts" / "hooks" / "validate-output.sh").exists()
    assert (target / ".workflow" / "scripts" / "hooks" / "tool-output-truncator.sh").exists()
    assert (target / ".workflow" / "scripts" / "hooks" / "edit-error-recovery.sh").exists()
    assert (target / ".workflow" / "scripts" / "hooks" / "tool-failure-tracker.sh").exists()


def test_install_does_not_overwrite_existing_files_without_force(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("keep me\n", encoding="utf-8")
    run_install(target)
    assert existing.read_text(encoding="utf-8") == "keep me\n"


def test_install_force_overwrites_existing_files(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("old\n", encoding="utf-8")
    run_install(target, "--force")
    assert "so2x-flow workspace guide" in existing.read_text(encoding="utf-8")


def test_install_does_not_copy_generated_task_artifacts(tmp_path: Path):
    target = tmp_path / "app"
    run_install(target)
    assert not (target / ".workflow" / "tasks" / "feature" / "로그인-기능-구현.json").exists()
    assert not (target / ".workflow" / "tasks" / "qa" / "qa-001-홈-버튼-클릭-안됨.json").exists()


def test_install_can_patch_existing_claude_md_without_duplicate_section(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    claude_md = target / "CLAUDE.md"
    claude_md.write_text("# local guide\n", encoding="utf-8")

    run_install(target, "--patch-claude-md")
    first = claude_md.read_text(encoding="utf-8")
    assert "## so2x-flow" in first
    assert "존재하지 않으면 이 파일은 무시한다" in first

    run_install(target, "--patch-claude-md")
    second = claude_md.read_text(encoding="utf-8")
    assert second.count("## so2x-flow") == 1


def test_install_rewrites_incomplete_managed_claude_section(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    claude_md = target / "CLAUDE.md"
    claude_md.write_text(
        "# local guide\n\n<!-- so2x-flow:managed:start -->\n## so2x-flow\n- stale\n<!-- so2x-flow:managed:end -->\n",
        encoding="utf-8",
    )

    run_install(target, "--patch-claude-md")
    rewritten = claude_md.read_text(encoding="utf-8")
    assert "- stale" not in rewritten
    assert "<!-- so2x-flow:managed:start -->" in rewritten
    assert "존재하지 않으면 이 파일은 무시한다" in rewritten


def test_readme_uses_exit_trap_cleanup_and_hook_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "trap 'rm -rf .tmp/so2x-flow; rmdir .tmp 2>/dev/null || true' EXIT" in readme
    assert "예: `rm -rf`, 무차별 삭제/이동 같은 명령 차단" in readme
    assert "예: 필수 섹션, verification, 승인 게이트 질문, `Proposed Steps` 개수(3~7), 닫힌 next-step 질문 누락 방지" in readme
    assert "예: 긴 dry-run/grep/bash 출력은 요약본을 추가하고 error/traceback 라인은 유지" in readme
    assert "예: old_string mismatch, ambiguous match, permission 문제 재시도 가이드" in readme
    assert "예: 같은 patch/edit 실패 3회 이상이면 파일 재읽기나 다른 접근 유도" in readme
    assert "예: task 문서 없이 바로 구현부터 하려는 프롬프트 견제" in readme
    assert "예: 종료 전에 빠진 검증이나 다음 액션 누락 방지" in readme


def test_command_and_skill_docs_use_workflow_paths_consistently():
    init_command = (ROOT / ".claude" / "commands" / "flow-init.md").read_text(encoding="utf-8")
    commands_readme = (ROOT / ".claude" / "commands" / "README.md").read_text(encoding="utf-8")
    skills_readme = (ROOT / ".claude" / "skills" / "README.md").read_text(encoding="utf-8")
    feature_command = (ROOT / ".claude" / "commands" / "flow-feature.md").read_text(encoding="utf-8")
    qa_command = (ROOT / ".claude" / "commands" / "flow-qa.md").read_text(encoding="utf-8")
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    plan_command = (ROOT / ".claude" / "commands" / "flow-plan.md").read_text(encoding="utf-8")
    review_command = (ROOT / ".claude" / "commands" / "flow-review.md").read_text(encoding="utf-8")
    assert "`.workflow/tasks/init/<slug>.json`" in init_command
    assert "skill만 있어도 workflow 정의는 성립하고" in commands_readme
    assert "Optional slash commands, if added later, should only be thin wrappers" in skills_readme
    assert "핵심 실사용 루프도 skill 기준으로 본다." in skills_readme
    assert "- `/simplify` 반복" in skills_readme
    assert "`/simplify`는 별도 `flow-*` skill이 아니라, 보통 `flow-feature` 완료 뒤 또는 승인된 plan 기준 구현이 끝난 뒤에 도는 마감 루프다." in skills_readme
    assert "PRD/ARCHITECTURE/QA/DESIGN에 매핑된 질문 목록" in init_command
    assert "초안으로 채울 수 있는 값은 먼저 반영하고" in init_command
    assert "`.workflow/tasks/init/<slug>.json` canonical init artifact" in init_skill
    assert "질문 없이 PRD/ARCHITECTURE/DESIGN 내용을 지어내기 금지" in init_skill
    assert "질문은 항상 한 번에 하나씩만 한다" in init_skill
    assert "가능한 값은 먼저 자동으로 채운다" in init_skill
    assert "작업 진행 후 자동 채우기" in init_skill
    assert "다음 질문으로 넘어간다" in init_skill
    assert "`.workflow/tasks/feature/<slug>.json`" in feature_command
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_command
    assert "`.workflow/tasks/review/<slug>.json`" in review_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in feature_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in qa_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in review_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in plan_command
    assert "승인된 방향이 없으면 바로 구현으로 밀지 않는다" in feature_skill
    assert "## Position in real workflow" in feature_skill
    assert "실사용 기본 루프는 보통 `flow-plan` → `flow-feature` → `/simplify` 반복 → convergence `0` → squash 순서다." in feature_skill
    assert "## Input" in feature_skill
    assert "## Output contract" in feature_skill
    assert "## Forbidden" in feature_skill
    assert "validate_prompt:" in feature_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in feature_skill
    assert "구현/테스트가 끝난 뒤 기본 마감 루프는 `/simplify` 반복 → convergence `0` → squash다" in feature_skill
    assert "`/simplify`는 가능하면 현재 diff / 현재 slice 범위로만 돌린다" in feature_skill
    assert "매회 `/simplify`는 최대 2~3개 개선만 처리하고, convergence 요약은 짧게 남긴다" in feature_skill
    assert "convergence가 `0`이면 바로 종료하고 squash한다" in feature_skill
    assert "convergence가 작더라도 반복은 보통 2~3회를 넘기지 않는다" in feature_skill
    assert "`flow-review`, `flow-qa`는 필요할 때만 추가하고, GitHub PR 운영은 선택 사항이다" in feature_skill
    assert "## Input" in qa_skill
    assert "## Outputs" in qa_skill
    assert "## Forbidden" in qa_skill
    assert "validate_prompt:" in qa_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in qa_skill
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")
    assert "validate_prompt:" in init_skill
    assert "validate_prompt:" in review_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in review_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in plan_skill
    assert "validate_prompt:" in plan_skill
    assert "## Position in real workflow" in plan_skill
    assert "실사용 기본 루프는 보통 `flow-plan` → `flow-feature` → `/simplify` 반복 → convergence `0` → squash 순서다." in plan_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "중복 산출물을 만들지 않고 `.workflow/tasks/plan/<slug>.json` 하나만 남긴다" in plan_command
    assert "`/flow-plan`은 markdown 계획 문서를 만들지 않는다." in plan_skill
    assert "승인 전에는 /flow-feature로 자동 전환하지 않는다" in plan_skill
    assert "이 설계 방향으로 확정할까요? (y/n)" in plan_command


def test_readme_documents_init_install_split_and_artifact_naming():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## init vs install" in readme
    assert "설치와 운영 초기화는 분리돼 있다" in readme
    assert "## artifact naming" in readme
    assert "canonical task 산출물은 계속 `.workflow/tasks/...` 아래에 둔다." in readme
    assert "실행 결과 payload는 별도로 `.workflow/outputs/<mode>/<slug>.json`에 남긴다." in readme
    assert "- init 결과: `.workflow/tasks/init/<slug>.json`" in readme
    assert "- `flow-init` — PRD/ARCHITECTURE/QA/DESIGN 기준 질문지를 만들고 init task JSON을 남김" in readme
    assert "`--skip-plan`에 쓰려면 `approved: true` 또는 `status: approved`로 명시 승인되어 있어야 한다" in readme
    assert "- `/flow-plan` — 구현 없이 계획만 수행" in readme
    assert "- `flow-review` — 문서/태스크 기준 리뷰 흐름" in readme
    assert "이미 설치된 scaffold를 바탕으로 init 질문지를 만드는 운영 단계" in readme
    assert "`/flow-plan`은 `.workflow/tasks/plan/*.json` 하나를 canonical 계획 산출물로 남기는 docs-first 흐름이다." in readme
    assert '`allow_live_run`은 반드시 YAML boolean `true`/`false` 값이어야 한다' in readme
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in readme
    assert '/flow-plan으로 "결제 기능 작업 분해" 계획 산출물을 만들어줘.' in readme


def test_flow_init_skill_documents_strict_boolean_live_run_policy():
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    assert "live 실행은 `runtime.allow_live_run=true`일 때만 허용" in init_skill
    assert "문자열 `\"true\"` 같은 값은 허용하지 않는다" in init_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in init_skill


def test_flow_init_docs_require_one_question_at_a_time_followup():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    init_command = (ROOT / ".claude" / "commands" / "flow-init.md").read_text(encoding="utf-8")
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")

    assert "`flow-init`은 시작할 때 초기화 방식을 하나 고르게 하고, 기본은 repo와 최근 요청을 바탕으로 초안을 먼저 채운다." in readme
    assert "작업 진행 후 자동 채우기" in init_command
    assert "초안으로 채울 수 있는 값은 먼저 반영하고" in init_command
    assert "질문은 항상 한 번에 하나씩만 한다." in init_skill
    assert "가능한 값은 먼저 자동으로 채운다." in init_skill
    assert "사용자가 답하면 init artifact의 `answers`에 반영한 뒤 다음 질문으로 넘어간다." in init_skill


def test_readme_install_prompt_forces_single_turn_completion_without_recap_only():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "1~5단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해" in readme
    assert 'recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고' in readme
    assert '문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써' in readme


def test_install_output_and_readme_show_one_obvious_next_action():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "## 실사용 기본 경로" in readme
    assert "실제로는 아래 순서로 보면 된다." in readme
    assert "`/simplify`는 별도 `flow-*` workflow가 아니라, `flow-feature` 완료 뒤나 승인된 plan 기준 구현이 끝난 뒤에 붙는 마감 루프다." in readme
    assert "1. 필요하면 `/flow-plan`으로 방향과 slice를 먼저 고정한다." in readme
    assert "2. `/flow-feature`로 구현과 테스트를 끝낸다." in readme
    assert "3. `/simplify`를 반복한다." in readme
    assert "4. convergence가 `0`이 될 때까지 다시 `/simplify`를 돈다." in readme
    assert "5. convergence `0`이 되면 squash commit으로 정리한다." in readme
    assert "6. 필요하면 `flow-review`, `flow-qa`를 추가한다." in readme
    assert "7. GitHub PR 생성/본문 반영/checks watch는 필요할 때만 붙인다." in readme
    assert "next_step: flow-init으로 이 프로젝트를 초기화해줘." in install_script
    assert "next_step_cli: /flow-init" in install_script
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in install_script


def test_install_output_contract_includes_first_run_guidance_lines(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target, "--patch-claude-md")

    assert "next_step: flow-init으로 이 프로젝트를 초기화해줘." in result.stdout
    assert "next_step_cli: /flow-init" in result.stdout
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in result.stdout
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in result.stdout



def test_readme_first_run_guidance_stays_project_local_and_scan_friendly():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "전역 `~/.claude/skills` 설치가 아니라 현재 프로젝트 내부 설치" in readme
    assert "## 처음 3단계" in readme
    assert "1. `/flow-init`으로 PRD/ARCHITECTURE/QA/DESIGN 질문지를 만든다." in readme
    assert "2. 요구사항이 아직 크거나 애매하면 `/flow-plan`부터 돌린다." in readme
    assert "3. 승인된 plan이 생긴 뒤에만 `/flow-feature`로 들어간다." in readme
    assert "마지막 한 줄 안내는 항상 이걸 기준으로 보면 된다." in readme
    assert "- 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme


def test_readme_and_claude_document_doctor_status_surface():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "doctor/status surface" in readme
    assert "python3 .workflow/scripts/doctor.py --brief" in readme
    assert "python3 .workflow/scripts/execute.py doctor" in readme
    assert "`.workflow/outputs/doctor/status.json`" in readme
    assert "doctor.py --brief" in claude
    assert "execute.py doctor" in claude


def test_readme_documents_smoke_test_entrypoint():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs-first canonical 흐름만 따로 보고 싶으면 smoke test 하나만 찍어도 된다." in readme
    assert "python3 -m pytest tests/test_execute.py -q -k docs_first_smoke_plan_feature_qa_sequence" in readme
    assert "release/handoff 문서 초안은 git diff 기준으로 바로 생성할 수 있다." in readme
    assert "python3 .workflow/scripts/release_handoff.py --base-ref origin/main --head-ref HEAD --pr-number 7 --output-dir ." in readme
    assert "생성한 PR 본문을 현재 PR에 바로 반영하려면 `gh`를 붙이면 된다." in readme
    assert "python3 .workflow/scripts/release_handoff.py --base-ref origin/main --head-ref HEAD --output-dir . --publish-pr-body" in readme
    assert "PR 생성부터 본문 반영, checks watch까지 한 번에 돌리려면 아래처럼 쓰면 된다." in readme
    assert "--create-pr" in readme
    assert "--watch-checks" in readme
    assert "`gh pr create`, `gh pr edit`(필요 시), `gh pr checks --watch`에 대응한다." in readme
    assert "RELEASE_NOTES_PR7.md" in readme
    assert "RELEASE_BODY_PR7.md" in readme
    assert "설치까지 포함한 real-world smoke는 빈 프로젝트 하나를 만들어 직접 install 결과를 보는 방식이 가장 빠르다." in readme
    assert "외부 샘플 target repo 기준 e2e smoke는 `tests/test_execute.py::test_external_sample_repo_install_init_plan_e2e_smoke`로 고정돼 있다." in readme
    assert 'tmpdir="$(mktemp -d)"' in readme
    assert 'python3 .workflow/scripts/install.py --target "$tmpdir/app" --patch-claude-md' in readme
    assert 'python3 "$tmpdir/app/.workflow/scripts/execute.py" init "샘플 앱 초기 설정" --dry-run' in readme
    assert 'python3 "$tmpdir/app/.workflow/scripts/execute.py" plan "로그인 기능 작업 분해" --dry-run' in readme



def test_core_workflow_contracts_are_consistent_across_readme_claude_and_flow_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    feature_command = (ROOT / ".claude" / "commands" / "flow-feature.md").read_text(encoding="utf-8")
    plan_command = (ROOT / ".claude" / "commands" / "flow-plan.md").read_text(encoding="utf-8")
    qa_command = (ROOT / ".claude" / "commands" / "flow-qa.md").read_text(encoding="utf-8")
    review_command = (ROOT / ".claude" / "commands" / "flow-review.md").read_text(encoding="utf-8")
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")

    shared_contracts = [
        "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback",
        "승인된 plan이 없으면",
        ".workflow/tasks/plan/<slug>.json",
    ]
    for contract in shared_contracts:
        assert contract in readme
        assert contract in claude

    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-qa -> GitHub PR 운영은 옵션" in readme
    assert "GitHub PR 생성/본문 반영/checks watch는 필요할 때만 추가로 사용한다" in readme
    assert "이 변경 기준으로 /simplify를 한 번 돌려줘." in readme
    assert "convergence가 0이 아니면 /simplify를 다시 반복해줘." in readme
    assert "convergence 0이 되면 squash commit 기준으로 정리해줘." in readme
    assert "create `.workflow/tasks/qa/<slug>.json` first, then execute when QA work is needed" in claude
    assert "review against workflow docs and task artifacts when review is needed" in claude
    assert "`/simplify` is not a separate `flow-*` workflow; it is the default finish loop after `flow-feature` or after implementation based on an approved plan." in claude
    assert "승인된 plan이 없으면 여기서 멈추고 `flow-plan`으로 먼저 범위를 확정할지 묻는다" in feature_command
    assert "승인된 plan이 없으면 여기서 멈추고 `flow-plan` 선행 여부를 먼저 묻는다" in feature_skill
    assert "`/simplify`는 별도 `flow-*` workflow가 아니라 `flow-feature` 뒤에 붙는 기본 마감 루프다" in feature_skill
    assert "승인 전에는 `/flow-feature`로 자동 전환" in plan_skill
    assert "이 단계는 구현을 직접 하지 않고, 이후 `/simplify` 반복 루프로 갈 수 있게 slice와 검증 기준을 고정한다" in plan_skill
    assert "기본 downstream 마감 루프는 `flow-feature` 이후 `/simplify` 반복 → convergence `0` → squash다" in plan_skill
    assert "`/simplify`는 별도 `flow-*` workflow가 아니라 승인된 plan 기준 구현이 끝난 뒤 붙는 마감 루프다" in plan_skill
    assert "승인 전에는 `/flow-feature`로 자동 전환" in plan_command
    assert "설치와 운영 초기화는 분리돼 있다" in readme
    assert "Use `.claude/settings.json` hooks as deterministic guardrails" in claude

    assert "`.workflow/tasks/feature/<slug>.json`" in feature_command
    assert "planner -> implementer 흐름 결과 또는 dry-run 요약" in feature_command
    assert "마지막은 즉답 가능한 닫힌 질문으로 끝낸다." in feature_command
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_command
    assert "qa-planner -> implementer 흐름 결과 또는 dry-run 요약" in qa_command
    assert "가능하면 root cause hypothesis / minimal fix / verification이 함께 보여야 한다" in qa_command
    assert "가능하면 `test-driven-development`를 따라 failing reproduction/test를 먼저 만들고 fix 후 회귀 검증까지 끝낸다." in qa_skill
    assert "`.workflow/tasks/review/<slug>.json`" in review_command
    assert "review 결과 또는 dry-run 요약" in review_command
    assert "막연한 칭찬보다 blocking issue를 먼저 적는다." in review_command
    assert "`flow-review`는 칭찬문이 아니라 independent verification 단계다." in review_skill
    assert "plan은 중복 산출물을 만들지 않고 `.workflow/tasks/plan/<slug>.json` 하나만 남긴다." in plan_command
    assert "`/flow-plan` dry-run도 canonical 계획 산출물 `.workflow/tasks/plan/<slug>.json`을 만든다." in plan_command


def test_readme_positions_current_repo_as_v1_ready():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "so2x-flow는 Claude Code에서 기능 구현, QA, 리뷰, 계획 작업을 문서 중심으로 굴리는 얇은 워크플로우 하네스다." in readme
    assert "기본 회귀 검증은 `--dry-run`과 자동 테스트로 빠르게 확인하고, live 실행은 명시 opt-in 뒤 실제 runner로 검증한다" in readme
    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-qa -> GitHub PR 운영은 옵션" in readme


def test_command_docs_lock_runtime_and_artifact_wrapper_contracts():
    feature_command = (ROOT / ".claude" / "commands" / "flow-feature.md").read_text(encoding="utf-8")
    plan_command = (ROOT / ".claude" / "commands" / "flow-plan.md").read_text(encoding="utf-8")
    qa_command = (ROOT / ".claude" / "commands" / "flow-qa.md").read_text(encoding="utf-8")
    review_command = (ROOT / ".claude" / "commands" / "flow-review.md").read_text(encoding="utf-8")

    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in feature_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in plan_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in qa_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in review_command

    assert "`.workflow/tasks/feature/<slug>.json`" in feature_command
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_command
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_command
    assert "`.workflow/tasks/review/<slug>.json`" in review_command
