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
    assert (target / "DESIGN.md").exists()
    settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert settings["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["type"] == "command"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == ".workflow/scripts/hooks/dangerous-cmd-guard.sh"


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
    assert "예: task 문서 없이 바로 구현부터 하려는 프롬프트 견제" in readme
    assert "예: 종료 전에 빠진 검증이나 다음 액션 누락 방지" in readme


def test_command_and_skill_docs_use_workflow_paths_consistently():
    init_command = (ROOT / ".claude" / "commands" / "flow-init.md").read_text(encoding="utf-8")
    feature_command = (ROOT / ".claude" / "commands" / "flow-feature.md").read_text(encoding="utf-8")
    qa_command = (ROOT / ".claude" / "commands" / "flow-qa.md").read_text(encoding="utf-8")
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    plan_command = (ROOT / ".claude" / "commands" / "flow-plan.md").read_text(encoding="utf-8")
    review_command = (ROOT / ".claude" / "commands" / "flow-review.md").read_text(encoding="utf-8")
    assert "`.workflow/tasks/init/<slug>.json`" in init_command
    assert "PRD/ARCHITECTURE/QA/DESIGN에 매핑된 질문 목록" in init_command
    assert "`.workflow/tasks/init/<slug>.json` canonical init artifact" in init_skill
    assert "질문 없이 PRD/ARCHITECTURE/DESIGN 내용을 지어내기 금지" in init_skill
    assert "`.workflow/tasks/feature/<slug>.json`" in feature_command
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_command
    assert "`.workflow/tasks/review/<slug>.json`" in review_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in feature_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in qa_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in review_command
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in plan_command
    assert "승인된 방향이 없으면 바로 구현으로 밀지 않는다" in feature_skill
    assert "## Input" in feature_skill
    assert "## Output contract" in feature_skill
    assert "## Forbidden" in feature_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in feature_skill
    assert "## Input" in qa_skill
    assert "## Outputs" in qa_skill
    assert "## Forbidden" in qa_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in qa_skill
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in review_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in plan_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "중복 산출물을 만들지 않고 `.workflow/tasks/plan/<slug>.json` 하나만 남긴다" in plan_command
    assert "현재 v0 `/flow-plan`은 markdown 계획 문서를 만들지 않는다." in plan_skill
    assert "승인 전에는 /flow-feature로 자동 전환하지 않는다" in plan_skill
    assert "이 설계 방향으로 확정할까요? (y/n)" in plan_command


def test_readme_documents_init_install_split_and_artifact_naming():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## init vs install" in readme
    assert "설치와 운영 초기화는 일부러 분리돼 있다" in readme
    assert "## artifact naming" in readme
    assert "run 이력 JSON은 따로 남기지 않는다. 각 task JSON이 canonical 산출물이다." in readme
    assert "- init 결과: `.workflow/tasks/init/<slug>.json`" in readme
    assert "- `flow-init` — PRD/ARCHITECTURE/QA/DESIGN 기준 질문지를 만들고 init task JSON을 남김" in readme
    assert "`--skip-plan`에 쓰려면 `approved: true` 또는 `status: approved`로 명시 승인되어 있어야 한다" in readme
    assert "- `/flow-plan` — 구현 없이 계획만 수행" in readme
    assert "- `flow-review` — 문서와 태스크 기준 리뷰 JSON 생성 후 검토 수행" in readme
    assert "질문 기반 init task를 만들고 dry-run/live 결과를 남기는 운영 단계" in readme
    assert "현재 v0 `/flow-plan`은 `.workflow/tasks/plan/*.json` 하나를 canonical 계획 산출물로 남기는 docs-first 흐름이다." in readme
    assert '`allow_live_run`은 반드시 YAML boolean `true`/`false` 값이어야 한다' in readme
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in readme
    assert '/flow-plan으로 "결제 기능 작업 분해" 계획 산출물을 만들어줘.' in readme


def test_flow_init_skill_documents_strict_boolean_live_run_policy():
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    assert "live 실행은 `runtime.allow_live_run=true`일 때만 허용" in init_skill
    assert "문자열 `\"true\"` 같은 값은 허용하지 않는다" in init_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in init_skill


def test_readme_install_prompt_forces_single_turn_completion_without_recap_only():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "1~5단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해" in readme
    assert 'recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고' in readme
    assert '문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써' in readme


def test_install_output_and_readme_show_one_obvious_next_action():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "처음 3단계" in readme
    assert "1. `/flow-init`으로 PRD/ARCHITECTURE/QA/DESIGN 질문지를 만든다." in readme
    assert "2. 요구사항이 아직 크거나 애매하면 `/flow-plan`부터 돌린다." in readme
    assert "3. 승인된 plan이 생긴 뒤에만 `/flow-feature`로 들어간다." in readme
    assert "next_step: flow-init으로 이 프로젝트를 초기화해줘." in install_script
    assert "next_step_cli: /flow-init" in install_script
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in install_script


def test_readme_documents_smoke_test_entrypoint():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs-first canonical 흐름만 빠르게 보려면 smoke test 하나만 찍어도 된다." in readme
    assert "python3 -m pytest tests/test_execute.py -q -k docs_first_smoke_plan_feature_qa_sequence" in readme



def test_core_workflow_contracts_are_consistent_across_readme_claude_and_flow_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    feature_command = (ROOT / ".claude" / "commands" / "flow-feature.md").read_text(encoding="utf-8")
    plan_command = (ROOT / ".claude" / "commands" / "flow-plan.md").read_text(encoding="utf-8")
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")

    shared_contracts = [
        "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback",
        "승인된 plan이 없으면",
        ".workflow/tasks/plan/<slug>.json",
    ]
    for contract in shared_contracts:
        assert contract in readme
        assert contract in claude

    assert "승인된 plan이 없으면 여기서 멈추고 `flow-plan`으로 먼저 범위를 확정할지 묻는다" in feature_command
    assert "승인된 plan이 없으면 여기서 멈추고 `flow-plan` 선행 여부를 먼저 묻는다" in feature_skill
    assert "승인 전에는 `/flow-feature`로 자동 전환" in plan_skill
    assert "승인 전에는 `/flow-feature`로 자동 전환" in plan_command
    assert "설치와 운영 초기화는 일부러 분리돼 있다" in readme
    assert "Use `.claude/settings.json` hooks as deterministic guardrails" in claude
