import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

from execute_helpers import make_sample_target_repo, make_workspace, output_path, read_json, run_execute

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


def test_init_dry_run_marks_ready_for_review_with_flow_plan_next_step_when_questions_finished(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    first = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    payload = read_json(output_path(workspace, first.stdout, "output_json"))
    init_path = workspace / payload["artifacts"][0]

    existing = read_json(init_path)
    existing["selected_init_mode"] = "auto-fill-now"
    existing["answers"] = {
        "project_name": "개인용 운동 코칭 앱 MVP",
        "goal": "개인용 운동 코칭 앱 MVP",
        "users": "혼자 운동하는 사용자",
        "scope": "운동 기록과 루틴 관리",
        "out_of_scope": "커뮤니티 기능",
        "architecture": "Next.js 단일 앱",
        "qa": "운동 기록 저장 시나리오",
        "design": "미니멀한 모바일 UX",
    }
    init_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    second = run_execute(workspace, "init", "개인용 운동 코칭 앱 MVP", "--dry-run")
    rerun_payload = read_json(output_path(workspace, second.stdout, "output_json"))
    rerun_json = read_json(workspace / rerun_payload["artifacts"][0])

    assert rerun_json["status"] == "ready_for_review"
    assert rerun_json["pending_questions"] == []
    assert rerun_json["current_question_id"] is None
    assert rerun_json["next_step_prompt"] == "init 초안이 준비됐습니다. 요구사항과 slice를 고정하려면 /flow-plan으로 이어가세요."
    assert "next_step_prompt: init 초안이 준비됐습니다. 요구사항과 slice를 고정하려면 /flow-plan으로 이어가세요." in second.stdout

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
