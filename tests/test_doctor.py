import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from test_execute import make_workspace, output_path, run_execute


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
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    brief = run_doctor(workspace, "--brief")
    json_only = run_doctor(workspace, "--json")

    assert brief.stdout.strip().startswith("ok:feature | feature dry-run ready: 로그인 기능 구현")
    assert json_only.stdout.strip() == ".workflow/outputs/doctor/status.json"



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
    }

    try:
        module.validate_artifact("doctor", invalid_doctor)
    except ValueError as exc:
        assert "doctor field 'overall_status' must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid doctor overall_status")
