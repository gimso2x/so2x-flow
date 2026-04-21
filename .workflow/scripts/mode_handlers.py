from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workflow_context import select_approved_plan
from workflow_contracts import contract_for_mode
from workflow_docs import collect_docs, load_docs_bundle
from workflow_tasks import (
    write_feature_task,
    write_init_task,
    write_plan_mode_task,
    write_qa_task,
    write_review_task,
)


@dataclass
class ModeContext:
    docs_used: list[str]
    docs_bundle: str
    design_doc: str | None
    roles: list[str]
    task_path: str | None
    task_content: str | None
    artifacts: list[str]
    approved_plan_path: str | None
    approved_plan_match_reason: str | None


def prepare_mode_context(
    *,
    project_root: Path,
    workflow_root: Path,
    plan_tasks: Path,
    config: dict,
    mode: str,
    request: str,
    docs: list[str] | None,
    task: str | None,
    qa_id: str | None,
    skip_plan: bool,
    with_design: bool,
    dry_run: bool,
    load_text,
) -> ModeContext:
    docs_used, design_doc = collect_docs(project_root, workflow_root, mode, docs, task, with_design)
    docs_bundle = load_docs_bundle(project_root, docs_used, load_text)
    configured_roles = contract_for_mode(mode).roles
    skip_roles = {"planner", "qa_planner"} if skip_plan else set()
    roles = [] if mode == "init" else [role for role in configured_roles if role not in skip_roles]
    task_path = None
    task_content = None
    approved_plan_path = None
    approved_plan_match_reason = None
    artifacts: list[str] = []

    if mode == "feature":
        approved_plan_path, approved_plan_match_reason = select_approved_plan(
            project_root,
            plan_tasks,
            request,
            require_explicit_approval=skip_plan,
        )
        if approved_plan_path and approved_plan_path not in docs_used:
            docs_used.append(approved_plan_path)
            docs_bundle = load_docs_bundle(project_root, docs_used, load_text)
        if skip_plan and approved_plan_path is None:
            raise SystemExit("skip-plan requires an explicitly approved plan artifact; run /flow-plan, mark it approved, or omit --skip-plan")
        if not dry_run and approved_plan_path is None:
            raise SystemExit("feature live execution requires an explicitly approved plan artifact; run /flow-plan, mark it approved, or use --dry-run")
        task_path = write_feature_task(project_root, request, approved_plan_path)
        artifacts.append(task_path)
    elif mode == "init":
        task_path = write_init_task(project_root, request)
        artifacts = [task_path]
        roles = []
    elif mode == "qa":
        task_path = write_qa_task(project_root, request, qa_id)
        artifacts.append(task_path)
    elif mode == "plan":
        task_path = write_plan_mode_task(project_root, request, docs_used)
        artifacts.append(task_path)
    elif mode == "review":
        task_path = write_review_task(project_root, request, docs_used, task)
        artifacts.append(task_path)

    if task_path:
        task_content = load_text(project_root / task_path)

    return ModeContext(
        docs_used=docs_used,
        docs_bundle=docs_bundle,
        design_doc=design_doc,
        roles=roles,
        task_path=task_path,
        task_content=task_content,
        artifacts=artifacts,
        approved_plan_path=approved_plan_path,
        approved_plan_match_reason=approved_plan_match_reason,
    )
