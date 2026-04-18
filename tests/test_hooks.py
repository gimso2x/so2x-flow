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
            "tool_response": "Approved Direction\nImplementation Slice\nVerification\n",
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
            "Approved Direction",
            "Implementation Slice",
            "Out of Scope",
            "Proposed Steps",
            "- first",
            "- second",
            "- third",
            "Verification",
            "Review Gate",
            "Follow-up Slice",
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
            "Approved Direction",
            "Implementation Slice",
            "Out of Scope",
            "Proposed Steps",
            "- first",
            "- second",
            "- third",
            "Verification",
            "Review Gate",
            "Follow-up Slice",
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
