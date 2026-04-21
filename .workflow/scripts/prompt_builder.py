from __future__ import annotations

from pathlib import Path

from workflow_contracts import contract_for_mode


def load_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def prompt_path_for_role(prompts_dir: Path, role: str) -> Path:
    mapping = {
        "planner": "planner.md",
        "implementer": "implementer.md",
        "qa_planner": "qa-planner.md",
        "reviewer": "reviewer.md",
    }
    return prompts_dir / mapping[role]


def load_prompt_template(prompts_dir: Path, role: str) -> str:
    return load_text(prompt_path_for_role(prompts_dir, role))


def build_prompt(
    *,
    prompts_dir: Path,
    role: str,
    mode: str,
    request: str,
    docs_used: list[str],
    docs_bundle: str,
    task_path: str | None,
    task_content: str | None,
    qa_id: str | None,
    prior_role: str | None,
    prior_role_output: str | None,
    design_doc: str | None,
    approved_plan_path: str | None = None,
    approved_plan_match_reason: str | None = None,
) -> str:
    prompt_template = load_prompt_template(prompts_dir, role)
    mode_contract = contract_for_mode(mode)
    required_markers = mode_contract.output_contract.markers if mode_contract.output_contract else ()
    lines = [
        f"role: {role}",
        f"mode: {mode}",
        f"artifact_kind: {mode_contract.artifact_kind}",
        f"request: {request}",
        f"docs_used: {', '.join(docs_used) if docs_used else '(none)'}",
        f"design_doc: {design_doc or '(none)'}",
        f"approved_plan_path: {approved_plan_path or '(none)'}",
        f"approved_plan_match_reason: {approved_plan_match_reason or '(none)'}",
        f"required_output_markers: {', '.join(required_markers) if required_markers else '(none)'}",
        "",
        "prompt_template:",
        prompt_template.strip(),
        "",
        "docs_content:",
        docs_bundle,
    ]
    if task_path:
        lines.extend(["", f"task_path: {task_path}", "task_content:", (task_content or "").strip()])
    if qa_id:
        lines.append(f"qa_id: {qa_id}")
    if prior_role_output:
        lines.extend(["", f"{prior_role}_output:", prior_role_output])
    return "\n".join(lines)
