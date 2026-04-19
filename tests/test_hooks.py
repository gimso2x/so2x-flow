import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / ".workflow" / "scripts" / "hooks"


def run_hook(name: str, payload: dict, *, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["sh", str(HOOKS_DIR / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd or ROOT,
        env=merged_env,
        check=True,
    )


def hook_context(result: subprocess.CompletedProcess[str]) -> str:
    assert result.stdout.strip(), "hook produced no output"
    payload = json.loads(result.stdout)
    return payload["hookSpecificOutput"]["additionalContext"]


def test_validate_output_hook_emits_validation_reminder_for_flow_feature() -> None:
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION REMINDER [flow-feature]" in context
    assert "Approved Direction" in context
    assert "Next Step Prompt" in context



def test_validate_output_hook_checks_skill_response_when_present() -> None:
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "tool_response": ".workflow/tasks/feature/payment-slice.json\nApproved Direction: use plan\nImplementation Slice:\n- build api\nVerification: run pytest\n",
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-feature]" in context
    assert "Out of Scope" in context
    assert "Next Step Prompt" in context



def test_validate_output_hook_warns_when_feature_without_plan_does_not_ask_flow_plan() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/feature/payment-slice.json",
            "Approved Direction: none yet",
            "Implementation Slice:",
            "- payment slice placeholder",
            "Out of Scope: refunds",
            "Proposed Steps",
            "- first",
            "- second",
            "- third",
            "Verification: pending plan approval",
            "Review Gate: wait for plan",
            "Follow-up Slice: later",
            "approved_plan_path: (none)",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-feature]" in context
    assert "flow-plan first" in context



def test_validate_output_hook_reports_checked_when_required_markers_exist() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/feature/payment-slice.json",
            "Approved Direction: use approved payment plan v1",
            "Implementation Slice:",
            "- add payment API adapter",
            "Out of Scope: refund flow",
            "Proposed Steps",
            "- first",
            "- second",
            "- third",
            "Verification:",
            "- pytest tests/test_payments.py -q",
            "Review Gate: reviewer sign-off after green tests",
            "Follow-up Slice: refund support later",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION CHECKED [flow-feature]" in context
    assert "VALIDATION WARNING" not in context



def test_validate_output_hook_warns_when_feature_section_is_empty() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/feature/payment-slice.json",
            "Approved Direction:",
            "Implementation Slice:",
            "- add payment API adapter",
            "Out of Scope: refund flow",
            "Proposed Steps",
            "- first",
            "- second",
            "- third",
            "Verification:",
            "- pytest tests/test_payments.py -q",
            "Review Gate: reviewer sign-off after green tests",
            "Follow-up Slice: refund support later",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-feature]" in context
    assert "Approved Direction section is empty" in context



def test_validate_output_hook_warns_when_feature_steps_are_too_short() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/feature/payment-slice.json",
            "Approved Direction: use approved payment plan v1",
            "Implementation Slice:",
            "- add payment API adapter",
            "Out of Scope: refund flow",
            "Proposed Steps",
            "- first",
            "- second",
            "Verification:",
            "- pytest tests/test_payments.py -q",
            "Review Gate: reviewer sign-off after green tests",
            "Follow-up Slice: refund support later",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-feature"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-feature]" in context
    assert "Proposed Steps has 2 items (< 3)" in context



