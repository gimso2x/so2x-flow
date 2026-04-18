from __future__ import annotations

import subprocess
from dataclasses import dataclass

from runner_commands import build_runner_command, command_preview
from runner_resolution import RunnerError


DEFAULT_ROLE_TIMEOUT = 300
MAX_ERROR_OUTPUT_CHARS = 400


@dataclass
class RoleResult:
    role: str
    runner: str
    engine: str
    model: str
    status: str
    output: str
    command: list[str]
    command_preview: str
    fallback_reason: str | None = None


def timeout_for_role(role: str, runtime_config: dict | None = None) -> int:
    runtime = runtime_config or {}
    role_timeouts = runtime.get("role_timeouts") or {}
    if not isinstance(role_timeouts, dict):
        raise RunnerError("runtime.role_timeouts must be a mapping of role -> timeout seconds")
    timeout = role_timeouts.get(role, DEFAULT_ROLE_TIMEOUT)
    if not isinstance(timeout, int) or timeout <= 0:
        raise RunnerError(f"runtime.role_timeouts.{role} must be a positive integer")
    return timeout


def _format_output_snippet(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "(none)"
    if len(text) <= MAX_ERROR_OUTPUT_CHARS:
        return text
    return f"{text[:MAX_ERROR_OUTPUT_CHARS]}...(truncated {len(text) - MAX_ERROR_OUTPUT_CHARS} chars)"


def authentication_hint(runner: str, stderr: str | None) -> str | None:
    if runner != "ccs" or not stderr:
        return None
    lowered = stderr.lower()
    if "authentication required for openai codex" in lowered:
        return "ccs is installed but Codex auth is not configured; run `ccs setup` or `ccs codex --auth` and finish login before live run"
    return None


def run_role(
    *,
    runner: str,
    role: str,
    prompt: str,
    role_config: dict,
    runtime_config: dict | None = None,
    dry_run: bool,
    fallback_reason: str | None = None,
) -> RoleResult:
    command = build_runner_command(
        runner=runner,
        role=role,
        prompt=prompt,
        role_config=role_config,
        runtime_config=runtime_config,
    )
    preview = command_preview(command)
    engine = role_config.get("engine", role_config.get("claude_role", role))
    model = role_config.get("model", runner)
    if dry_run:
        output = f"[dry-run] runner={runner} role={role} engine={engine} model={model} command={preview}\n\n{prompt}"
        return RoleResult(role=role, runner=runner, engine=engine, model=model, status="dry-run", output=output, command=command, command_preview=preview, fallback_reason=fallback_reason)

    raise NotImplementedError(f"Live {runner} execution is not implemented yet for role={role}")


def run_role_subprocess(
    *,
    runner: str,
    role: str,
    prompt: str,
    role_config: dict,
    runtime_config: dict | None = None,
    timeout: int | None = None,
    fallback_reason: str | None = None,
) -> RoleResult:
    command = build_runner_command(
        runner=runner,
        role=role,
        prompt=prompt,
        role_config=role_config,
        runtime_config=runtime_config,
    )
    preview = command_preview(command)
    resolved_timeout = timeout if timeout is not None else timeout_for_role(role, runtime_config)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=resolved_timeout, check=True)
    except subprocess.TimeoutExpired:
        detail = f"runner={runner} role={role} timed out after {resolved_timeout}s: {preview}"
        if fallback_reason:
            detail = f"{detail}\nfallback_reason: {fallback_reason}"
        raise RunnerError(detail)
    except subprocess.CalledProcessError as exc:
        hint = authentication_hint(runner, exc.stderr)
        stdout = _format_output_snippet(getattr(exc, "output", None))
        stderr = _format_output_snippet(exc.stderr)
        detail = f"runner={runner} role={role} exited {exc.returncode}: {preview}\nstdout: {stdout}\nstderr: {stderr}"
        if fallback_reason:
            detail = f"{detail}\nfallback_reason: {fallback_reason}"
        if hint:
            detail = f"{detail}\nhint: {hint}"
        raise RunnerError(detail) from exc
    engine = role_config.get("engine", role_config.get("claude_role", role))
    model = role_config.get("model", runner)
    return RoleResult(role=role, runner=runner, engine=engine, model=model, status="success", output=completed.stdout, command=command, command_preview=preview, fallback_reason=fallback_reason)
