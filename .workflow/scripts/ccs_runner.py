from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass


BUILTIN_CCS_PROFILES = {"codex", "claude"}


class RunnerError(RuntimeError):
    """Raised when a runner subprocess fails."""


@dataclass
class RunnerResolution:
    requested_runner: str
    selected_runner: str
    fallback_used: bool
    fallback_reason: str | None


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


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def resolve_runner(requested_runner: str, *, has_ccs: bool | None = None) -> RunnerResolution:
    ccs_available = has_ccs if has_ccs is not None else has_command("ccs")
    normalized = requested_runner or "auto"
    if normalized == "claude":
        return RunnerResolution(normalized, "claude", False, None)
    if normalized == "auto":
        if ccs_available:
            return RunnerResolution(normalized, "ccs", False, None)
        return RunnerResolution(normalized, "claude", True, "ccs not found in PATH")
    if normalized == "ccs":
        if ccs_available:
            return RunnerResolution(normalized, "ccs", False, None)
        return RunnerResolution(normalized, "claude", True, "ccs not found in PATH")
    raise ValueError(f"Unsupported runner: {requested_runner}")


def probe_ccs_profile(profile: str, command: str = "ccs") -> tuple[bool, str | None]:
    try:
        completed = subprocess.run([command, profile, "--help"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    combined = "\n".join(part for part in (stdout, stderr) if part).strip()
    if completed.returncode != 0 and f"Profile '{profile}' not found" in combined:
        return False, combined
    return True, combined or None


def is_missing_ccs_profile(profile: str, detail: str | None) -> bool:
    return bool(detail and f"Profile '{profile}' not found" in detail)


def resolve_role_runner(
    *,
    requested_runner: str,
    role: str,
    role_config: dict,
    runtime_config: dict | None = None,
    has_ccs: bool | None = None,
    has_claude: bool | None = None,
) -> RunnerResolution:
    runtime = runtime_config or {}
    base_resolution = resolve_runner(requested_runner, has_ccs=has_ccs)
    if base_resolution.selected_runner != "ccs":
        return base_resolution

    profile = role_config.get("ccs_profile") or role_config.get("profile")
    ccs_command = role_config.get("command", "ccs")
    if not profile or profile in BUILTIN_CCS_PROFILES:
        return base_resolution

    profile_ok, detail = probe_ccs_profile(profile, command=ccs_command)
    if profile_ok:
        return base_resolution
    if not is_missing_ccs_profile(profile, detail):
        raise RunnerError(f"role={role} ccs profile probe failed for '{profile}': {detail or 'unknown error'}")

    fallback_reason = f"role={role} profile '{profile}' is not available via ccs"
    if detail:
        fallback_reason = f"{fallback_reason}: {detail}"

    role_claude_config = role_config.get("claude", {}) if isinstance(role_config.get("claude"), dict) else {}
    claude_command = role_claude_config.get("command") or role_config.get("claude_command") or runtime.get("claude_command", "claude")
    claude_available = has_claude if has_claude is not None else has_command(claude_command)
    if claude_available:
        return RunnerResolution(base_resolution.requested_runner, "claude", True, fallback_reason)

    raise RunnerError(f"{fallback_reason}; claude fallback is unavailable ({claude_command})")


def build_ccs_command(role: str, prompt: str, role_config: dict) -> list[str]:
    profile = role_config.get("ccs_profile") or role_config.get("profile")
    target = profile or role_config.get("engine", role)
    command = [role_config.get("command", "ccs"), target]
    model = role_config.get("model")
    extra_args = role_config.get("extra_args", [])
    if model and model != target:
        command.extend(["--model", model])
    command.extend(extra_args)
    command.append(prompt)
    return command


def build_claude_command(role: str, prompt: str, role_config: dict, runtime_config: dict | None = None) -> list[str]:
    runtime = runtime_config or {}
    command = [role_config.get("command", runtime.get("claude_command", "claude"))]
    extra_args = role_config.get("extra_args", [])
    claude_role = role_config.get("claude_role")
    if claude_role:
        command.extend(["--append-system-prompt", f"role={claude_role}"])
    command.extend(extra_args)
    command.extend([runtime.get("claude_headless_flag", "-p"), prompt])
    return command


def build_runner_command(
    *,
    runner: str,
    role: str,
    prompt: str,
    role_config: dict,
    runtime_config: dict | None = None,
) -> list[str]:
    if runner == "ccs":
        return build_ccs_command(role=role, prompt=prompt, role_config=role_config)
    if runner == "claude":
        return build_claude_command(role=role, prompt=prompt, role_config=role_config, runtime_config=runtime_config)
    raise ValueError(f"Unsupported runner: {runner}")


def command_preview(command: list[str]) -> str:
    return shlex.join(command)


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
    timeout: int = 300,
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
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        detail = f"runner={runner} role={role} timed out after {timeout}s: {preview}"
        if fallback_reason:
            detail = f"{detail}\nfallback_reason: {fallback_reason}"
        raise RunnerError(detail)
    except subprocess.CalledProcessError as exc:
        hint = authentication_hint(runner, exc.stderr)
        stdout = (getattr(exc, "output", None) or "").strip() or "(none)"
        stderr = (exc.stderr or "").strip() or "(none)"
        detail = f"runner={runner} role={role} exited {exc.returncode}: {preview}\nstdout: {stdout}\nstderr: {stderr}"
        if fallback_reason:
            detail = f"{detail}\nfallback_reason: {fallback_reason}"
        if hint:
            detail = f"{detail}\nhint: {hint}"
        raise RunnerError(detail) from exc
    engine = role_config.get("engine", role_config.get("claude_role", role))
    model = role_config.get("model", runner)
    return RoleResult(role=role, runner=runner, engine=engine, model=model, status="success", output=completed.stdout, command=command, command_preview=preview, fallback_reason=fallback_reason)