def test_validate_output_hook_warns_when_canonical_artifact_path_is_missing() -> None:
    response = "\n".join(
        [
            "Context Snapshot",
            "Open Questions",
            "Options",
            "Recommendation",
            "Implementation Slices",
            "Verification Gates",
            "Draft Plan",
            "Approval Gate",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-plan"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-plan]" in context
    assert "canonical plan artifact path" in context



def test_validate_output_hook_checks_canonical_plan_artifact_path_when_present() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/plan/payment-breakdown.json",
            "Context Snapshot: payments need phase-1 scope",
            "Open Questions: none",
            "Options",
            "- keep sync calls",
            "- add queue",
            "Recommendation: choose queue-backed worker",
            "Implementation Slices",
            "- slice 1: queue producer",
            "Verification Gates: unit + smoke tests",
            "Draft Plan: implement producer before worker",
            "Approval Gate: approve queue direction",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-plan"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION CHECKED [flow-plan]" in context
    assert "VALIDATION WARNING" not in context



def test_validate_output_hook_warns_when_qa_section_is_empty() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/qa/qa-001.json",
            "Reproduction:",
            "Expected: save succeeds",
            "Actual: 500 error",
            "Root Cause Hypothesis: null config value",
            "Minimal Fix: guard empty config",
            "Verification: rerun failing test",
            "Residual Risk: broader config drift",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-qa"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-qa]" in context
    assert "Reproduction section is empty" in context



def test_validate_output_hook_warns_when_review_section_is_empty() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/review/payment-review.json",
            "Spec Gap: none",
            "Architecture Concern:",
            "Test Gap: missing retry test",
            "QA Watchpoints: retry queue saturation",
            "Security / Regression Risk: payment retries can duplicate",
            "Verdict: changes requested",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-review"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-review]" in context
    assert "Architecture Concern section is empty" in context



def test_validate_output_hook_warns_when_plan_options_are_too_thin() -> None:
    response = "\n".join(
        [
            ".workflow/tasks/plan/payment-breakdown.json",
            "Context Snapshot: payments need phase-1 scope",
            "Open Questions: none",
            "Options",
            "- only one option",
            "Recommendation: choose queue-backed worker",
            "Implementation Slices",
            "- slice 1: queue producer",
            "Verification Gates: unit + smoke tests",
            "Draft Plan: implement producer before worker",
            "Approval Gate: approve queue direction",
            "Next Step Prompt?",
        ]
    )
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "flow-plan"},
            "tool_response": response,
            "cwd": str(ROOT),
        },
        cwd=ROOT,
    )
    context = hook_context(result)
    assert "VALIDATION WARNING [flow-plan]" in context
    assert "Options has 1 items (< 2)" in context



def test_validate_output_hook_ignores_skills_without_validate_prompt(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills"
    skill_dir.mkdir(parents=True)
    (skill_dir / "plain-skill.md").write_text("# plain-skill\n", encoding="utf-8")
    result = run_hook(
        "validate-output.sh",
        {
            "tool_name": "Skill",
            "tool_input": {"skill": "plain-skill"},
            "cwd": str(tmp_path),
        },
        cwd=tmp_path,
    )
    assert result.stdout.strip() == ""



def test_tool_output_truncator_hook_adds_summary_for_large_output() -> None:
    large_output = "header\n" + ("x" * 13000) + "\nTraceback: boom\nfooter"
    result = run_hook(
        "tool-output-truncator.sh",
        {
            "tool_name": "Bash",
            "tool_response": large_output,
        },
    )
    context = hook_context(result)
    assert "Large Bash output detected" in context
    assert "SUMMARY ONLY" in context
    assert "Traceback: boom" in context



def test_edit_error_recovery_hook_emits_guidance() -> None:
    result = run_hook(
        "edit-error-recovery.sh",
        {
            "tool_name": "Edit",
            "error": "old_string not found in file",
        },
    )
    context = hook_context(result)
    assert "EDIT RECOVERY" in context
    assert "exact context" in context or "다시 읽고" in context



def test_tool_failure_tracker_escalates_after_repeated_failures(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path)}
    payload = {
        "session_id": "session-123",
        "tool_name": "Edit",
    }
    first = run_hook("tool-failure-tracker.sh", payload, env=env)
    second = run_hook("tool-failure-tracker.sh", payload, env=env)
    third = run_hook("tool-failure-tracker.sh", payload, env=env)
    assert first.stdout.strip() == ""
    assert second.stdout.strip() == ""
    context = hook_context(third)
    assert "REPEATED FAILURE" in context
    assert "Edit" in context
