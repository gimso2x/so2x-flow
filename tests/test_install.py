import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / ".workflow" / "scripts" / "install.py"


def _read_patch_claude_md() -> str:
    return (ROOT / ".workflow" / "scripts" / "patch_claude_md.py").read_text(encoding="utf-8")


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
    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in result.stdout
    assert "copied_count:" in result.stdout
    assert "skipped_existing_count:" in result.stdout
    assert "skipped_missing_count:" in result.stdout
    assert "claude_md_status: not created (rerun with --patch-claude-md to create/update)" in result.stdout
    assert "copied_files: hidden (rerun with --verbose-copied-files to inspect each path)" in result.stdout
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


def test_install_verbose_flag_prints_each_copied_path(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target, "--verbose-copied-files")
    assert "copied_files:" in result.stdout
    assert ".workflow/scripts/execute.py" in result.stdout
    assert ".claude/skills/flow-init.md" in result.stdout


def test_install_does_not_overwrite_existing_files_without_force(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("keep me\n", encoding="utf-8")
    result = run_install(target)
    assert existing.read_text(encoding="utf-8") == "keep me\n"
    assert "skipped_existing_count:" in result.stdout


def test_install_reports_claude_md_created_when_patch_enabled(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target, "--patch-claude-md")
    assert "claude_md_status: created_or_updated" in result.stdout


def test_install_force_overwrites_existing_scaffold_file(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir(parents=True)
    existing = target / ".workflow" / "docs" / "PRD.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old\n", encoding="utf-8")

    run_install(target, "--force")

    assert existing.read_text(encoding="utf-8") != "old\n"
    assert "# PRD" in existing.read_text(encoding="utf-8")


def test_install_patch_creates_claude_md_when_missing(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target, "--patch-claude-md")

    claude_md = target / "CLAUDE.md"
    assert claude_md.exists()
    assert "claude_md_patched: True" in result.stdout
    assert "## so2x-flow" in claude_md.read_text(encoding="utf-8")


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


def test_readme_uses_exit_trap_cleanup_and_install_checks():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "### 30초 설치 체크표" in readme
    assert "trap 'rm -rf .tmp/so2x-flow; rmdir .tmp 2>/dev/null || true' EXIT" in readme
    assert "test -f CLAUDE.md" in readme
    assert 'grep -n "## so2x-flow" CLAUDE.md' in readme
    assert 'grep -n "<!-- so2x-flow:managed:start -->" CLAUDE.md' in readme
    assert "`python3 .workflow/scripts/doctor.py --brief`" in readme
    assert "기본 성공 판단은 **step 로그 + 필수 파일 4개 확인**으로 먼저 닫는다." in readme
    assert "`copied_files: hidden (rerun with --verbose-copied-files to inspect each path)`는 기본 출력이 요약 모드라는 뜻이다." in readme
    assert "성공 경로에서는 `trap - EXIT`를 cleanup 직전에 호출해 자동 EXIT cleanup을 해제한 뒤" in readme
    assert "이 옵션은 이미 로컬 `CLAUDE.md`가 있는 프로젝트에서 기존 사용자 가이드와 so2x-flow 섹션을 한 파일로 합칠 때 특히 의미가 크다." in readme
    assert "`CLAUDE.md`가 아예 없는 새 프로젝트라면 install이 scaffold 기본 파일을 복사하는 대신 patch 단계에서 새 `CLAUDE.md`를 만들어 managed so2x-flow 섹션을 넣는다." in readme


def test_skill_docs_use_workflow_paths_consistently():
    skills_readme = (ROOT / ".claude" / "skills" / "README.md").read_text(encoding="utf-8")
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")

    assert "workflow source of truth" in skills_readme
    assert "핵심 실사용 루프도 skill 기준으로 본다." in skills_readme
    assert "- `/simplify` 반복" in skills_readme
    assert "`/simplify`는 별도 `flow-*` skill이 아니라, 보통 `flow-feature` 완료 뒤 또는 승인된 plan 기준 구현이 끝난 뒤에 도는 마감 루프다." in skills_readme
    assert "`.workflow/tasks/init/<slug>.json` canonical init artifact" in init_skill
    assert "질문 없이 PRD/ARCHITECTURE/DESIGN 내용을 지어내기 금지" in init_skill
    assert "질문은 항상 한 번에 하나씩만 한다" in init_skill
    assert "가능한 값은 먼저 자동으로 채운다" in init_skill
    assert "다음 질문으로 넘어간다" in init_skill
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
    assert "`flow-review`, `flow-fix`(`flow-qa` alias)는 필요할 때만 추가하고, GitHub PR 운영은 선택 사항이다" in feature_skill
    assert "## Input" in qa_skill
    assert "## Outputs" in qa_skill
    assert "## Forbidden" in qa_skill
    assert "validate_prompt:" in qa_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in qa_skill
    assert "validate_prompt:" in init_skill
    assert "validate_prompt:" in review_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in review_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in plan_skill
    assert "validate_prompt:" in plan_skill
    assert "## Position in real workflow" in plan_skill
    assert "실사용 기본 루프는 보통 `flow-plan` → `flow-feature` → `/simplify` 반복 → convergence `0` → squash 순서다." in plan_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "`/flow-plan`은 markdown 계획 문서를 만들지 않는다." in plan_skill
    assert "승인 전에는 /flow-feature로 자동 전환하지 않는다" in plan_skill


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
    assert "role별 `ccs.command` 또는 `command`로 커스텀 ccs 래퍼를 지정했다면" in readme
    assert '/flow-plan으로 "결제 기능 작업 분해" 계획 산출물을 만들어줘.' in readme


def test_flow_init_skill_documents_strict_boolean_live_run_policy():
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")
    assert "live 실행은 `runtime.allow_live_run=true`일 때만 허용" in init_skill
    assert "문자열 `\"true\"` 같은 값은 허용하지 않는다" in init_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in init_skill


def test_flow_init_docs_require_one_question_at_a_time_followup():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    init_skill = (ROOT / ".claude" / "skills" / "flow-init.md").read_text(encoding="utf-8")

    assert "`flow-init`은 시작할 때 먼저 `1. 자동채우기`, `2. 질문` 중 하나를 고르게 한다." in readme
    assert "질문은 항상 한 번에 하나씩만 한다." in init_skill
    assert "가능한 값은 먼저 자동으로 채운다." in init_skill
    assert "사용자가 답하면 init artifact의 `answers`에 반영한 뒤 다음 질문으로 넘어간다." in init_skill


def test_readme_install_prompt_stays_single_turn_and_project_local():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "전역 `~/.claude/skills` 설치가 아니라 현재 프로젝트 내부 설치" in readme
    assert "중간 단계 성공만 보고하고 응답을 끝내지 말고, 아래 작업을 한 턴에서 끝까지 실제로 실행해." in readme
    assert "install 출력 tail(`next_step`, `next_step_cli`, `next_step_human`, `first_run_path`, `target`, `copied_count`, `skipped_existing_count`, `skipped_missing_count`, `claude_md_status`, `copied_files`)" in readme
    assert "필요하면 선택적으로 `python3 .workflow/scripts/doctor.py --brief`" in readme
    assert "마지막 한 줄은 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 끝내." in readme
    assert "기본 성공 판단은 **step 로그 + 필수 파일 4개 확인**으로 먼저 닫는다." in readme


def test_readme_install_examples_match_installer_required_file_contract():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")

    assert '".workflow/scripts/doctor.py",' in install_script
    assert "`.workflow/scripts/doctor.py`" in readme
    assert 'test -f .workflow/scripts/doctor.py' in readme
    assert "### 30초 설치 체크표" in readme
    assert "| 필수 파일 4개 |" in readme
    assert "| 마지막 안내 | `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` |" in readme


def test_install_output_and_readme_show_one_obvious_next_action():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "### install 출력에서 바로 보는 키" in readme
    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "next_step_cli: /flow-init" in readme
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in readme
    assert "## 실사용 기본 경로" in readme
    assert "실제로는 아래 순서로 보면 된다." in readme
    assert "1. 필요하면 `/flow-plan`으로 방향과 slice를 먼저 고정한다." in readme
    assert "2. `/flow-feature`로 구현과 테스트를 끝낸다." in readme
    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "next_step_cli: /flow-init" in install_script
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in install_script
    assert "target:" in readme
    assert "copied_count:" in readme
    assert "skipped_existing_count:" in readme
    assert "skipped_missing_count:" in readme
    assert "claude_md_status:" in readme
    assert "copied_files: hidden (rerun with --verbose-copied-files to inspect each path)" in readme


def test_install_output_contract_includes_first_run_guidance_lines(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target, "--patch-claude-md")

    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in result.stdout
    assert "next_step_cli: /flow-init" in result.stdout
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in result.stdout
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in result.stdout
    assert (target / ".claude" / "skills" / "flow-init.md").exists()
    assert (target / ".workflow" / "scripts" / "execute.py").exists()
    assert (target / ".workflow" / "scripts" / "doctor.py").exists()
    assert (target / ".workflow" / "config" / "ccs-map.yaml").exists()
    assert (target / "CLAUDE.md").exists()
    assert "claude_md_status: created_or_updated" in result.stdout



def test_readme_first_run_guidance_stays_project_local_and_scan_friendly():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "전역 `~/.claude/skills` 설치가 아니라 현재 프로젝트 내부 설치" in readme
    assert "## 처음 3단계" in readme
    assert "1. `/flow-init`으로 PRD/ARCHITECTURE/QA/DESIGN 질문지를 만든다." in readme
    assert "2. 요구사항이 아직 크거나 애매하면 `/flow-plan`부터 돌린다." in readme
    assert "3. 승인된 plan이 생긴 뒤에만 `/flow-feature`로 들어간다." in readme
    assert "마지막 한 줄 안내는 항상 이걸 기준으로 보면 된다." in readme
    assert "- 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme


def test_readme_and_patch_claude_md_document_doctor_status_surface():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    patch_claude = _read_patch_claude_md()

    assert "doctor/status surface" in readme
    assert "python3 .workflow/scripts/doctor.py --brief" in readme
    assert "python3 .workflow/scripts/execute.py doctor" in readme
    assert "`.workflow/outputs/doctor/status.json`" in readme
    assert "doctor.py --brief" not in patch_claude
    assert "execute.py doctor" not in patch_claude


def test_readme_and_patch_claude_md_align_on_flow_qa_task_artifact_gate():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    patch_claude = _read_patch_claude_md()

    assert "먼저 `.workflow/tasks/qa/<slug>.json` 이슈 문서를 만든 뒤 실행한다" in readme
    assert "구현 전에 항상 `.workflow/tasks` 아래 task 문서를 먼저 만든다." in patch_claude


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
    assert "--verbose-copied-files" in readme
    assert 'python3 "$tmpdir/app/.workflow/scripts/execute.py" init "샘플 앱 초기 설정" --dry-run' in readme
    assert 'python3 "$tmpdir/app/.workflow/scripts/execute.py" plan "로그인 기능 작업 분해" --dry-run' in readme



def test_core_workflow_contracts_are_consistent_across_readme_patch_claude_and_flow_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    patch_claude = _read_patch_claude_md()
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")
    evaluate_skill = (ROOT / ".claude" / "skills" / "flow-evaluate.md").read_text(encoding="utf-8")

    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in readme
    assert "runner 선택은 `.workflow/config/ccs-map.yaml`을 따른다. `auto`면 `ccs`가 있으면 `ccs`, 없으면 `claude -p`를 사용한다." in patch_claude
    assert "승인된 plan이 없으면" in readme
    assert ".workflow/tasks/plan/<slug>.json" in readme

    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-fix(flow-qa alias) -> GitHub PR 운영은 옵션" in readme
    assert "GitHub PR 생성/본문 반영/checks watch는 필요할 때만 추가로 사용한다" in readme
    assert "이 변경 기준으로 /simplify를 한 번 돌려줘." in readme
    assert "convergence가 0이 아니면 /simplify를 다시 반복해줘." in readme
    assert "convergence 0이 되면 squash commit 기준으로 정리해줘." in readme
    assert "구현 전에 항상 `.workflow/tasks` 아래 task 문서를 먼저 만든다." in patch_claude
    assert "docs-first 실행에는 현재 프로젝트의 `.claude/skills` 아래 `flow-init`, `flow-feature`, `flow-fix`(=`flow-qa`), `flow-review`, `flow-evaluate`, `flow-plan`을 사용한다." in patch_claude
    assert "승인된 plan이 없으면 여기서 멈추고 `flow-plan` 선행 여부를 먼저 묻는다" in feature_skill
    assert "`/simplify`는 별도 `flow-*` workflow가 아니라 `flow-feature` 뒤에 붙는 기본 마감 루프다" in feature_skill
    assert "승인 전에는 `/flow-feature`로 자동 전환" in plan_skill
    assert "이 단계는 구현을 직접 하지 않고, 이후 `/simplify` 반복 루프로 갈 수 있게 slice와 검증 기준을 고정한다" in plan_skill
    assert "기본 downstream 마감 루프는 `flow-feature` 이후 `/simplify` 반복 → convergence `0` → squash다" in plan_skill
    assert "`/simplify`는 별도 `flow-*` workflow가 아니라 승인된 plan 기준 구현이 끝난 뒤 붙는 마감 루프다" in plan_skill
    assert "설치와 운영 초기화는 분리돼 있다" in readme
    assert "`.claude/settings.json`에 들어 있는 guardrail은 설명용 문구가 아니라 실제 hook 연결이다." in readme

    assert "`.workflow/tasks/feature/<slug>.json`" in feature_skill
    assert "`Proposed Steps`를 planner가 구체화한다" in feature_skill
    assert "implementer는 planner 결과만 따라 최소 범위로 실행한다" in feature_skill
    assert "닫힌 질문으로 끝낸다" in feature_skill
    assert "## Input" in qa_skill
    assert "## Outputs" in qa_skill
    assert "reproduction / expected / actual / root cause hypothesis / minimal fix를 명시한다" in qa_skill
    assert "가능하면 `test-driven-development`를 따라 failing reproduction/test를 먼저 만들고 fix 후 회귀 검증까지 끝낸다." in qa_skill
    assert "`.workflow/tasks/review/<slug>.json`" in review_skill
    assert "Mechanical Status" in evaluate_skill
    assert "Semantic Status" in evaluate_skill
    assert "Release Readiness" in evaluate_skill
    assert "Regression Risks" in evaluate_skill
    assert "Recommended Next Step" in evaluate_skill
    assert "`.workflow/tasks/evaluate/<slug>.json`" in evaluate_skill
    assert "## Outputs" in review_skill
    assert "Code Reuse Review" in review_skill
    assert "Code Quality Review" in review_skill
    assert "Efficiency Review" in review_skill
    assert "actionable finding 위주로 쓴다" in review_skill
    assert "`flow-review`는 칭찬문이 아니라 independent verification 단계다." in review_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "canonical 계획 산출물은 `.workflow/tasks/plan/` 아래 JSON으로 남긴다" in plan_skill


def test_readme_positions_current_repo_as_v1_ready():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "so2x-flow는 Claude Code에서 기능 구현, QA, 리뷰, 계획 작업을 문서 중심으로 굴리는 얇은 워크플로우 하네스다." in readme
    assert "기본 회귀 검증은 `--dry-run`과 자동 테스트로 빠르게 확인하고, live 실행은 명시 opt-in 뒤 실제 runner로 검증한다" in readme
    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-fix(flow-qa alias) -> GitHub PR 운영은 옵션" in readme


def test_readme_documents_absorbed_role_contract_and_review_lenses():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Code Reuse Review / Code Quality Review / Efficiency Review를 명시적으로 남기고 싶다" in readme
    assert "release/readiness gate만 보고 싶다 → `flow-evaluate`" in readme
    assert "먼저 `.workflow/tasks/evaluate/<slug>.json` readiness task를 만든 뒤 실행한다" in readme
    assert "## 역할 계약과 handoff" in readme
    assert "| planner | plan, feature | request, docs bundle, approved plan context, feature task | 방향 고정, `Proposed Steps`, verification gate | implementer |" in readme
    assert "review는 `Code Reuse Review`, `Code Quality Review`, `Efficiency Review` 세 렌즈를 항상 드러낸다." in readme


def test_readme_documents_evaluate_and_doctor_surface():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "`flow-evaluate` — 구현 후 mechanical/semantic readiness 점검 흐름" in readme
    assert "doctor는 이제 `init/plan/feature/qa/review/evaluate/doctor` 최신 산출물을 함께 본다." in readme
    assert "evaluate 결과: `.workflow/tasks/evaluate/<slug>.json`" in readme


def test_skill_docs_lock_runtime_and_artifact_contracts():
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")
    evaluate_skill = (ROOT / ".claude" / "skills" / "flow-evaluate.md").read_text(encoding="utf-8")

    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in feature_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in plan_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in qa_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in review_skill
    assert "reviewer가 단독으로 readiness gate를 남긴다" in evaluate_skill

    assert "`.workflow/tasks/feature/<slug>.json`" in feature_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_skill
    assert "`.workflow/tasks/review/<slug>.json`" in review_skill
    assert "`.workflow/tasks/evaluate/<slug>.json`" in evaluate_skill
