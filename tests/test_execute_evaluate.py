from pathlib import Path

from execute_helpers import make_workspace, output_path, read_json, run_execute



def test_evaluate_dry_run_uses_reviewer_only_and_creates_task(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_execute(workspace, "evaluate", "로그인 기능 readiness 점검", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["mode"] == "evaluate"
    assert payload["roles"] == ["reviewer"]
    assert payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert payload["artifacts"] == [".workflow/tasks/evaluate/로그인-기능-readiness-점검.json"]

    task_json = read_json(workspace / payload["artifacts"][0])
    assert task_json["mechanical_status"] == "pending"
    assert task_json["semantic_status"] == "pending"
    assert task_json["release_readiness"] == "hold"
    assert task_json["recommended_next_step"] == "/flow-review 또는 /flow-fix로 후속 조치를 진행할까요? (y/n)"



def test_evaluate_mode_collects_related_task_document_when_passed_via_task_option(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    feature_result = run_execute(workspace, "feature", "세션 만료 처리", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    task_relpath = feature_payload["artifacts"][0]

    evaluate_result = run_execute(workspace, "evaluate", "세션 만료 처리 readiness", "--task", task_relpath, "--dry-run")
    evaluate_payload = read_json(output_path(workspace, evaluate_result.stdout, "output_json"))

    assert task_relpath in evaluate_payload["docs_used"]
    evaluate_json = read_json(workspace / evaluate_payload["artifacts"][0])
    assert evaluate_json["related_task"] == task_relpath
