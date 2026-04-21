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


def test_install_force_overwrites_existing_files(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("old\n", encoding="utf-8")
    run_install(target, "--force")
    assert existing.read_text(encoding="utf-8") == "old\n"


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


def test_readme_uses_exit_trap_cleanup_and_hook_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "trap 'rm -rf .tmp/so2x-flow; rmdir .tmp 2>/dev/null || true' EXIT" in readme
    assert "test -f CLAUDE.md" in readme
    assert 'grep -n "## so2x-flow" CLAUDE.md' in readme
    assert 'grep -n "<!-- so2x-flow:managed:start -->" CLAUDE.md' in readme
    assert '`grep -n "## so2x-flow"`는 managed 섹션 제목이 실제로 삽입된 위치를 보여주고, `grep -n "<!-- so2x-flow:managed:start -->"`는 install이 이후 재실행 때 같은 관리 블록을 다시 찾아 갱신할 수 있게 표시해 두는 시작 마커까지 보여준다.' in readme
    assert '즉 heading 확인은 "섹션이 들어갔는가"를, managed start marker 확인은 "다음 `--patch-claude-md` 재실행 때 install이 같은 관리 블록을 안전하게 다시 찾을 수 있는가"를 보는 검증이다.' in readme
    assert 'plain `grep -n`은 사람이 managed heading이나 marker가 들어간 위치를 눈으로 확인할 때 더 잘 맞고, `>/dev/null`을 붙인 변형은 셸 스크립트나 CI에서 통과/실패만 빠르게 보려는 검증에 더 잘 맞는다.' in readme
    assert '앞의 `test -f CLAUDE.md`는 grep 에러를 숨기기 위한 장식이 아니라, `--patch-claude-md` 검증을 시작하기 전에 patch 결과가 실제 파일로 생겼는지 먼저 닫는 존재 확인 단계다.' in readme
    assert '즉 사람이 눈으로 위치를 읽는 visible `grep -n` 예시는 `test -f CLAUDE.md`를 별도 줄로 먼저 두는 편이 맞고, quiet `test -f CLAUDE.md && grep ... >/dev/null` 변형은 파일 존재 확인과 pass/fail 검증을 한 줄로 묶고 싶을 때 쓰는 대안이다.' in readme
    assert 'grep 출력 자체를 보고 싶지 않다면 `test -f CLAUDE.md && grep -n "## so2x-flow" CLAUDE.md >/dev/null`처럼 heading 존재만 조용히 통과/실패로 볼 수도 있고, `test -f CLAUDE.md && grep -n "<!-- so2x-flow:managed:start -->" CLAUDE.md >/dev/null`처럼 같은 관리 블록 재탐색 마커도 같은 방식으로 확인할 수 있다.' in readme
    assert '# 개별 복사 경로가 정말 필요할 때만 마지막에 --verbose-copied-files 추가' in readme
    assert '`--verbose-copied-files` 재실행은 개별 복사 경로를 더 자세히 보고 싶을 때만 쓰는 선택 확인 단계이고, 기본 설치 성공 판단은 위 install 출력과 4개 필수 파일 존재 확인으로 먼저 닫는다.' in readme
    assert '일반 셸 경로에서도 `next_step`, `next_step_cli`, `next_step_human`, `first_run_path`, `target`, `copied_count`, `skipped_existing_count`, `skipped_missing_count`, `claude_md_status`, `copied_files`는 같은 install 실행의 출력 tail에 함께 이어지는 성공 요약이므로, `copied_files` summary mode 문장도 그 한 묶음 안에서 읽으면 된다.' in readme
    assert '일반 셸 경로에서도 install 출력의 `copied_files: hidden (rerun with --verbose-copied-files to inspect each path)`는 기본 출력이 요약 모드라는 뜻이지, 출력이 잘리거나 설치가 덜 끝났다는 뜻이 아니다.' in readme
    assert '일반 셸 설치에서도 `python3 .workflow/scripts/doctor.py --brief`는 설치 직후 상태를 더 보고 싶을 때만 붙이는 선택 확인이고, 생략해도 cleanup과 `/flow-init` 진입으로 바로 넘어가면 된다.' in readme
    assert '# 개별 복사 경로가 정말 필요할 때만 마지막에 --verbose-copied-files 추가' in readme
    assert '`--verbose-copied-files` 재실행은 patch 경로에서도 개별 복사 경로를 더 자세히 보고 싶을 때만 쓰는 선택 확인 단계이고, 기본 설치 성공 판단은 `--patch-claude-md` install 출력과 위 필수 파일/`CLAUDE.md` 검증으로 먼저 닫는다.' in readme
    assert 'patch 경로에서도 `next_step`, `next_step_cli`, `next_step_human`, `first_run_path`, `target`, `copied_count`, `skipped_existing_count`, `skipped_missing_count`, `claude_md_status`, `copied_files`는 같은 install 실행의 출력 tail에 함께 이어지는 성공 요약이므로, `copied_files` summary mode 문장도 patch 검증과 같은 맥락에서 읽으면 된다.' in readme
    assert 'patch 경로에서도 install 출력의 `copied_files: hidden (rerun with --verbose-copied-files to inspect each path)`는 기본 출력이 요약 모드라는 뜻이지, patch 적용 검증이 덜 끝났거나 출력이 중간에 잘렸다는 뜻이 아니다.' in readme
    assert '성공 경로에서는 `trap - EXIT`를 cleanup 직전에 호출해 자동 EXIT cleanup을 해제한 뒤 아래 `rm -rf`/`rmdir` 정리를 한 번만 눈에 보이게 수행하므로, 실패 시에는 trap이 임시 디렉터리를 치우고 성공 시에는 사용자가 수동 cleanup이 실제로 끝났는지 바로 확인할 수 있다.' in readme
    assert '여기서도 성공 경로에서는 `trap - EXIT`를 cleanup 직전에 호출해 자동 EXIT cleanup을 해제한 뒤 아래 `rm -rf`/`rmdir` 정리를 한 번만 눈에 보이게 수행하므로, 실패 시에는 trap이 임시 디렉터리를 치우고 성공 시에는 사용자가 patch 검증까지 끝난 뒤 수동 cleanup이 실제로 끝났는지 바로 확인할 수 있다.' in readme
    assert "이 옵션은 이미 로컬 `CLAUDE.md`가 있는 프로젝트에서 기존 사용자 가이드와 so2x-flow 섹션을 한 파일로 합칠 때 특히 의미가 크다." in readme
    assert "`CLAUDE.md`가 아예 없는 새 프로젝트라면 install이 scaffold 기본 파일을 복사하는 대신 patch 단계에서 새 `CLAUDE.md`를 만들어 managed so2x-flow 섹션을 넣는다." in readme
    assert "예: `rm -rf`, 무차별 삭제/이동 같은 명령 차단" in readme
    assert "예: 필수 섹션, verification, 승인 게이트 질문, `Proposed Steps` 개수(3~7), 닫힌 next-step 질문 누락 방지" in readme
    assert "예: 긴 dry-run/grep/bash 출력은 요약본을 추가하고 error/traceback 라인은 유지" in readme
    assert "예: old_string mismatch, ambiguous match, permission 문제 재시도 가이드" in readme
    assert "예: 같은 patch/edit 실패 3회 이상이면 파일 재읽기나 다른 접근 유도" in readme
    assert "예: task 문서 없이 바로 구현부터 하려는 프롬프트 견제" in readme
    assert "예: 종료 전에 빠진 검증이나 다음 액션 누락 방지" in readme


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
    assert "`flow-review`, `flow-qa`는 필요할 때만 추가하고, GitHub PR 운영은 선택 사항이다" in feature_skill
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


def test_readme_install_prompt_forces_single_turn_completion_without_recap_only():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "1~5단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해" in readme
    assert 'recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고' in readme
    assert "마지막 정리에서는 step 1~4의 성공/실패만 먼저 짧게 요약하고, 그 다음 마지막 한 줄에만 다음 실행 안내를 plain 문장으로 넣어." in readme
    assert "그 마지막 줄은 bullet이나 코드블록으로 다시 감싸지 말고" in readme
    assert "그 마지막 줄 뒤에는 추가 조언 문장을 붙이지 말며" in readme
    assert '문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써' in readme
    assert "이 step 로그 뒤에 같은 install 실행의 출력 tail로 `next_step`, `next_step_cli`, `next_step_human`, `first_run_path`, `target`, `copied_count`, `skipped_existing_count`, `skipped_missing_count`, `claude_md_status`, `copied_files` 요약이 이어진다는 점도 같이 보고해." in readme
    assert "여기서 `copied_files: hidden (rerun with --verbose-copied-files to inspect each path)`는 기본 출력이 요약 모드라는 뜻이지, step 로그나 설치가 중간에 잘렸다는 뜻이 아니다." in readme
    assert "개별 복사 경로까지 확인이 정말 필요할 때만 같은 명령을 `--verbose-copied-files`와 함께 다시 실행해도 된다." in readme
    assert "다만 이 verbose 재실행은 선택 확인 단계일 뿐이고, 기본 설치 성공 판단은 step 로그와 아래 4개 필수 파일 존재 확인으로 먼저 닫는다." in readme
    assert "이 네 파일 존재 확인이 설치 성공 기준이고, 설치 직후 상태 surface까지 바로 보고 싶으면 선택적으로 `python3 .workflow/scripts/doctor.py --brief` 도 한 번 실행해. 이 선택 확인은 생략해도 step 4 cleanup과 `/flow-init` 진입으로 바로 넘어가면 된다." in readme
    assert "이 경로에서도 install 출력 tail에 legacy `next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.`, `next_step_cli: /flow-init`, `next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.`, `first_run_path: /flow-init -> /flow-plan -> /flow-feature`, `target: <설치 대상 경로>`, `copied_count: <복사된 파일 수>`, `skipped_existing_count: <기존 파일이라 유지된 수>`, `skipped_missing_count: <소스에 없어 건너뛴 수>`, `claude_md_status: <not created|created_or_updated|already_present>`, `copied_files: hidden (rerun with --verbose-copied-files to inspect each path)`가 함께 보이므로, Claude Code 사용자는 step 로그를 읽은 직후 기계용 바로가기 키와 첫 실행 순서뿐 아니라 지금 어디에 설치됐고 몇 개 파일이 복사됐는지, 기존 파일 유지나 소스 누락 skip가 몇 건 있었는지, `CLAUDE.md`가 생성/갱신됐는지, 기본 출력이 요약 모드이며 상세 경로는 정말 필요할 때만 `--verbose-copied-files` 재실행으로 보면 된다는 점뿐 아니라 사람용 다음 단계 문장까지 같은 응답 tail에서 바로 확인할 수 있다. 즉 기본 설치 성공 판단은 이 출력 tail과 step 3의 네 필수 파일 확인으로 먼저 닫히며, `python3 .workflow/scripts/doctor.py --brief`는 그 네 필수 파일 확인 뒤에만 덧붙이는 선택 상태 확인일 뿐 cleanup 선행 조건은 아니다. `.tmp/so2x-flow` cleanup은 그 네 파일 확인이 끝난 뒤에만 넘어가야 하며, doctor 확인을 생략해도 된다. 그다음 바로 `/flow-init`로 넘어가면 된다. 다만 `next_step_human`은 install 출력 tail에서 사람이 읽는 참고 키이고, step 5의 최종 응답은 그 키 이름을 다시 감싸지 말고 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 문장 자체를 plain 마지막 줄에 직접 남겨야 한다. 즉 마지막 줄을 `next_step:` 또는 `next_step_human:` 같은 키 이름으로 다시 시작하지 말고, 사람에게 바로 보이는 한국어 문장만 그대로 두는 것이 계약이다." in readme
    assert '`target:`은 설치 대상 디렉터리 절대 경로를, `copied_count:`는 복사된 파일 수를 보여주고, `skipped_existing_count:`와 `skipped_missing_count:`는 각각 기존 파일 유지 수와 소스 누락 skip 수를 보여주며, `claude_md_status:`는 `CLAUDE.md`가 생성/갱신됐는지 여부를 보여준다. `copied_files:`는 기본적으로 요약만 표시하며 개별 경로가 정말 필요할 때만 `--verbose-copied-files`로 다시 확인하면 된다.' in readme
    assert '즉 기본 성공 판단은 이 예시 블록 그대로 닫고, 개별 복사 경로가 궁금할 때만 `--verbose-copied-files` 재실행으로 넘어가면 된다.' in readme


def test_readme_install_examples_match_installer_required_file_contract():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")

    assert '".workflow/scripts/doctor.py",' in install_script
    assert "`.workflow/scripts/doctor.py`" in readme
    assert 'test -f .workflow/scripts/doctor.py' in readme
    assert 'test -f "$tmpdir/app/.workflow/scripts/doctor.py"' in readme
    assert readme.count("설치 직후 상태 surface까지 바로 확인하려면 위 검증 다음 줄에 `python3 .workflow/scripts/doctor.py --brief`를 한 번 더 실행하면 된다.") >= 2
    assert "설치가 잘 끝났는지 빠르게 보려면 install 출력 마지막에 legacy 호환 안내 줄인 `next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.`와, 기계용 바로가기 키인 `next_step_cli: /flow-init`, 사람용 안내 문장인 `next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.`가 함께 보이는지도 같이 확인하면 된다." in readme


def test_install_output_and_readme_show_one_obvious_next_action():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_script = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "설치가 끝나면 install 출력 마지막에 아래 안내가 보이면 된다." in readme
    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "next_step_cli: /flow-init" in readme
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in readme
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
    assert "next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "next_step_cli: /flow-init" in install_script
    assert "next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요." in install_script
    assert "first_run_path: /flow-init -> /flow-plan -> /flow-feature" in install_script
    # README install output example must also show target/copied_count/copied_files
    assert "target:" in readme
    assert "copied_count:" in readme
    assert "skipped_existing_count:" in readme
    assert "skipped_missing_count:" in readme
    assert "claude_md_status:" in readme
    assert "copied_files: hidden (rerun with --verbose-copied-files to inspect each path)" in readme
    assert "위 예시에서 `first_run_path:`, `target:`, `copied_count:`, `skipped_existing_count:`, `skipped_missing_count:`, `claude_md_status:`, `copied_files:` 줄도 실제 install 출력 tail에 `next_step` 안내와 함께 나오므로, shell 사용자는 다음 단계 안내뿐 아니라 첫 실행 경로(`/flow-init -> /flow-plan -> /flow-feature`), 설치 대상 경로, 복사 파일 수, 기존 파일 유지/소스 누락 여부, `CLAUDE.md` 처리 상태, 기본 출력이 summary mode인지 여부까지 한 번에 확인할 수 있다." in readme


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

    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback" in readme
    assert "runner 선택은 `.workflow/config/ccs-map.yaml`을 따른다. `auto`면 `ccs`가 있으면 `ccs`, 없으면 `claude -p`를 사용한다." in patch_claude
    assert "승인된 plan이 없으면" in readme
    assert ".workflow/tasks/plan/<slug>.json" in readme

    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-qa -> GitHub PR 운영은 옵션" in readme
    assert "GitHub PR 생성/본문 반영/checks watch는 필요할 때만 추가로 사용한다" in readme
    assert "이 변경 기준으로 /simplify를 한 번 돌려줘." in readme
    assert "convergence가 0이 아니면 /simplify를 다시 반복해줘." in readme
    assert "convergence 0이 되면 squash commit 기준으로 정리해줘." in readme
    assert "구현 전에 항상 `.workflow/tasks` 아래 task 문서를 먼저 만든다." in patch_claude
    assert "docs-first 실행에는 현재 프로젝트의 `.claude/skills` 아래 `flow-init`, `flow-feature`, `flow-qa`, `flow-review`, `flow-plan`을 사용한다." in patch_claude
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
    assert "구현 완료 -> /simplify 반복 -> convergence 0 -> squash -> 필요하면 flow-review 또는 flow-qa -> GitHub PR 운영은 옵션" in readme


def test_readme_documents_absorbed_role_contract_and_review_lenses():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Code Reuse Review / Code Quality Review / Efficiency Review를 명시적으로 남기고 싶다" in readme
    assert "## 역할 계약과 handoff" in readme
    assert "| planner | plan, feature | request, docs bundle, approved plan context, feature task | 방향 고정, `Proposed Steps`, verification gate | implementer |" in readme
    assert "review는 `Code Reuse Review`, `Code Quality Review`, `Efficiency Review` 세 렌즈를 항상 드러낸다." in readme


def test_skill_docs_lock_runtime_and_artifact_contracts():
    feature_skill = (ROOT / ".claude" / "skills" / "flow-feature.md").read_text(encoding="utf-8")
    plan_skill = (ROOT / ".claude" / "skills" / "flow-plan.md").read_text(encoding="utf-8")
    qa_skill = (ROOT / ".claude" / "skills" / "flow-qa.md").read_text(encoding="utf-8")
    review_skill = (ROOT / ".claude" / "skills" / "flow-review.md").read_text(encoding="utf-8")

    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in feature_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in plan_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in qa_skill
    assert "role별 `ccs_profile`이 없으면 그 role만 `claude -p`로 fallback하고 이유를 role 결과에 남긴다." in review_skill

    assert "`.workflow/tasks/feature/<slug>.json`" in feature_skill
    assert "`.workflow/tasks/plan/<slug>.json`" in plan_skill
    assert "`.workflow/tasks/qa/<slug>.json`" in qa_skill
    assert "`.workflow/tasks/review/<slug>.json`" in review_skill
