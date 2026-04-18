from __future__ import annotations

from ccs_runner import resolve_role_runner, run_role, run_role_subprocess
from prompt_builder import build_prompt


class ExecutionFailure(RuntimeError):
    def __init__(self, *, role: str, stage: str, message: str, role_results: list[dict]):
        super().__init__(message)
        self.role = role
        self.stage = stage
        self.message = message
        self.role_results = role_results



def validate_runtime_config(runtime_config: dict, *, dry_run: bool) -> bool:
    allow_live_run_raw = runtime_config.get("allow_live_run", False)
    if not isinstance(allow_live_run_raw, bool):
        raise SystemExit("live execution blocked: runtime.allow_live_run must be a boolean true/false value")
    allow_live_run = allow_live_run_raw
    if not dry_run and not allow_live_run:
        raise SystemExit("live execution blocked: set runtime.allow_live_run=true or use --dry-run")
    return allow_live_run



def _role_result_payload(result) -> dict:
    return {
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



def run_roles(*, config: dict, resolution, runtime_config: dict, prompts_dir, project_root, mode: str, request: str, context, qa_id: str | None, dry_run: bool) -> list[dict]:
    role_results: list[dict] = []
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
            prompts_dir=prompts_dir,
            project_root=project_root,
            role=role,
            mode=mode,
            request=request,
            docs_used=context.docs_used,
            docs_bundle=context.docs_bundle,
            task_path=context.task_path,
            qa_id=qa_id,
            planner_output=planner_output,
            design_doc=context.design_doc,
            approved_plan_path=context.approved_plan_path,
            approved_plan_match_reason=context.approved_plan_match_reason,
        )
        try:
            if dry_run:
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
        except Exception as exc:
            raise ExecutionFailure(role=role, stage="role_execution", message=str(exc), role_results=role_results) from exc
        role_results.append(_role_result_payload(result))
        if role in {"planner", "qa_planner"}:
            planner_output = result.output
    return role_results
