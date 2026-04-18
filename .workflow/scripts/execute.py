#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_ROOT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ccs_runner import resolve_role_runner, resolve_runner, run_role, run_role_subprocess
from mode_handlers import prepare_mode_context
from payloads import build_payload, print_summary
from prompt_builder import build_prompt, load_text
from task_artifacts import save_task_payload

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


def ensure_bootstrap_files() -> list[str]:
    artifacts: list[str] = []
    for rel_dir in BOOTSTRAP_DIRS:
        (PROJECT_ROOT / rel_dir).mkdir(parents=True, exist_ok=True)
    for rel_path in BOOTSTRAP_ARTIFACTS:
        path = PROJECT_ROOT / rel_path
        if path.exists():
            artifacts.append(rel_path)
    return artifacts


def main() -> int:
    args = parse_args()
    mode = canonical_mode(args.mode)
    bootstrap_artifacts = ensure_bootstrap_files() if mode == "init" else []
    config = load_config()
    context = prepare_mode_context(
        project_root=PROJECT_ROOT,
        workflow_root=WORKFLOW_ROOT,
        plan_tasks=PLAN_TASKS,
        config=config,
        mode=mode,
        request=args.request,
        docs=args.docs,
        task=args.task,
        qa_id=args.qa_id,
        skip_plan=args.skip_plan,
        with_design=args.with_design,
        load_text=load_text,
    )
    artifacts = list(bootstrap_artifacts) if mode == "init" else []
    if mode == "init":
        artifacts = list(context.artifacts)
    else:
        artifacts.extend(context.artifacts)

    runtime_config = config.get("runtime", {})
    allow_live_run_raw = runtime_config.get("allow_live_run", False)
    if not isinstance(allow_live_run_raw, bool):
        raise SystemExit("live execution blocked: runtime.allow_live_run must be a boolean true/false value")
    allow_live_run = allow_live_run_raw
    if not args.dry_run and not allow_live_run:
        raise SystemExit("live execution blocked: set runtime.allow_live_run=true or use --dry-run")
    resolution = resolve_runner(runtime_config.get("runner", "auto"))
    role_results = []
    planner_output = context.planner_output
    for role in context.roles:
        requested_role_config = config["roles"][role][resolution.selected_runner]
        shared_role_config = {**config["roles"][role], **requested_role_config}
        role_resolution = resolve_role_runner(
            requested_runner=resolution.selected_runner,
            role=role,
            role_config=shared_role_config,
            runtime_config=runtime_config,
        )
        active_role_config = config["roles"][role][role_resolution.selected_runner]
        shared_role_config = {**config["roles"][role], **active_role_config}
        prompt = build_prompt(
            prompts_dir=PROMPTS_DIR,
            project_root=PROJECT_ROOT,
            role=role,
            mode=mode,
            request=args.request,
            docs_used=context.docs_used,
            docs_bundle=context.docs_bundle,
            task_path=context.task_path,
            qa_id=args.qa_id,
            planner_output=planner_output,
            design_doc=context.design_doc,
            approved_plan_path=context.approved_plan_path,
            approved_plan_match_reason=context.approved_plan_match_reason,
        )
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

    payload = build_payload(
        mode=mode,
        request=args.request,
        dry_run=args.dry_run,
        resolution=resolution,
        design_doc=context.design_doc,
        approved_plan_path=context.approved_plan_path,
        approved_plan_match_reason=context.approved_plan_match_reason,
        docs_used=context.docs_used,
        roles=context.roles,
        role_results=role_results,
        artifacts=artifacts,
    )
    json_path = save_task_payload(PROJECT_ROOT, payload)
    if json_path is not None:
        payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
