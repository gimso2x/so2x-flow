import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

from execute_helpers import make_sample_target_repo, make_workspace, output_path, read_json, run_execute

def test_qa_dry_run_prioritizes_qa_doc_and_uses_qa_planner(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "flow-fix", "QA-001 홈 버튼 클릭 안됨", "--qa-id", "QA-001", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "qa"
    assert payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert [item["role"] for item in payload["role_results"]] == ["qa_planner", "implementer", "reviewer"]
    task_json = read_json(workspace / payload["artifacts"][0])
    assert task_json["reproduction"] == ["Describe how to reproduce the issue."]
    assert task_json["expected"] == ["Describe the intended behavior."]
    assert task_json["actual"] == ["Describe the current broken behavior."]
    assert task_json["minimal_fix"] == ["Describe the smallest safe repair."]
    assert "qa_id: QA-001" in payload["role_results"][1]["output"]
    assert "implementer_output:" in payload["role_results"][2]["output"]

def test_review_dry_run_uses_reviewer_only_and_includes_design_doc(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "review", "이번 변경 QA 관점 점검", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["mode"] == "review"
    assert payload["roles"] == ["reviewer"]
    assert payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert payload["design_doc"] == "DESIGN.md"
    assert payload["artifacts"] == [".workflow/tasks/review/이번-변경-qa-관점-점검.json"]

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
