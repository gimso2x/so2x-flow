import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from execute_helpers import make_workspace, output_path, run_execute


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_doctor(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    doctor = workspace / ".workflow" / "scripts" / "doctor.py"
    return subprocess.run(
        [sys.executable, str(doctor), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )


def test_doctor_reports_idle_when_no_flow_outputs_exist(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["mode"] == "doctor"
    assert payload["overall_status"] == "idle"
    assert payload["exact_status"] == "idle"
    assert payload["blocked_reason"] is None
    assert payload["latest_summary"] == "No flow outputs yet."
    assert payload["latest_output_json"] is None
    assert payload["latest_outputs"] == {"doctor": ".workflow/outputs/doctor/status.json"}
    assert payload["latest_tasks"] == {}
    assert payload["approval_status"] == "none"
    assert payload["latest_approved_plan_path"] is None
    assert payload["latest_runner_resolution"] is None
    assert payload["suggested_next_command"] == "/flow-init"



def test_doctor_reports_waiting_init_without_outputs(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "init", "샘플 앱 초기 설정", "--dry-run")
    output = workspace / ".workflow" / "outputs" / "init" / "샘플-앱-초기-설정.json"
    output.unlink()

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["overall_status"] == "waiting"
    assert payload["exact_status"] == "waiting:init"
    assert payload["latest_summary"] == "Init questionnaire is waiting for user input."
    assert payload["latest_output_json"] is None
    assert payload["latest_tasks"]["init"] == ".workflow/tasks/init/샘플-앱-초기-설정.json"



def test_doctor_reports_waiting_plan_approval_without_outputs(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    output = workspace / ".workflow" / "outputs" / "plan" / "로그인-기능-설계-확정.json"
    output.unlink()

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["overall_status"] == "waiting"
    assert payload["exact_status"] == "waiting:approval"
    assert payload["latest_summary"] == "Plan approval is waiting: 로그인 기능 설계 확정"
    assert payload["latest_tasks"]["plan"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"



def test_doctor_reports_init_ready_for_review_surface_and_next_step(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    init_path = workspace / ".workflow" / "tasks" / "init" / "개인용-운동-코칭-앱-mvp.json"
    init_json = read_json(init_path)
    init_json["selected_init_mode"] = "auto-fill-now"
    init_json["answers"] = {
        "project_name": "개인용 운동 코칭 앱 MVP",
        "goal": "개인용 운동 코칭 앱 MVP",
        "users": "혼자 운동하는 사용자",
        "scope": "운동 기록과 루틴 관리",
        "out_of_scope": "커뮤니티 기능",
        "architecture": "Next.js 단일 앱",
        "qa": "운동 기록 저장 시나리오",
        "design": "미니멀한 모바일 UX",
    }
    init_path.write_text(json.dumps(init_json, ensure_ascii=False, indent=2), encoding="utf-8")
    run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["overall_status"] == "ok"
    assert payload["exact_status"] == "ok:init"
    assert payload["blocked_reason"] is None
    assert payload["latest_summary"] == "init ready for review: 개인용 운동 코칭 앱 MVP"
    assert payload["latest_output_json"] == ".workflow/outputs/init/개인용-운동-코칭-앱-mvp.json"
    assert payload["latest_tasks"]["init"] == ".workflow/tasks/init/개인용-운동-코칭-앱-mvp.json"
    assert payload["suggested_next_command"] == "/flow-plan"



def test_doctor_reports_latest_success_surface_and_task_links(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["overall_status"] == "ok"
    assert payload["exact_status"] == "ok:feature"
    assert payload["blocked_reason"] is None
    assert payload["latest_output_json"] == ".workflow/outputs/feature/로그인-기능-구현.json"
    assert payload["latest_outputs"]["feature"] == ".workflow/outputs/feature/로그인-기능-구현.json"
    assert payload["latest_outputs"]["plan"] == ".workflow/outputs/plan/로그인-기능-설계-확정.json"
    assert payload["latest_tasks"]["feature"] == ".workflow/tasks/feature/로그인-기능-구현.json"
    assert payload["latest_tasks"]["plan"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert payload["approval_status"] == "matched-unapproved-plan"
    assert payload["latest_approved_plan_path"] is None
    assert payload["latest_runner_resolution"] == {
        "requested_runner": "auto",
        "selected_runner": "ccs",
        "fallback_used": False,
        "fallback_reason": None,
        "execution_mode": "dry_run",
    }
    assert payload["suggested_next_command"] == "/flow-plan"
    assert payload["latest_summary"].startswith("feature dry-run ready: 로그인 기능 구현")
    assert payload["last_event"]["request"] == "로그인 기능 구현"
    assert payload["last_event"]["output_json"] == ".workflow/outputs/feature/로그인-기능-구현.json"



def test_doctor_reports_blocked_reason_from_latest_failed_output(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    broken = workspace / ".workflow" / "outputs" / "feature" / "세션-만료-처리.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text(
        json.dumps(
            {
                "mode": "feature",
                "request": "세션 만료 처리",
                "dry_run": False,
                "failed_stage": "implementer",
                "failed_role": "implementer",
                "failure_message": "tests failed",
                "artifacts": [".workflow/tasks/feature/세션-만료-처리.json"],
                "output_json": ".workflow/outputs/feature/세션-만료-처리.json",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["overall_status"] == "blocked"
    assert payload["exact_status"] == "blocked:implementer"
    assert payload["blocked_reason"] == "tests failed"
    assert payload["latest_output_json"] == ".workflow/outputs/feature/세션-만료-처리.json"
    assert payload["latest_summary"] == "feature blocked on implementer: 세션 만료 처리"
    assert payload["last_event"]["failed_role"] == "implementer"
    assert payload["last_event"]["failure_message"] == "tests failed"



def test_doctor_brief_and_json_modes_emit_machine_friendly_output(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "plan", "로그인 기능 설계 확정", "--dry-run")
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    brief = run_doctor(workspace, "--brief")
    json_only = run_doctor(workspace, "--json")

    assert brief.stdout.strip().startswith("ok:feature | feature dry-run ready: 로그인 기능 구현")
    assert "| next=/flow-plan" in brief.stdout.strip()
    assert json_only.stdout.strip() == ".workflow/outputs/doctor/status.json"



def test_doctor_reports_approved_plan_surface_for_live_feature_output(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "프로필 편집 설계 확정", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_output = workspace / ".workflow" / "outputs" / "feature" / "프로필-편집.json"
    feature_output.parent.mkdir(parents=True, exist_ok=True)
    feature_output.write_text(
        json.dumps(
            {
                "mode": "feature",
                "request": "프로필 편집",
                "dry_run": False,
                "requested_runner": "auto",
                "selected_runner": "claude",
                "fallback_used": True,
                "fallback_reason": "ccs profile missing",
                "approved_plan_path": ".workflow/tasks/plan/프로필-편집-설계-확정.json",
                "approved_plan_match_reason": "matched plan similarity exact slug via artifact request",
                "docs_used": [".workflow/docs/PRD.md"],
                "roles": ["planner", "implementer", "reviewer"],
                "role_results": [],
                "artifacts": [".workflow/tasks/feature/프로필-편집.json"],
                "output_json": ".workflow/outputs/feature/프로필-편집.json",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_doctor(workspace)
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["approval_status"] == "approved"
    assert payload["latest_approved_plan_path"] == ".workflow/tasks/plan/프로필-편집-설계-확정.json"
    assert payload["latest_runner_resolution"] == {
        "requested_runner": "auto",
        "selected_runner": "claude",
        "fallback_used": True,
        "fallback_reason": "ccs profile missing",
        "execution_mode": "live",
    }
    assert payload["suggested_next_command"] == "/simplify"



def test_doctor_artifact_schema_rejects_invalid_overall_status(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    task_artifacts = workspace / ".workflow" / "scripts" / "task_artifacts.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_task_artifacts", task_artifacts)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    invalid_doctor = {
        "mode": "doctor",
        "overall_status": "broken",
        "exact_status": "ok:feature",
        "blocked_reason": None,
        "latest_summary": "summary",
        "latest_output_json": None,
        "latest_outputs": {"doctor": ".workflow/outputs/doctor/status.json"},
        "latest_tasks": {},
        "approval_status": "none",
        "latest_approved_plan_path": None,
        "latest_runner_resolution": None,
        "suggested_next_command": "/flow-init",
    }

    try:
        module.validate_artifact("doctor", invalid_doctor)
    except ValueError as exc:
        assert "doctor field 'overall_status' must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid doctor overall_status")


def test_cleanup_fixture_removes_generated_outputs_and_non_template_tasks(tmp_path: Path):
    generated_output = ROOT / ".workflow" / "outputs" / "doctor" / "status.json"
    generated_output.parent.mkdir(parents=True, exist_ok=True)
    generated_output.write_text("{}", encoding="utf-8")

    generated_review = ROOT / ".workflow" / "tasks" / "review" / "generated-review.json"
    generated_review.parent.mkdir(parents=True, exist_ok=True)
    generated_review.write_text("{}", encoding="utf-8")

    from conftest import _cleanup_generated_files

    _cleanup_generated_files()

    assert not generated_output.exists()
    assert not generated_review.exists()
    assert (ROOT / ".workflow" / "tasks" / "feature" / "_template.json").exists()
