#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_ROOT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ccs_runner import resolve_role_runner, resolve_runner, run_role, run_role_subprocess
from task_artifacts import (
    render_feature_task,
    render_init_task,
    render_plan_doc,
    render_qa_task,
    render_review_task,
    save_task_payload,
    write_initial_task,
    write_plan_task,
)
from workflow_context import (
    collect_docs,
    load_docs_bundle,
    select_approved_plan,
    slugify,
)

CONFIG_PATH = WORKFLOW_ROOT / "config" / "ccs-map.yaml"
PLAN_TASKS = WORKFLOW_ROOT / "tasks" / "plan"
PROMPTS_DIR = WORKFLOW_ROOT / "prompts"

MODE_ALIASES = {
    "qa-fix": "qa",
    "plan-only": "plan",
}

BOOTSTRAP_ARTIFACTS = [
    "CLAUDE.md",
    "DESIGN.md",
    ".claude/settings.json",
    ".claude/skills/README.md",
    ".claude/skills/flow-init.md",
    ".claude/skills/flow-feature.md",
    ".claude/skills/flow-qa.md",
    ".claude/skills/flow-review.md",
    ".claude/skills/flow-plan.md",
    ".workflow/config/ccs-map.yaml",
    ".workflow/docs/PRD.md",
    ".workflow/docs/ARCHITECTURE.md",
    ".workflow/docs/ADR.md",
    ".workflow/docs/QA.md",
    ".workflow/prompts/planner.md",
    ".workflow/prompts/implementer.md",
    ".workflow/prompts/qa-planner.md",
    ".workflow/prompts/reviewer.md",
    ".workflow/tasks/feature/_template.json",
    ".workflow/tasks/qa/_template.json",
    ".workflow/scripts/hooks/tdd-guard.sh",
    ".workflow/scripts/hooks/dangerous-cmd-guard.sh",
    ".workflow/scripts/hooks/circuit-breaker.sh",
]

BOOTSTRAP_DIRS = [
    ".claude",
    ".claude/skills",
    ".workflow/config",
    ".workflow/docs",
    ".workflow/prompts",
    ".workflow/scripts/hooks",
    ".workflow/tasks/feature",
    ".workflow/tasks/init",
    ".workflow/tasks/qa",
    ".workflow/tasks/plan",
    ".workflow/tasks/review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="so2x-flow execution entrypoint")
    parser.add_argument("mode", choices=["init", "feature", "qa", "qa-fix", "review", "plan", "plan-only"])
    parser.add_argument("request")
    parser.add_argument("--task")
    parser.add_argument("--qa-id")
    parser.add_argument("--docs", nargs="*")
    parser.add_argument("--skip-plan", action="store_true")
    parser.add_argument("--with-design", action="store_true")
    parser.add_argument("--output-name")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def canonical_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode, mode)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"config not found: {CONFIG_PATH}")
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def ensure_bootstrap_files() -> list[str]:
    artifacts: list[str] = []
    for rel_dir in BOOTSTRAP_DIRS:
        (PROJECT_ROOT / rel_dir).mkdir(parents=True, exist_ok=True)
    for rel_path in BOOTSTRAP_ARTIFACTS:
        path = PROJECT_ROOT / rel_path
        if path.exists():
            artifacts.append(rel_path)
    return artifacts


def prompt_path_for_role(role: str) -> Path:
    mapping = {
        "planner": "planner.md",
        "implementer": "implementer.md",
        "qa_planner": "qa-planner.md",
        "reviewer": "reviewer.md",
    }
    return PROMPTS_DIR / mapping[role]


def load_prompt_template(role: str) -> str:
    return load_text(prompt_path_for_role(role))


def build_prompt(
    role: str,
    mode: str,
    request: str,
    docs_used: list[str],
    docs_bundle: str,
    task_path: str | None,
    qa_id: str | None,
    planner_output: str | None,
    design_doc: str | None,
    approved_plan_path: str | None = None,
    approved_plan_match_reason: str | None = None,
) -> str:
    prompt_template = load_prompt_template(role)
    lines = [
        f"role: {role}",
        f"mode: {mode}",
        f"request: {request}",
        f"docs_used: {', '.join(docs_used) if docs_used else '(none)'}",
        f"design_doc: {design_doc or '(none)'}",
        f"approved_plan_path: {approved_plan_path or '(none)'}",
        f"approved_plan_match_reason: {approved_plan_match_reason or '(none)'}",
        "",
        "prompt_template:",
        prompt_template.strip(),
        "",
        "docs_content:",
        docs_bundle,
    ]
    if task_path:
        task_file = PROJECT_ROOT / task_path
        lines.extend(["", f"task_path: {task_path}", "task_content:", load_text(task_file).strip()])
    if qa_id:
        lines.append(f"qa_id: {qa_id}")
    if planner_output:
        lines.extend(["", "planner_output:", planner_output])
    return "\n".join(lines)


def print_summary(payload: dict) -> None:
    print(f"mode: {payload['mode']}")
    print(f"request: {payload['request']}")
    print(f"dry_run: {payload['dry_run']}")
    print(f"requested_runner: {payload['requested_runner']}")
    print(f"selected_runner: {payload['selected_runner']}")
    print(f"fallback_used: {payload['fallback_used']}")
    print(f"fallback_reason: {payload['fallback_reason'] or '(none)'}")
    print(f"design_doc: {payload['design_doc'] or '(none)'}")
    print(f"approved_plan_path: {payload.get('approved_plan_path') or '(none)'}")
    print(f"approved_plan_match_reason: {payload.get('approved_plan_match_reason') or '(none)'}")
    print("docs_used:")
    for doc in payload["docs_used"]:
        print(f"  - {doc}")
    print("roles:")
    for item in payload["role_results"]:
        print(f"  - {item['role']} ({item['status']})")
    print("commands:")
    for item in payload["role_results"]:
        print(f"  - {item['role']}: {item['command_preview']}")
    print("role_fallbacks:")
    for item in payload["role_results"]:
        print(f"  - {item['role']}: {item.get('fallback_reason') or '(none)'}")
    print("role_outputs:")
    for item in payload["role_results"]:
        print(f"  - {item['role']} output:")
        if item["output"]:
            for line in item["output"].splitlines():
                print(f"    {line}")
        else:
            print("    ")
    print("artifacts:")
    for artifact in payload["artifacts"]:
        print(f"  - {artifact}")
    print(f"output_json: {payload['output_json']}")


