import importlib.util
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


def make_sample_target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-target"
    repo.mkdir()
    (repo / "README.md").write_text("# sample target\n", encoding="utf-8")
    (repo / "app.py").write_text("print('sample app')\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("# local target guide\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Hermes"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "hermes@example.com"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "commit", "-m", "chore: sample target bootstrap"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(repo), "--patch-claude-md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return repo


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def output_path(workspace: Path, stdout: str, label: str) -> Path:
    prefix = f"{label}: "
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return workspace / line[len(prefix) :]
    raise AssertionError(f"Could not find {label} in stdout:\n{stdout}")


def test_init_dry_run_creates_questionnaire_task_and_uses_canonical_init_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert "mode: init" in result.stdout
    assert payload["mode"] == "init"
    assert payload["roles"] == []
    assert payload["role_results"] == []
    assert payload["artifacts"] == [".workflow/tasks/init/개인용-운동-코칭-앱-mvp.json"]
    assert ".claude/skills/flow-init.md" not in payload["artifacts"]
    assert payload["docs_used"] == [
        ".workflow/docs/PRD.md",
        ".workflow/docs/ARCHITECTURE.md",
        ".workflow/docs/ADR.md",
        ".workflow/docs/QA.md",
        "DESIGN.md",
    ]

    init_json = read_json(workspace / payload["artifacts"][0])
    assert init_json["title"] == "개인용 운동 코칭 앱 MVP"
    assert init_json["status"] == "needs_user_input"
    assert init_json["answers"] == {}
    assert init_json["init_mode_options"] == [
        "auto-fill-now",
        "ask-first",
    ]
    assert init_json["selected_init_mode"] == "ask-first"
    assert init_json["pending_questions"] == [
        "project_name",
        "goal",
        "users",
        "scope",
        "out_of_scope",
        "architecture",
        "qa",
        "design",
    ]
    assert init_json["current_question_id"] is None
    assert init_json["next_mode_prompt"] == "먼저 방식을 골라주세요: 1. 자동채우기 2. 질문"
    assert init_json["next_step_prompt"] == "먼저 1번(자동채우기) 또는 2번(질문) 중 하나를 골라주세요."
    assert [item["id"] for item in init_json["questions"]] == [
        "project_name",
        "goal",
        "users",
        "scope",
        "out_of_scope",
        "architecture",
        "qa",
        "design",
    ]
    assert init_json["questions"][0]["target_doc"] == ".workflow/docs/PRD.md"
    assert init_json["questions"][-1]["target_doc"] == "DESIGN.md"


def test_init_dry_run_applies_auto_fill_now_mode_from_existing_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    existing = read_json(init_path)
    existing["selected_init_mode"] = "auto-fill-now"
    init_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    second = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    rerun_payload = read_json(output_path(workspace, second.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])

    assert rerun_json["status"] == "draft_auto_filled"
    assert rerun_json["answers"] == {"project_name": "개인용 운동 코칭 앱 MVP", "goal": "개인용 운동 코칭 앱 MVP"}
    assert rerun_json["current_question_id"] == "users"
    assert rerun_json["next_step_prompt"] == "자동으로 채운 초안을 확인했고, 남은 질문은 한 번에 하나씩 이어서 물어보면 돼요."


def test_init_dry_run_preserves_existing_answers_on_rerun(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    existing = read_json(init_path)
    existing["status"] = "in_progress"
    existing["answers"] = {"project_name": "핏로그", "goal": "운동 기록 자동화"}
    existing["notes"] = ["keep-me"]
    init_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    second = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    rerun_payload = read_json(output_path(workspace, second.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])

    assert rerun_json["status"] == "in_progress"
    assert rerun_json["answers"] == {"project_name": "핏로그", "goal": "운동 기록 자동화"}
    assert rerun_json["notes"] == ["keep-me"]



def test_init_dry_run_resets_status_to_needs_user_input_when_answers_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    existing = read_json(init_path)
    existing["status"] = "in_progress"
    existing["notes"] = ["keep-me"]
    init_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    second = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    rerun_payload = read_json(output_path(workspace, second.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])

    assert rerun_json["status"] == "needs_user_input"
    assert rerun_json["notes"] == ["keep-me"]
    assert rerun_json["answers"] == {}



def test_init_dry_run_resets_status_to_needs_user_input_when_answers_empty(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    existing = read_json(init_path)
    existing["status"] = "in_progress"
    existing["answers"] = {}
    init_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    second = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    rerun_payload = read_json(output_path(workspace, second.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])

    assert rerun_json["status"] == "needs_user_input"
    assert rerun_json["answers"] == {}



def test_init_dry_run_keeps_questionnaire_only_without_planner_execution(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["roles"] == []
    assert payload["role_results"] == []
    assert "role_outputs:" in result.stdout
    assert "planner (dry-run)" not in result.stdout
    assert "planner output:" not in result.stdout


def test_init_rerun_fails_clearly_when_persisted_artifact_is_missing_required_questions(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    broken = read_json(init_path)
    broken.pop("questions")
    init_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "init", "개인용 운동 코칭 앱 MVP", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "init missing required field: questions" in (result.stderr or result.stdout)



def test_plan_rerun_fails_clearly_when_persisted_artifact_has_invalid_approved_type(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    plan_path = workspace / payload["artifacts"][0]

    broken = read_json(plan_path)
    broken["approved"] = "yes"
    plan_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "plan", "로그인 기능 설계 확정", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "plan field 'approved' must be of type bool" in (result.stderr or result.stdout)



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
    assert payload["artifacts"] == [".workflow/tasks/feature/로그인-기능-구현.json"]

    task_json = read_json(workspace / payload["artifacts"][0])
    assert task_json["approved_direction"]["source_plan_artifact"] == "(none)"
    assert task_json["latest_approved_flow_plan_output"] == "(none matched request)"
    assert "승인된 plan이 없으면 여기서 멈추고 /flow-plan으로 먼저 범위를 확정할지 묻는다." in task_json["approval_gate"][0]
    assert task_json["next_step_prompt"] == "이 요청은 아직 승인된 방향이 없으니, /flow-plan으로 먼저 범위를 확정할까요? (y/n)"

    implementer_output = payload["role_results"][1]["output"]
    assert "planner_output:" in implementer_output
    assert "role: planner" in implementer_output
    assert "Implementation Slice" in implementer_output
    assert "Approved Direction" in implementer_output
    assert "approved_plan_path: (none)" in implementer_output
    assert "approved_plan_match_reason: no plan artifacts found" in implementer_output


def test_execute_doctor_mode_persists_status_surface(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    result = run_execute(workspace, "doctor")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["mode"] == "doctor"
    assert payload["overall_status"] == "ok"
    assert payload["exact_status"] == "ok:feature"
    assert payload["latest_output_json"] == ".workflow/outputs/feature/로그인-기능-구현.json"
    assert payload["latest_outputs"]["doctor"] == ".workflow/outputs/doctor/status.json"


def test_execute_doctor_mode_uses_default_request_and_prints_doctor_summary(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    result = run_execute(workspace, "doctor")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert "overall_status: idle" in result.stdout
    assert "exact_status: idle" in result.stdout
    assert payload["mode"] == "doctor"
    assert payload["overall_status"] == "idle"


def test_feature_dry_run_links_matching_latest_plan_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    feature_result = run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    assert feature_payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert feature_payload["approved_plan_match_reason"].startswith("matched plan ")
    assert feature_payload["approved_plan_path"] in feature_payload["docs_used"]
    task_json = read_json(workspace / feature_payload["artifacts"][0])
    assert task_json["latest_approved_flow_plan_output"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert task_json["approved_direction"]["source_plan_artifact"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert task_json["next_step_prompt"] == "승인된 방향이 있으니, 이번 slice를 진행할까요? (y/n)"
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
    task_json = read_json(workspace / feature_payload["artifacts"][0])
    assert task_json["latest_approved_flow_plan_output"] == "(none matched request)"
    assert task_json["approved_direction"]["source_plan_artifact"] == "(none)"


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



def test_feature_dry_run_prefers_more_specific_plan_match_over_broader_overlap(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "로그인 보안 강화 설계 확정", "--dry-run")
    run_execute(workspace, "plan", "로그인 비밀번호 재설정 설계 확정", "--dry-run")

    feature_result = run_execute(workspace, "feature", "로그인 비밀번호 재설정 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))

    assert feature_payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-비밀번호-재설정-설계-확정.json"
    assert "shared_tokens=로그인, 비밀번호, 재설정" in feature_payload["approved_plan_match_reason"]
    assert "candidate=로그인-비밀번호-재설정-설계-확정" in feature_payload["approved_plan_match_reason"]



def test_feature_dry_run_can_match_plan_by_artifact_request_when_filename_is_generic(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 비밀번호 재설정 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    original_path = workspace / plan_payload["artifacts"][0]
    renamed_path = original_path.with_name("승인된-최근-작업.json")
    original_path.rename(renamed_path)

    feature_result = run_execute(workspace, "feature", "로그인 비밀번호 재설정 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))

    assert feature_payload["approved_plan_path"] == ".workflow/tasks/plan/승인된-최근-작업.json"
    assert "artifact request" in feature_payload["approved_plan_match_reason"]



def test_feature_dry_run_reports_best_below_threshold_candidate_when_no_match(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "알림 이메일 설정 설계 확정", "--dry-run")

    feature_result = run_execute(workspace, "feature", "알림 설정 구현", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))

    assert feature_payload["approved_plan_path"] is None
    assert "best_candidate=알림-이메일-설정-설계-확정" in feature_payload["approved_plan_match_reason"]
    assert "shared_tokens=설정, 알림" in feature_payload["approved_plan_match_reason"]
    assert "threshold=" in feature_payload["approved_plan_match_reason"]



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
    task_json = read_json(workspace / payload["artifacts"][0])
    assert task_json["reproduction"] == ["Describe how to reproduce the issue."]
    assert task_json["expected"] == ["Describe the intended behavior."]
    assert task_json["actual"] == ["Describe the current broken behavior."]
    assert task_json["minimal_fix"] == ["Describe the smallest safe repair."]
    assert "qa_id: QA-001" in payload["role_results"][1]["output"]


def test_review_dry_run_uses_reviewer_only_and_includes_design_doc(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "review", "이번 변경 QA 관점 점검", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "review"
    assert payload["roles"] == ["reviewer"]
    assert payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert payload["design_doc"] == "DESIGN.md"
    assert payload["artifacts"] == [".workflow/tasks/review/이번-변경-qa-관점-점검.json"]


def test_plan_dry_run_uses_single_canonical_task_artifact(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_tasks_dir = workspace / ".workflow" / "tasks" / "plan"
    result = run_execute(workspace, "plan", "결제 기능 작업 분해", "--dry-run")
    output_json = output_path(workspace, result.stdout, "output_json")
    payload = read_json(output_json)
    assert payload["mode"] == "plan"
    assert output_json == workspace / ".workflow" / "outputs" / "plan" / "결제-기능-작업-분해.json"
    assert "output_md" not in result.stdout
    assert payload["artifacts"] == [".workflow/tasks/plan/결제-기능-작업-분해.json"]

    plan_json = read_json(workspace / payload["artifacts"][0])
    assert (plan_tasks_dir / "결제-기능-작업-분해.json").exists()
    assert plan_json["request"] == "결제 기능 작업 분해"
    assert plan_json["status"] == "draft"
    assert plan_json["approved"] is False
    assert ".workflow/docs/PRD.md" in plan_json["related_docs"]
    assert ".workflow/docs/PRD.md" in payload["docs_used"]
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


def test_skip_plan_requires_existing_approved_plan_for_feature_run(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "프로필 편집", "--skip-plan", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "skip-plan requires an explicitly approved plan artifact" in result.stderr



def test_skip_plan_rejects_unapproved_matching_plan(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "프로필 편집 설계 확정", "--dry-run")
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "프로필 편집", "--skip-plan", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "skip-plan requires an explicitly approved plan artifact" in result.stderr



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



def test_live_execution_rejects_non_boolean_allow_live_run_values(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["allow_live_run"] = "true"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "실실행 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "allow_live_run must be a boolean true" in result.stderr



def test_feature_live_execution_requires_approved_plan_even_without_skip_plan(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["allow_live_run"] = True
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "프로필 편집"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "feature live execution requires an explicitly approved plan artifact" in result.stderr



def test_skip_plan_allows_feature_run_when_matching_plan_is_explicitly_approved(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "프로필 편집 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_execute(workspace, "feature", "프로필 편집", "--skip-plan", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["roles"] == ["implementer"]
    assert payload["approved_plan_path"] == ".workflow/tasks/plan/프로필-편집-설계-확정.json"
    assert "planner_output:" not in payload["role_results"][0]["output"]



def test_plan_rerun_preserves_explicit_approval_metadata(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "프로필 편집 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    rerun = run_execute(workspace, "plan", "프로필 편집 설계 확정", "--dry-run")
    rerun_payload = read_json(output_path(workspace, rerun.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])
    assert rerun_json["approved"] is True
    assert rerun_json["status"] == "approved"


def test_review_mode_collects_related_task_document_when_passed_via_task_option(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    feature_result = run_execute(workspace, "feature", "세션 만료 처리", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    task_relpath = feature_payload["artifacts"][0]
    review_result = run_execute(workspace, "review", "세션 만료 처리 검토", "--task", task_relpath, "--dry-run")
    review_payload = read_json(output_path(workspace, review_result.stdout, "output_json"))
    assert task_relpath in review_payload["docs_used"]
    assert review_payload["artifacts"] == [".workflow/tasks/review/세션-만료-처리-검토.json"]
    review_json = read_json(workspace / review_payload["artifacts"][0])
    assert review_json["related_task"] == task_relpath


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


def test_build_payload_leaves_output_json_empty_until_persisted(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Resolution:
        requested_runner = "claude"
        selected_runner = "claude"
        fallback_used = False
        fallback_reason = None

    payload = module.build_payload(
        mode="review",
        request="출력 경로 확인",
        dry_run=True,
        resolution=Resolution(),
        design_doc="DESIGN.md",
        approved_plan_path=None,
        approved_plan_match_reason=None,
        docs_used=[".workflow/docs/QA.md"],
        roles=["reviewer"],
        role_results=[],
        artifacts=[".workflow/tasks/review/출력-경로-확인.json"],
    )

    assert payload["output_json"] == ""



def test_build_payload_keeps_failure_and_fallback_contract_fields(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Resolution:
        requested_runner = "ccs"
        selected_runner = "claude"
        fallback_used = True
        fallback_reason = "ccs not found; falling back to claude -p"

    role_results = [
        {
            "role": "planner",
            "runner": "claude",
            "engine": "claude",
            "model": "claude-sonnet",
            "status": "success",
            "output": "planner ok\n",
            "command": ["claude", "-p", "hello"],
            "command_preview": "claude -p hello",
            "fallback_reason": "role=planner profile 'codex' is not available via ccs",
        }
    ]

    payload = module.build_payload(
        mode="feature",
        request="로그인 기능 구현",
        dry_run=False,
        resolution=Resolution(),
        design_doc="DESIGN.md",
        approved_plan_path=".workflow/tasks/plan/로그인-기능-설계-확정.json",
        approved_plan_match_reason="explicit approval metadata matched latest request",
        docs_used=[".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md"],
        roles=["planner", "implementer"],
        role_results=role_results,
        artifacts=[".workflow/tasks/feature/로그인-기능-구현.json"],
        failed_role="implementer",
        failed_stage="role_execution",
        failure_message="implementer failed after planner success",
    )

    assert payload["requested_runner"] == "ccs"
    assert payload["selected_runner"] == "claude"
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "ccs not found; falling back to claude -p"
    assert payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert payload["failed_role"] == "implementer"
    assert payload["failed_stage"] == "role_execution"
    assert payload["failure_message"] == "implementer failed after planner success"
    assert payload["role_results"][0]["fallback_reason"] == "role=planner profile 'codex' is not available via ccs"
    assert payload["output_json"] == ""



def test_print_summary_emits_fallbacks_failures_and_output_json_lines(tmp_path: Path, capsys):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    payload = {
        "mode": "feature",
        "artifact_kind": "feature",
        "request": "로그인 기능 구현",
        "dry_run": False,
        "requested_runner": "ccs",
        "selected_runner": "ccs",
        "fallback_used": False,
        "fallback_reason": None,
        "design_doc": "DESIGN.md",
        "approved_plan_path": ".workflow/tasks/plan/로그인-기능-설계-확정.json",
        "approved_plan_match_reason": "token overlap matched approved artifact",
        "docs_used": [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md"],
        "roles": ["planner", "implementer"],
        "role_results": [
            {
                "role": "planner",
                "runner": "ccs",
                "engine": "codex",
                "model": "codex",
                "status": "success",
                "output": "planner ok\n",
                "command": ["ccs", "codex", "prompt"],
                "command_preview": "ccs codex prompt",
                "fallback_reason": None,
            },
            {
                "role": "implementer",
                "runner": "claude",
                "engine": "claude",
                "model": "claude-sonnet",
                "status": "failed",
                "output": "",
                "command": ["claude", "-p", "prompt"],
                "command_preview": "claude -p prompt",
                "fallback_reason": "role=implementer profile 'missing-profile' is not available via ccs",
            },
        ],
        "artifacts": [".workflow/tasks/feature/로그인-기능-구현.json"],
        "failed_role": "implementer",
        "failed_stage": "role_execution",
        "failure_message": "implementer failed after planner success",
        "output_json": ".workflow/outputs/feature/로그인-기능-구현.json",
    }

    module.print_summary(payload)
    stdout = capsys.readouterr().out
    assert "fallback_used: False" in stdout
    assert "fallback_reason: (none)" in stdout
    assert "approved_plan_path: .workflow/tasks/plan/로그인-기능-설계-확정.json" in stdout
    assert "approved_plan_match_reason: token overlap matched approved artifact" in stdout
    assert "role_fallbacks:" in stdout
    assert "  - planner: (none)" in stdout
    assert "  - implementer: role=implementer profile 'missing-profile' is not available via ccs" in stdout
    assert "failed_role: implementer" in stdout
    assert "failed_stage: role_execution" in stdout
    assert "failure_message: implementer failed after planner success" in stdout
    assert "output_json: .workflow/outputs/feature/로그인-기능-구현.json" in stdout



def test_run_roles_reports_runner_resolution_stage_separately(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    runtime_path = workspace / ".workflow" / "scripts" / "execution_runtime.py"
    scripts_dir = str(runtime_path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("so2x_flow_execution_runtime", runtime_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class Resolution:
            selected_runner = "ccs"

        class Context:
            roles = ["implementer"]
            docs_used = [".workflow/docs/PRD.md"]
            docs_bundle = "bundle"
            task_path = None
            task_content = None
            design_doc = "DESIGN.md"
            approved_plan_path = None
            approved_plan_match_reason = None

        def fake_resolve_role_runner(**kwargs):
            raise RuntimeError("probe exploded")

        module.resolve_role_runner = fake_resolve_role_runner

        try:
            module.run_roles(
                config={"roles": {"implementer": {"ccs": {"command": "ccs"}}}},
                resolution=Resolution(),
                runtime_config={},
                prompts_dir=workspace / ".workflow" / "prompts",
                mode="feature",
                request="로그인 기능 구현",
                context=Context(),
                qa_id=None,
                dry_run=True,
            )
        except module.ExecutionFailure as exc:
            assert exc.stage == "runner_resolution"
            assert exc.role == "implementer"
            assert exc.role_results == []
            assert "probe exploded" in exc.message
        else:
            raise AssertionError("Expected ExecutionFailure for runner resolution")
    finally:
        sys.path.remove(scripts_dir)



def test_run_roles_reports_prompt_build_stage_separately(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    runtime_path = workspace / ".workflow" / "scripts" / "execution_runtime.py"
    scripts_dir = str(runtime_path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("so2x_flow_execution_runtime", runtime_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class Resolution:
            selected_runner = "claude"

        class RoleResolution:
            selected_runner = "claude"
            fallback_reason = None

        class Context:
            roles = ["reviewer"]
            docs_used = [".workflow/docs/QA.md"]
            docs_bundle = "bundle"
            task_path = None
            task_content = None
            design_doc = "DESIGN.md"
            approved_plan_path = None
            approved_plan_match_reason = None

        module.resolve_role_runner = lambda **kwargs: RoleResolution()
        module.build_prompt = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("prompt template missing"))

        try:
            module.run_roles(
                config={"roles": {"reviewer": {"claude": {"command": "claude"}}}},
                resolution=Resolution(),
                runtime_config={},
                prompts_dir=workspace / ".workflow" / "prompts",
                mode="review",
                request="QA 관점 점검",
                context=Context(),
                qa_id=None,
                dry_run=True,
            )
        except module.ExecutionFailure as exc:
            assert exc.stage == "prompt_build"
            assert exc.role == "reviewer"
            assert exc.role_results == []
            assert "prompt template missing" in exc.message
        else:
            raise AssertionError("Expected ExecutionFailure for prompt build")
    finally:
        sys.path.remove(scripts_dir)



def test_execute_uses_runner_resolution_layer_and_live_runner_path(tmp_path: Path):
    execute = (ROOT / ".workflow" / "scripts" / "execute.py").read_text(encoding="utf-8")
    execution_runtime = (ROOT / ".workflow" / "scripts" / "execution_runtime.py").read_text(encoding="utf-8")
    prompt_builder = (ROOT / ".workflow" / "scripts" / "prompt_builder.py").read_text(encoding="utf-8")
    mode_handlers = (ROOT / ".workflow" / "scripts" / "mode_handlers.py").read_text(encoding="utf-8")
    payloads = (ROOT / ".workflow" / "scripts" / "payloads.py").read_text(encoding="utf-8")
    workflow_context = (ROOT / ".workflow" / "scripts" / "workflow_context.py").read_text(encoding="utf-8")
    workflow_docs = (ROOT / ".workflow" / "scripts" / "workflow_docs.py").read_text(encoding="utf-8")
    workflow_tasks = (ROOT / ".workflow" / "scripts" / "workflow_tasks.py").read_text(encoding="utf-8")
    assert "from ccs_runner import resolve_runner" in execute
    assert "from execution_runtime import" in execute
    assert "def run_roles(" in execution_runtime
    assert "def validate_runtime_config(" in execution_runtime
    assert "runner_resolution" in execution_runtime
    assert "prompt_build" in execution_runtime
    assert "def build_prompt(" in prompt_builder
    assert "project_root=project_root" not in execution_runtime
    assert "project_root=PROJECT_ROOT,\n            mode=mode,\n            request=args.request,\n            context=context,\n            qa_id=args.qa_id,\n            dry_run=args.dry_run" not in execute
    assert "task_content=context.task_content" in execution_runtime
    assert "task_content: str | None" in mode_handlers
    assert "planner_output: str | None" not in mode_handlers
    assert "load_text(task_file)" not in prompt_builder
    assert "from workflow_docs import collect_docs, load_docs_bundle" in mode_handlers
    assert "from workflow_context import select_approved_plan" in mode_handlers
    assert "from workflow_tasks import (" in mode_handlers
    assert "def build_payload(" in payloads
    assert "def select_approved_plan(" in workflow_context
    assert "def collect_docs(" not in workflow_context
    assert "def load_docs_bundle(" not in workflow_context
    assert "def collect_docs(" in workflow_docs
    assert "def load_docs_bundle(" in workflow_docs
    assert "def write_feature_task(" in workflow_tasks
    assert "def write_init_task(" in workflow_tasks
    assert "def write_plan_mode_task(" in workflow_tasks

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



def test_live_execution_requires_explicit_runtime_opt_in_duplicate_guard(tmp_path: Path):
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



def test_live_execution_uses_role_specific_timeout_and_persists_failure_payload(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    fake_runner = workspace / "fake-timeout.sh"
    fake_runner.write_text("#!/usr/bin/env bash\nsleep 2\n", encoding="utf-8")
    fake_runner.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "claude"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_runner)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["runtime"]["role_timeouts"] = {"reviewer": 1}
    config["roles"]["reviewer"]["claude"]["command"] = str(fake_runner)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "타임아웃 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "failed_role: reviewer" in result.stdout
    assert "timed out after 1s" in result.stderr
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["failed_role"] == "reviewer"
    assert payload["failed_stage"] == "role_execution"
    assert payload["role_results"] == []
    assert "timed out after 1s" in payload["failure_message"]



def test_live_execution_persists_partial_results_when_later_role_fails(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 구현", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    fake_claude = workspace / "fake-claude.sh"
    fake_claude.write_text("#!/usr/bin/env bash\nprintf 'planner-live-ok\\n'\n", encoding="utf-8")
    fake_claude.chmod(0o755)

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    probe_dir = workspace / "probe-bin"
    probe_dir.mkdir()
    probe = probe_dir / "ccs"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"missing-profile\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  echo \"Profile 'missing-profile' not found\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "if [ \"$1\" = \"codex\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  exit 0\n"
        "fi\n"
        "printf 'planner-live-ok\\n'\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)

    failing_claude = workspace / "fake-failing-claude.sh"
    failing_claude.write_text("#!/usr/bin/env bash\necho 'implementer failed' >&2\nexit 9\n", encoding="utf-8")
    failing_claude.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_claude)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["planner"]["ccs_profile"] = "codex"
    config["roles"]["planner"]["ccs"]["command"] = str(probe)
    config["roles"]["implementer"]["ccs_profile"] = "missing-profile"
    config["roles"]["implementer"]["claude"]["command"] = str(failing_claude)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env = dict(**__import__("os").environ)
    env["PATH"] = f"{probe_dir}:{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "로그인 기능 구현"],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "failed_role: implementer" in result.stdout
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["failed_role"] == "implementer"
    assert payload["failed_stage"] == "role_execution"
    assert len(payload["role_results"]) == 1
    assert payload["role_results"][0]["role"] == "planner"
    assert payload["role_results"][0]["output"] == "planner-live-ok\n"
    assert "fallback_reason" in payload["failure_message"]
    assert "implementer failed" in payload["failure_message"]



def test_live_ccs_execution_surfaces_codex_auth_guidance(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    fake_ccs = workspace / "fake-ccs.sh"
    fake_ccs.write_text(
        "#!/usr/bin/env bash\n"
        "echo '[X] Failed to start OAuth flow' >&2\n"
        "echo '[X] Authentication required for OpenAI Codex' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_ccs.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["roles"]["planner"]["ccs"]["command"] = str(fake_ccs)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "plan", "결제 기능 작업 분해"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ccs is installed but Codex auth is not configured" in result.stderr
    assert "run `ccs setup` or `ccs codex --auth`" in result.stderr


def test_docs_first_smoke_plan_feature_qa_sequence(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    plan_result = run_execute(workspace, "plan", "로그인 폼 validation과 submit 흐름 추가", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    assert plan_json["request"] == "로그인 폼 validation과 submit 흐름 추가"
    assert plan_json["status"] == "draft"
    assert plan_json["approved"] is False

    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_result = run_execute(workspace, "feature", "로그인 폼 validation과 submit 흐름 추가", "--skip-plan", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    feature_json = read_json(workspace / feature_payload["artifacts"][0])
    assert feature_payload["roles"] == ["implementer"]
    assert feature_payload["approved_plan_path"] == plan_payload["artifacts"][0]
    assert feature_json["latest_approved_flow_plan_output"] == plan_payload["artifacts"][0]
    assert feature_json["approved_direction"]["source_plan_artifact"] == plan_payload["artifacts"][0]
    assert feature_json["verification"] == ["List the checks required before considering this slice done."]

    qa_result = run_execute(workspace, "qa", "로그인 실패시 에러 메시지와 재시도 동작 점검", "--qa-id", "QA-101", "--dry-run")
    qa_payload = read_json(output_path(workspace, qa_result.stdout, "output_json"))
    qa_json = read_json(workspace / qa_payload["artifacts"][0])
    assert qa_payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert qa_payload["roles"] == ["qa_planner", "implementer"]
    assert qa_json["qa_id"] == "QA-101"
    assert qa_json["reproduction"] == ["Describe how to reproduce the issue."]
    assert qa_json["minimal_fix"] == ["Describe the smallest safe repair."]


def test_external_sample_repo_install_init_plan_e2e_smoke(tmp_path: Path):
    repo = make_sample_target_repo(tmp_path)

    init_result = run_execute(repo, "init", "외부 샘플 앱 초기 설정", "--dry-run")
    init_payload = read_json(output_path(repo, init_result.stdout, "output_json"))
    init_json = read_json(repo / init_payload["artifacts"][0])
    assert (repo / "README.md").read_text(encoding="utf-8") == "# sample target\n"
    assert (repo / "app.py").read_text(encoding="utf-8") == "print('sample app')\n"
    assert "## so2x-flow" in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert init_json["status"] == "needs_user_input"
    assert init_json["current_question_id"] is None
    assert init_payload["docs_used"][0] == ".workflow/docs/PRD.md"

    plan_result = run_execute(repo, "plan", "외부 샘플 앱 로그인 흐름 작업 분해", "--dry-run")
    plan_payload = read_json(output_path(repo, plan_result.stdout, "output_json"))
    plan_json = read_json(repo / plan_payload["artifacts"][0])
    assert plan_json["request"] == "외부 샘플 앱 로그인 흐름 작업 분해"
    assert plan_json["status"] == "draft"
    assert plan_json["approved"] is False
    assert (repo / ".workflow" / "scripts" / "execute.py").exists()
    assert (repo / ".claude" / "skills" / "flow-init.md").exists()


def test_live_feature_role_can_fallback_to_claude_when_ccs_profile_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 구현", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    fake_claude = workspace / "fake-claude.sh"
    fake_claude.write_text("#!/usr/bin/env bash\nprintf 'claude-live-ok\\n'\n", encoding="utf-8")
    fake_claude.chmod(0o755)

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    probe_dir = workspace / "probe-bin"
    probe_dir.mkdir()
    probe = probe_dir / "ccs"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"missing-profile\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  echo \"Profile 'missing-profile' not found\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "printf 'ccs-live-ok\\n'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_claude)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["planner"]["ccs_profile"] = "codex"
    config["roles"]["implementer"]["ccs_profile"] = "missing-profile"
    config["roles"]["planner"]["claude"]["command"] = str(fake_claude)
    config["roles"]["implementer"]["claude"]["command"] = str(fake_claude)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env = dict(**__import__("os").environ)
    env["PATH"] = f"{probe_dir}:{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "로그인 기능 구현"],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["selected_runner"] == "ccs"
    assert "role_fallbacks:" in result.stdout
    assert "  - planner: (none)" in result.stdout
    assert payload["role_results"][0]["runner"] == "ccs"
    assert payload["role_results"][0]["fallback_reason"] is None
    assert payload["role_results"][0]["output"] == "ccs-live-ok\n"
    assert payload["role_results"][1]["runner"] == "claude"
    assert "role=implementer profile 'missing-profile' is not available via ccs" in payload["role_results"][1]["fallback_reason"]
    assert "role=implementer profile 'missing-profile' is not available via ccs" in result.stdout
    assert payload["role_results"][1]["output"] == "claude-live-ok\n"


def test_artifact_validation_rejects_missing_required_plan_field(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_plan = module.render_plan_doc("결제 기능 작업 분해", [".workflow/docs/PRD.md"])
    invalid_plan.pop("next_step_prompt")

    try:
        module.validate_artifact("plan", invalid_plan)
    except ValueError as exc:
        assert "plan missing required field: next_step_prompt" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid plan artifact")


def test_artifact_validation_rejects_wrong_feature_field_type(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_feature = module.render_feature_task("로그인 기능 구현")
    invalid_feature["verification"] = "not-a-list"

    try:
        module.validate_artifact("feature", invalid_feature)
    except ValueError as exc:
        assert "feature field 'verification' must be of type list" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid feature artifact")


def test_artifact_validation_rejects_invalid_init_question_shape(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_init = module.render_init_task("개인용 운동 코칭 앱 MVP")
    invalid_init["questions"] = [{"id": "project_name", "question": "이름?"}]

    try:
        module.validate_artifact("init", invalid_init)
    except ValueError as exc:
        assert "init questions[0] missing required field: target_doc" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid init artifact question shape")



def test_artifact_validation_rejects_invalid_init_status_value(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_init = module.render_init_task("개인용 운동 코칭 앱 MVP")
    invalid_init["status"] = "done"

    try:
        module.validate_artifact("init", invalid_init)
    except ValueError as exc:
        assert "init field 'status' must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid init status")



def test_artifact_validation_rejects_invalid_plan_options_shape(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_plan = module.render_plan_doc("결제 기능 작업 분해", [".workflow/docs/PRD.md"])
    invalid_plan["options"] = {"Option A": "가장 작은 MVP 접근"}

    try:
        module.validate_artifact("plan", invalid_plan)
    except ValueError as exc:
        assert "plan options['Option A'] must be a list[str]" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid plan options shape")



def test_artifact_validation_rejects_invalid_feature_approved_direction_shape(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_feature = module.render_feature_task("로그인 기능 구현")
    invalid_feature["approved_direction"] = {"summary": "요약만 있음"}

    try:
        module.validate_artifact("feature", invalid_feature)
    except ValueError as exc:
        assert "feature approved_direction missing required field: source_plan_artifact" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid feature approved_direction shape")



def test_init_rerun_rejects_malformed_persisted_artifact_missing_questions(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    broken = read_json(init_path)
    broken.pop("questions")
    init_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "init", "개인용 운동 코칭 앱 MVP", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "init missing required field: questions" in result.stderr



def test_init_rerun_rejects_malformed_persisted_artifact_invalid_question_shape(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    broken = read_json(init_path)
    broken["questions"] = [{"id": "project_name", "question": "이름?"}]
    init_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "init", "개인용 운동 코칭 앱 MVP", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "init questions[0] missing required field: target_doc" in result.stderr



def test_plan_rerun_rejects_malformed_persisted_artifact_wrong_approved_type(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "plan", "결제 기능 작업 분해", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    plan_path = workspace / payload["artifacts"][0]

    broken = read_json(plan_path)
    broken["approved"] = "yes"
    plan_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "plan", "결제 기능 작업 분해", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "plan field 'approved' must be of type bool" in result.stderr



def test_plan_rerun_rejects_malformed_persisted_artifact_invalid_options_shape(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "plan", "결제 기능 작업 분해", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    plan_path = workspace / payload["artifacts"][0]

    broken = read_json(plan_path)
    broken["options"] = {"Option A": "가장 작은 MVP 접근"}
    plan_path.write_text(json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "plan", "결제 기능 작업 분해", "--dry-run"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "plan options['Option A'] must be a list[str]" in result.stderr
