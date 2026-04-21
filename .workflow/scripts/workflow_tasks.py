from __future__ import annotations

import json
from pathlib import Path

from artifact_renderers import (
    render_evaluate_task,
    render_feature_task,
    render_init_task,
    render_plan_doc,
    render_qa_task,
    render_review_task,
)
from artifact_store import write_initial_task, write_plan_task
from workflow_context import slugify


def write_feature_task(project_root: Path, request: str, approved_plan_path: str | None) -> str:
    task_path = f".workflow/tasks/feature/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_feature_task(request, approved_plan_path), ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def write_init_task(project_root: Path, request: str) -> str:
    task_path = f".workflow/tasks/init/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    write_initial_task(path, render_init_task(request), preserve_existing=True)
    return task_path


def write_qa_task(project_root: Path, request: str, qa_id: str | None) -> str:
    task_path = f".workflow/tasks/qa/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_qa_task(request, qa_id), ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def write_plan_mode_task(project_root: Path, request: str, docs_used: list[str]) -> str:
    task_path = f".workflow/tasks/plan/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    write_plan_task(path, render_plan_doc(request, docs_used))
    return task_path


def write_review_task(project_root: Path, request: str, docs_used: list[str], task: str | None) -> str:
    task_path = f".workflow/tasks/review/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_review_task(request, docs_used, task), ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def write_evaluate_task(project_root: Path, request: str, docs_used: list[str], task: str | None) -> str:
    task_path = f".workflow/tasks/evaluate/{slugify(request)}.json"
    path = project_root / task_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_evaluate_task(request, docs_used, task), ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path
