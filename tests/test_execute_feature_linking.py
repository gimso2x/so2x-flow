import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

from execute_helpers import make_sample_target_repo, make_workspace, output_path, read_json, run_execute

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