def main() -> int:
    args = parse_args()
    mode = canonical_mode(args.mode)
    bootstrap_artifacts = ensure_bootstrap_files() if mode == "init" else []
    artifacts = list(bootstrap_artifacts) if mode == "init" else []
    config = load_config()
    docs_used, design_doc = collect_docs(PROJECT_ROOT, WORKFLOW_ROOT, mode, args.docs, args.task, args.with_design)
    docs_bundle = load_docs_bundle(PROJECT_ROOT, docs_used, load_text)
    configured_roles = config["modes"][mode]["roles"]
    skip_roles = {"planner", "qa_planner"} if args.skip_plan else set()
    roles = [] if mode == "init" else [role for role in configured_roles if role not in skip_roles]
    planner_output = None
    task_path = None
    approved_plan_path = None
    approved_plan_match_reason = None

    if mode == "feature":
        approved_plan_path, approved_plan_match_reason = select_approved_plan(PROJECT_ROOT, PLAN_TASKS, args.request, require_explicit_approval=args.skip_plan)
        if approved_plan_path and approved_plan_path not in docs_used:
            docs_used.append(approved_plan_path)
            docs_bundle = load_docs_bundle(PROJECT_ROOT, docs_used, load_text)
        if args.skip_plan and approved_plan_path is None:
            raise SystemExit("skip-plan requires an explicitly approved plan artifact; run /flow-plan, mark it approved, or omit --skip-plan")
        task_path = f".workflow/tasks/feature/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_feature_task(args.request, approved_plan_path), ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "init":
        task_path = f".workflow/tasks/init/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_initial_task(path, render_init_task(args.request), preserve_existing=True)
        artifacts = [task_path]
    elif mode == "qa":
        task_path = f".workflow/tasks/qa/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_qa_task(args.request, args.qa_id), ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "plan":
        task_path = f".workflow/tasks/plan/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_plan_task(path, render_plan_doc(args.request, docs_used))
        artifacts.append(task_path)
    elif mode == "review":
        task_path = f".workflow/tasks/review/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(render_review_task(args.request, docs_used, args.task), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        artifacts.append(task_path)

    runtime_config = config.get("runtime", {})
    allow_live_run_raw = runtime_config.get("allow_live_run", False)
    if not isinstance(allow_live_run_raw, bool):
        raise SystemExit("live execution blocked: runtime.allow_live_run must be a boolean true/false value")
    allow_live_run = allow_live_run_raw
    if not args.dry_run and not allow_live_run:
        raise SystemExit("live execution blocked: set runtime.allow_live_run=true or use --dry-run")
    resolution = resolve_runner(runtime_config.get("runner", "auto"))
    role_results = []
    for role in roles:
        requested_role_config = config["roles"][role][resolution.selected_runner]
        shared_role_config = {
            **config["roles"][role],
            **requested_role_config,
        }
        role_resolution = resolve_role_runner(
            requested_runner=resolution.selected_runner,
            role=role,
            role_config=shared_role_config,
            runtime_config=runtime_config,
        )
        active_role_config = config["roles"][role][role_resolution.selected_runner]
        shared_role_config = {
            **config["roles"][role],
            **active_role_config,
        }
        prompt = build_prompt(role, mode, args.request, docs_used, docs_bundle, task_path, args.qa_id, planner_output, design_doc, approved_plan_path, approved_plan_match_reason)
        if args.dry_run:
            result = run_role(
                runner=role_resolution.selected_runner,
                role=role,
                prompt=prompt,
                role_config=shared_role_config,
                runtime_config=runtime_config,
                dry_run=True,
                fallback_reason=role_resolution.fallback_reason,
            )
        else:
            result = run_role_subprocess(
                runner=role_resolution.selected_runner,
                role=role,
                prompt=prompt,
                role_config=shared_role_config,
                runtime_config=runtime_config,
                fallback_reason=role_resolution.fallback_reason,
            )
        role_results.append(
            {
                "role": result.role,
                "runner": result.runner,
                "engine": result.engine,
                "model": result.model,
                "status": result.status,
                "output": result.output,
                "command": result.command,
                "command_preview": result.command_preview,
                "fallback_reason": result.fallback_reason,
            }
        )
        if role in {"planner", "qa_planner"}:
            planner_output = result.output

    payload = {
        "mode": mode,
        "request": args.request,
        "dry_run": args.dry_run,
        "requested_runner": resolution.requested_runner,
        "selected_runner": resolution.selected_runner,
        "fallback_used": resolution.fallback_used,
        "fallback_reason": resolution.fallback_reason,
        "design_doc": design_doc,
        "approved_plan_path": approved_plan_path,
        "approved_plan_match_reason": approved_plan_match_reason,
        "docs_used": docs_used,
        "roles": roles,
        "role_results": role_results,
        "artifacts": artifacts,
        "output_json": artifacts[0] if artifacts and artifacts[0].endswith(".json") else "",
    }
    json_path = save_task_payload(PROJECT_ROOT, payload)
    if json_path is not None:
        payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
