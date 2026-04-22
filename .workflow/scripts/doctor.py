#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_ROOT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from artifact_schema import validate_artifact, write_json

OUTPUTS_ROOT = WORKFLOW_ROOT / "outputs"
STATUS_OUTPUT_PATH = OUTPUTS_ROOT / "doctor" / "status.json"
TASK_MODES = ("init", "plan", "feature", "qa", "review", "evaluate")
OUTPUT_MODES = TASK_MODES + ("doctor",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="so2x-flow doctor status entrypoint")
    parser.add_argument("--json", action="store_true", help="Print only the refreshed status JSON path")
    parser.add_argument("--brief", action="store_true", help="Print a one-line status summary")
    return parser.parse_args()


def relpath(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def newest_json(path: Path, *, skip_names: set[str] | None = None) -> Path | None:
    skip_names = skip_names or set()
    candidates = [item for item in path.glob("*.json") if item.is_file() and item.name not in skip_names]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.stat().st_mtime_ns, item.name))


def load_json(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))



def latest_approved_plan_path(latest_tasks: dict[str, str]) -> str | None:
    latest_plan = latest_tasks.get("plan")
    if not latest_plan:
        return None
    plan_payload = load_json(PROJECT_ROOT / latest_plan)
    if plan_payload and (plan_payload.get("approved") is True or plan_payload.get("status") == "approved"):
        return latest_plan
    return None



def approval_surface(latest_payload: dict | None, latest_tasks: dict[str, str]) -> tuple[str, str | None]:
    approved_plan = latest_approved_plan_path(latest_tasks)
    if approved_plan is not None:
        return "approved", approved_plan
    latest_plan = latest_tasks.get("plan")
    if latest_plan:
        plan_payload = load_json(PROJECT_ROOT / latest_plan)
        if plan_payload:
            if plan_payload.get("approved") is not True and plan_payload.get("status") != "approved":
                if latest_payload and latest_payload.get("approved_plan_path"):
                    return "matched-unapproved-plan", None
                return "waiting", None
    if latest_payload and latest_payload.get("approved_plan_path"):
        return "matched-unapproved-plan", None
    return "none", None



def runner_surface(latest_payload: dict | None) -> dict | None:
    if latest_payload is None:
        return None
    requested_runner = latest_payload.get("requested_runner")
    selected_runner = latest_payload.get("selected_runner")
    fallback_used = latest_payload.get("fallback_used")
    if not isinstance(requested_runner, str) or not isinstance(selected_runner, str) or not isinstance(fallback_used, bool):
        return None
    return {
        "requested_runner": requested_runner,
        "selected_runner": selected_runner,
        "fallback_used": fallback_used,
        "fallback_reason": latest_payload.get("fallback_reason"),
        "execution_mode": "dry_run" if latest_payload.get("dry_run") else "live",
    }



def suggested_next_command(overall_status: str, exact_status: str, approval_status: str) -> str:
    if exact_status == "idle":
        return "/flow-init"
    if exact_status == "waiting:init":
        return "/flow-init"
    if exact_status == "ok:init":
        return "/flow-plan"
    if exact_status == "waiting:approval" or approval_status in {"waiting", "matched-unapproved-plan"}:
        return "/flow-plan"
    if overall_status == "blocked":
        return "check doctor/output and fix blocked stage"
    if approval_status == "approved":
        return "/simplify"
    return "/flow-feature"



def summarize_latest(latest_payload: dict | None, latest_tasks: dict[str, str]) -> tuple[str, str | None, str, str]:
    latest_init = latest_tasks.get("init")
    latest_init_payload = load_json(PROJECT_ROOT / latest_init) if latest_init else None
    if latest_init_payload and latest_init_payload.get("status") == "ready_for_review":
        request = latest_init_payload.get("title") or "(unknown request)"
        return (f"init ready for review: {request}", None, "ok", "ok:init")
    if latest_payload is None:
        if latest_init:
            init_payload = latest_init_payload
            if (init_payload or {}).get("status") in {"draft_auto_filled", "needs_user_input", "in_progress"}:
                return ("Init questionnaire is waiting for user input.", None, "waiting", "waiting:init")
        latest_plan = latest_tasks.get("plan")
        if latest_plan:
            plan_payload = load_json(PROJECT_ROOT / latest_plan)
            if plan_payload and not plan_payload.get("approved") and plan_payload.get("status") != "approved":
                request = plan_payload.get("request") or "(unknown request)"
                return (f"Plan approval is waiting: {request}", None, "waiting", "waiting:approval")
        return ("No flow outputs yet.", None, "idle", "idle")

    mode = latest_payload.get("mode") or "unknown"
    request = latest_payload.get("request") or "(unknown request)"
    failure_message = latest_payload.get("failure_message")
    failed_stage = latest_payload.get("failed_stage")
    if failure_message:
        summary = f"{mode} blocked on {failed_stage or 'unknown stage'}: {request}"
        exact_status = f"blocked:{failed_stage}" if failed_stage else f"blocked:{mode}"
        return (summary, failure_message, "blocked", exact_status)

    role_results = latest_payload.get("role_results") or []
    if latest_payload.get("dry_run"):
        role_summary = ", ".join(f"{item['role']}={item['status']}" for item in role_results) or "no roles"
        return (f"{mode} dry-run ready: {request} [{role_summary}]", None, "ok", f"ok:{mode}")
    return (f"{mode} ready: {request}", None, "ok", f"ok:{mode}")


