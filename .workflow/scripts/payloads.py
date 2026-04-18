from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_contracts import contract_for_mode


def build_payload(
    *,
    mode: str,
    request: str,
    dry_run: bool,
    resolution,
    design_doc: str | None,
    approved_plan_path: str | None,
    approved_plan_match_reason: str | None,
    docs_used: list[str],
    roles: list[str],
    role_results: list[dict],
    artifacts: list[str],
    failed_role: str | None = None,
    failed_stage: str | None = None,
    failure_message: str | None = None,
) -> dict:
    contract = contract_for_mode(mode)
    return {
        "mode": mode,
        "artifact_kind": contract.artifact_kind,
        "request": request,
        "dry_run": dry_run,
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
        "failed_role": failed_role,
        "failed_stage": failed_stage,
        "failure_message": failure_message,
        "output_json": "",
    }



def print_summary(payload: dict) -> None:
    print(f"mode: {payload['mode']}")
    print(f"artifact_kind: {payload['artifact_kind']}")
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
    if payload.get("failed_role"):
        print(f"failed_role: {payload['failed_role']}")
    if payload.get("failed_stage"):
        print(f"failed_stage: {payload['failed_stage']}")
    if payload.get("failure_message"):
        print(f"failure_message: {payload['failure_message']}")
    print(f"output_json: {payload['output_json']}")
