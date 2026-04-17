import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / ".workflow" / "scripts" / "install.py"


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(workspace), "--patch-claude-md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return workspace


def run_execute(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    return subprocess.run(
        [sys.executable, str(execute), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def output_path(workspace: Path, stdout: str, label: str) -> Path:
    prefix = f"{label}: "
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return workspace / line[len(prefix) :]
    raise AssertionError(f"Could not find {label} in stdout:\n{stdout}")


def test_init_dry_run_writes_outputs_and_lists_bootstrap_artifacts(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "init"
    assert ".claude/skills/flow-init.md" in payload["artifacts"]
    assert "DESIGN.md" in payload["artifacts"]
    assert payload["roles"] == ["planner"]


def test_feature_dry_run_collects_design_doc_creates_task_and_chains_planner_to_implementer(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "feature"
    assert payload["design_doc"] == "DESIGN.md"
    assert payload["approved_plan_path"] is None
    assert payload["approved_plan_match_reason"] == "no plan artifacts found"
    assert payload["docs_used"] == [
        ".workflow/docs/PRD.md",
        ".workflow/docs/ARCHITECTURE.md",
        ".workflow/docs/ADR.md",
        "DESIGN.md",
    ]
    assert [item["role"] for item in payload["role_results"]] == ["planner", "implementer"]
    assert payload["artifacts"] == [".workflow/tasks/feature/로그인-기능-구현.md"]

    task_text = (workspace / payload["artifacts"][0]).read_text(encoding="utf-8")
    assert "## Approved Direction" in task_text
    assert "## Implementation Slice" in task_text
    assert "## Out of Scope" in task_text
    assert "## Verification" in task_text
    assert "## Follow-up Slice" in task_text
    assert "## Next Step Prompt" in task_text
    assert "Latest approved flow-plan output: (none matched request)" in task_text
    assert "Source plan artifact: (none)" in task_text
    assert "승인된 plan이 없으면 여기서 멈추고 /flow-plan으로 먼저 범위를 확정할지 묻는다." in task_text
    assert "이 요청은 아직 승인된 방향이 없으니, /flow-plan으로 먼저 범위를 확정할까요? (y/n)" in task_text

    implementer_output = payload["role_results"][1]["output"]
    assert "planner_output:" in implementer_output
    assert "role: planner" in implementer_output
    assert "Implementation Slice" in implementer_output
    assert "Approved Direction" in implementer_output
    assert "approved_plan_path: (none)" in implementer_output
    assert "approved_plan_match_reason: no plan artifacts found" in implementer_output


def test_feature_dry_run_links_matching_latest_plan_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    feature_result = run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    assert feature_payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert feature_payload["approved_plan_match_reason"].startswith("matched plan ")
    assert feature_payload["approved_plan_path"] in feature_payload["docs_used"]
    task_text = (workspace / feature_payload["artifacts"][0]).read_text(encoding="utf-8")
    assert "Latest approved flow-plan output: .workflow/tasks/plan/로그인-기능-설계-확정.json" in task_text
    assert "Source plan artifact: .workflow/tasks/plan/로그인-기능-설계-확정.json" in task_text
    assert "승인된 방향이 있으니, 이번 slice를 진행할까요? (y/n)" in task_text
    implementer_output = feature_payload["role_results"][1]["output"]
    assert f"approved_plan_path: {plan_payload['artifacts'][0]}" in implementer_output


def test_feature_dry_run_does_not_link_unrelated_latest_plan_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "결제 기능 설계 확정", "--dry-run")
    feature_result = run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    assert feature_payload["approved_plan_path"] is None
    assert feature_payload["approved_plan_match_reason"].startswith("no sufficiently similar plan")
    assert ".workflow/tasks/plan/결제-기능-설계-확정.json" not in feature_payload["docs_used"]
    task_text = (workspace / feature_payload["artifacts"][0]).read_text(encoding="utf-8")
    assert "Latest approved flow-plan output: (none matched request)" in task_text
    assert "Source plan artifact: (none)" in task_text


def test_feature_dry_run_selects_best_matching_plan_even_if_latest_plan_is_unrelated(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    run_execute(workspace, "plan", "결제 기능 설계 확정", "--dry-run")

    feature_result = run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))

    assert feature_payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert feature_payload["approved_plan_match_reason"].startswith("matched plan similarity")
    assert ".workflow/tasks/plan/로그인-기능-설계-확정.json" in feature_payload["docs_used"]
    assert ".workflow/tasks/plan/결제-기능-설계-확정.json" not in feature_payload["docs_used"]


def test_feature_dry_run_rejects_plan_when_only_generic_tokens_overlap(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "사용자 경험 개선 설계 확정", "--dry-run")

    feature_result = run_execute(workspace, "feature", "알림 기능 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))

    assert feature_payload["approved_plan_path"] is None
    assert feature_payload["approved_plan_match_reason"].startswith("no sufficiently similar plan")


def test_feature_dry_run_marks_missing_ui_guide_as_optional_when_design_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    design = workspace / "DESIGN.md"
    ui_guide = workspace / ".workflow" / "docs" / "UI_GUIDE.md"
    design.unlink()
    ui_guide.unlink()
    result = run_execute(workspace, "feature", "알림 설정", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["design_doc"] is None
    assert ".workflow/docs/UI_GUIDE.md" not in payload["docs_used"]


def test_qa_dry_run_prioritizes_qa_doc_and_uses_qa_planner(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "qa", "QA-001 홈 버튼 클릭 안됨", "--qa-id", "QA-001", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "qa"
    assert payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert [item["role"] for item in payload["role_results"]] == ["qa_planner", "implementer"]
    task_text = (workspace / payload["artifacts"][0]).read_text(encoding="utf-8")
    assert "## Reproduction" in task_text
    assert "## Expected" in task_text
    assert "## Actual" in task_text
    assert "## Minimal Fix" in task_text
    assert "qa_id: QA-001" in payload["role_results"][1]["output"]


def test_review_dry_run_uses_reviewer_only_and_includes_design_doc(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "review", "이번 변경 QA 관점 점검", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "review"
    assert payload["roles"] == ["reviewer"]
    assert payload["design_doc"] == "DESIGN.md"
    assert payload["artifacts"] == []


def test_plan_dry_run_writes_outputs_under_plans_directory(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plans_dir = workspace / ".workflow" / "outputs" / "plan"
    plan_tasks_dir = workspace / ".workflow" / "tasks" / "plan"
    result = run_execute(workspace, "plan", "결제 기능 작업 분해", "--dry-run")
    output_json = output_path(workspace, result.stdout, "output_json")
    payload = read_json(output_json)
    assert payload["mode"] == "plan"
    assert output_json.parent == plans_dir
    assert "output_md" not in result.stdout
    assert payload["artifacts"] == [".workflow/tasks/plan/결제-기능-작업-분해.json"]

    plan_json = read_json(workspace / payload["artifacts"][0])
    assert (plan_tasks_dir / "결제-기능-작업-분해.json").exists()
    assert plan_json["request"] == "결제 기능 작업 분해"
    assert ".workflow/docs/PRD.md" in plan_json["related_docs"]
    assert "Option A" in plan_json["options"]
    assert plan_json["recommendation"] == "추천안을 한 줄로 명시하고 이유를 붙인다."
    assert "이 설계 방향 자체를 확정할지 사용자 승인을 요청한다." in plan_json["approval_gate"]
    assert plan_json["next_step_prompt"] == "이 설계 방향으로 확정할까요? (y/n)"

    planner_output = payload["role_results"][0]["output"]
    assert "Context Snapshot" in planner_output
    assert "Options" in planner_output
    assert "Recommendation" in planner_output
    assert "Approval Gate" in planner_output
    assert "Next Step Prompt" in planner_output


def test_skip_plan_removes_planner_role_from_feature_run(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "feature", "프로필 편집", "--skip-plan", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["roles"] == ["implementer"]
    assert "planner_output:" not in payload["role_results"][0]["output"]


def test_review_mode_collects_related_task_document_when_passed_via_task_option(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    feature_result = run_execute(workspace, "feature", "세션 만료 처리", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    task_relpath = feature_payload["artifacts"][0]
    review_result = run_execute(workspace, "review", "세션 만료 처리 검토", "--task", task_relpath, "--dry-run")
    review_payload = read_json(output_path(workspace, review_result.stdout, "output_json"))
    reviewer_output = review_payload["role_results"][0]["output"]
    assert task_relpath in review_payload["docs_used"]
    assert "## Proposed Steps" in reviewer_output


def test_legacy_mode_aliases_still_work(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    qa_payload = read_json(output_path(workspace, run_execute(workspace, "qa-fix", "QA-009 토글 오동작", "--qa-id", "QA-009", "--dry-run").stdout, "output_json"))
    plan_payload = read_json(output_path(workspace, run_execute(workspace, "plan-only", "결제 기능 작업 분해", "--dry-run").stdout, "output_json"))
    assert qa_payload["mode"] == "qa"
    assert plan_payload["mode"] == "plan"


def test_requested_ccs_falls_back_to_claude_when_ccs_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    original = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    updated = json.loads(json.dumps(original))
    updated["runtime"]["runner"] = "ccs"
    config_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_execute(workspace, "review", "출력 경로 확인", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["requested_runner"] == "ccs"
    assert payload["selected_runner"] in {"ccs", "claude"}
    if payload["selected_runner"] == "claude":
        assert payload["fallback_used"] is True
        assert "claude -p" in payload["role_results"][0]["command_preview"]


def test_execute_uses_runner_resolution_layer_and_live_runner_path(tmp_path: Path):
    execute = (ROOT / ".workflow" / "scripts" / "execute.py").read_text(encoding="utf-8")
    assert "from ccs_runner import resolve_runner, run_role, run_role_subprocess" in execute

    workspace = make_workspace(tmp_path)
    fake_runner = workspace / "fake-claude.sh"
    fake_runner.write_text("#!/usr/bin/env bash\nprintf 'live-ok\\n'\n", encoding="utf-8")
    fake_runner.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "claude"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_runner)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["reviewer"]["claude"]["command"] = str(fake_runner)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = run_execute(workspace, "review", "실실행 테스트")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["role_results"][0]["status"] == "success"
    assert payload["role_results"][0]["output"] == "live-ok\n"


def test_live_execution_requires_explicit_runtime_opt_in(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "실실행 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "allow_live_run" in result.stderr
