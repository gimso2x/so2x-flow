from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from task_artifacts import (
    render_feature_task,
    render_init_task,
    render_plan_doc,
    render_qa_task,
    render_review_task,
    write_initial_task,
    write_plan_task,
)
from workflow_context import select_approved_plan, slugify
from workflow_docs import collect_docs, load_docs_bundle


@dataclass
class ModeContext:
    docs_used: list[str]
    docs_bundle: str
    design_doc: str | None
    roles: list[str]
    planner_output: str | None
    task_path: str | None
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
    load_text,
) -> ModeContext:
    docs_used, design_doc = collect_docs(project_root, workflow_root, mode, docs, task, with_design)
    docs_bundle = load_docs_bundle(project_root, docs_used, load_text)
    configured_roles = config["modes"][mode]["roles"]
    skip_roles = {"planner", "qa_planner"} if skip_plan else set()
    roles = [] if mode == "init" else [role for role in configured_roles if role not in skip_roles]
    planner_output = None
    task_path = None
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
        task_path = f".workflow/tasks/feature/{slugify(request)}.json"
        path = project_root / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_feature_task(request, approved_plan_path), ensure_ascii=False, indent=2), encoding='utf-8')
        artifacts.append(task_path)
    elif mode == "init":
        task_path = f".workflow/tasks/init/{slugify(request)}.json"
        path = project_root / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_initial_task(path, render_init_task(request), preserve_existing=True)
        artifacts = [task_path]
        roles = []
    elif mode == "qa":
        task_path = f".workflow/tasks/qa/{slugify(request)}.json"
        path = project_root / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_qa_task(request, qa_id), ensure_ascii=False, indent=2), encoding='utf-8')
        artifacts.append(task_path)
    elif mode == "plan":
        task_path = f".workflow/tasks/plan/{slugify(request)}.json"
        path = project_root / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_plan_task(path, render_plan_doc(request, docs_used))
        artifacts.append(task_path)
    elif mode == "review":
        task_path = f".workflow/tasks/review/{slugify(request)}.json"
        path = project_root / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_review_task(request, docs_used, task), ensure_ascii=False, indent=2), encoding='utf-8')
        artifacts.append(task_path)

    return ModeContext(
        docs_used=docs_used,
        docs_bundle=docs_bundle,
        design_doc=design_doc,
        roles=roles,
        planner_output=planner_output,
        task_path=task_path,
        artifacts=artifacts,
        approved_plan_path=approved_plan_path,
        approved_plan_match_reason=approved_plan_match_reason,
    )
