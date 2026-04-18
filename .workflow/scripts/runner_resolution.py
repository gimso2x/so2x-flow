from __future__ import annotations

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