def collect_latest_outputs() -> tuple[dict[str, str], dict | None, Path | None]:
    latest_by_mode: dict[str, str] = {}
    latest_payload = None
    latest_path = None
    latest_timestamp = None
    for mode in OUTPUT_MODES:
        candidate = newest_json(OUTPUTS_ROOT / mode)
        if candidate is None:
            continue
        latest_by_mode[mode] = relpath(candidate)
        candidate_timestamp = candidate.stat().st_mtime_ns
        if latest_timestamp is None or (candidate_timestamp, candidate.name) > (latest_timestamp, latest_path.name if latest_path else ""):
            latest_timestamp = candidate_timestamp
            latest_path = candidate
            latest_payload = load_json(candidate)
    return latest_by_mode, latest_payload, latest_path


def collect_latest_tasks() -> dict[str, str]:
    latest_tasks: dict[str, str] = {}
    tasks_root = WORKFLOW_ROOT / "tasks"
    for mode in TASK_MODES:
        candidate = newest_json(tasks_root / mode, skip_names={"_template.json"})
        if candidate is None:
            continue
        latest_tasks[mode] = relpath(candidate)
    return latest_tasks


def build_status_payload() -> dict:
    latest_outputs, latest_payload, latest_output_path = collect_latest_outputs()
    latest_outputs.setdefault("doctor", relpath(STATUS_OUTPUT_PATH))
    latest_tasks = collect_latest_tasks()
    latest_summary, blocked_reason, overall_status, exact_status = summarize_latest(latest_payload, latest_tasks)
    approval_status, approved_plan_path = approval_surface(latest_payload, latest_tasks)
    latest_resolution = runner_surface(latest_payload)
    next_command = suggested_next_command(overall_status, exact_status, approval_status)
    payload = validate_artifact(
        "doctor",
        {
            "mode": "doctor",
            "overall_status": overall_status,
            "exact_status": exact_status,
            "blocked_reason": blocked_reason,
            "latest_summary": latest_summary,
            "latest_output_json": relpath(latest_output_path) if latest_output_path else None,
            "latest_outputs": latest_outputs,
            "latest_tasks": latest_tasks,
            "approval_status": approval_status,
            "latest_approved_plan_path": approved_plan_path,
            "latest_runner_resolution": latest_resolution,
            "suggested_next_command": next_command,
        },
    )
    if latest_payload is not None:
        payload["last_event"] = {
            "mode": latest_payload.get("mode"),
            "request": latest_payload.get("request"),
            "dry_run": latest_payload.get("dry_run"),
            "failed_stage": latest_payload.get("failed_stage"),
            "failed_role": latest_payload.get("failed_role"),
            "failure_message": latest_payload.get("failure_message"),
            "artifacts": latest_payload.get("artifacts") or [],
            "output_json": latest_payload.get("output_json") or (relpath(latest_output_path) if latest_output_path else None),
        }
    return validate_artifact("doctor", payload)


def print_summary(payload: dict) -> None:
    print(f"overall_status: {payload['overall_status']}")
    print(f"exact_status: {payload['exact_status']}")
    print(f"blocked_reason: {payload['blocked_reason'] or '(none)'}")
    print(f"approval_status: {payload['approval_status']}")
    print(f"latest_approved_plan_path: {payload['latest_approved_plan_path'] or '(none)'}")
    print(f"suggested_next_command: {payload['suggested_next_command']}")
    print(f"latest_summary: {payload['latest_summary']}")
    print(f"latest_output_json: {payload['latest_output_json'] or '(none)'}")
    resolution = payload.get("latest_runner_resolution")
    if resolution is None:
        print("latest_runner_resolution: (none)")
    else:
        print("latest_runner_resolution:")
        print(f"  requested_runner: {resolution['requested_runner']}")
        print(f"  selected_runner: {resolution['selected_runner']}")
        print(f"  fallback_used: {resolution['fallback_used']}")
        print(f"  fallback_reason: {resolution['fallback_reason'] or '(none)'}")
        print(f"  execution_mode: {resolution['execution_mode']}")
    print("latest_outputs:")
    for mode in sorted(payload["latest_outputs"]):
        print(f"  - {mode}: {payload['latest_outputs'][mode]}")
    print("latest_tasks:")
    for mode in sorted(payload["latest_tasks"]):
        print(f"  - {mode}: {payload['latest_tasks'][mode]}")
    print(f"output_json: {relpath(STATUS_OUTPUT_PATH)}")



def print_brief(payload: dict) -> None:
    blocked_reason = payload["blocked_reason"]
    suffix = f" | {blocked_reason}" if blocked_reason else ""
    print(f"{payload['exact_status']} | {payload['latest_summary']} | next={payload['suggested_next_command']}{suffix}")

def main() -> int:
    args = parse_args()
    payload = build_status_payload()
    STATUS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(STATUS_OUTPUT_PATH, payload)
    if args.json:
        print(relpath(STATUS_OUTPUT_PATH))
    elif args.brief:
        print_brief(payload)
    else:
        print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
