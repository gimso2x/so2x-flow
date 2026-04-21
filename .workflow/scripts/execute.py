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

from ccs_runner import resolve_runner
from doctor import build_status_payload, print_summary as print_doctor_summary
from execution_runtime import ExecutionFailure, run_roles, validate_runtime_config
from mode_handlers import prepare_mode_context
from payloads import build_payload, print_summary
from prompt_builder import load_text
from task_artifacts import save_task_payload

CONFIG_PATH = WORKFLOW_ROOT / "config" / "ccs-map.yaml"
PLAN_TASKS = WORKFLOW_ROOT / "tasks" / "plan"
PROMPTS_DIR = WORKFLOW_ROOT / "prompts"

MODE_ALIASES = {
    "flow-fix": "qa",
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
    ".claude/skills/flow-fix.md",
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
    ".workflow/scripts/hooks/validate-output.sh",
    ".workflow/scripts/hooks/tool-output-truncator.sh",
    ".workflow/scripts/hooks/edit-error-recovery.sh",
    ".workflow/scripts/hooks/tool-failure-tracker.sh",
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
    parser.add_argument("mode", choices=["init", "feature", "qa", "qa-fix", "flow-fix", "review", "plan", "plan-only", "doctor"])
    parser.add_argument("request", nargs="?", default="doctor status")
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


def collect_artifacts_for_mode(mode: str, bootstrap_artifacts: list[str], context) -> list[str]:
    if mode == "init":
        return list(context.artifacts)
    artifacts = list(bootstrap_artifacts)
    artifacts.extend(context.artifacts)
    return artifacts


def persist_and_print(payload: dict) -> None:
    json_path = save_task_payload(PROJECT_ROOT, payload)
    if json_path is not None:
        payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    print_summary(payload)


def persist_and_print_doctor(payload: dict) -> None:
    json_path = save_task_payload(PROJECT_ROOT, payload)
    if json_path is not None:
        payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    print_doctor_summary(payload)


def main() -> int:
    args = parse_args()
    mode = canonical_mode(args.mode)
    if mode == "doctor":
        payload = build_status_payload()
        persist_and_print_doctor(payload)
        return 0
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
        dry_run=args.dry_run,
        load_text=load_text,
    )
    artifacts = collect_artifacts_for_mode(mode, bootstrap_artifacts, context)
    runtime_config = config.get("runtime", {})
    validate_runtime_config(runtime_config, dry_run=args.dry_run)
    resolution = resolve_runner(runtime_config.get("runner", "auto"))

    try:
        role_results = run_roles(
            config=config,
            resolution=resolution,
            runtime_config=runtime_config,
            prompts_dir=PROMPTS_DIR,
            mode=mode,
            request=args.request,
            context=context,
            qa_id=args.qa_id,
            dry_run=args.dry_run,
        )
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
        persist_and_print(payload)
        return 0
    except ExecutionFailure as exc:
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
            role_results=exc.role_results,
            artifacts=artifacts,
            failed_role=exc.role,
            failed_stage=exc.stage,
            failure_message=exc.message,
        )
        persist_and_print(payload)
        raise SystemExit(exc.message)


if __name__ == "__main__":
    raise SystemExit(main())
