from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import runner_commands as _commands
import runner_execution as _execution
import runner_resolution as _resolution

BUILTIN_CCS_PROFILES = _resolution.BUILTIN_CCS_PROFILES
DEFAULT_ROLE_TIMEOUT = _execution.DEFAULT_ROLE_TIMEOUT
MAX_ERROR_OUTPUT_CHARS = _execution.MAX_ERROR_OUTPUT_CHARS
RoleResult = _execution.RoleResult
RunnerError = _resolution.RunnerError
RunnerResolution = _resolution.RunnerResolution

subprocess = subprocess
_base_has_command = _resolution.has_command
_base_probe_ccs_profile = _resolution.probe_ccs_profile


def has_command(name: str) -> bool:
    return _base_has_command(name)


def resolve_runner(requested_runner: str, *, has_ccs: bool | None = None) -> RunnerResolution:
    return _resolution.resolve_runner(requested_runner, has_ccs=has_ccs)


def probe_ccs_profile(profile: str, command: str = "ccs") -> tuple[bool, str | None]:
    return _base_probe_ccs_profile(profile, command=command)


def is_missing_ccs_profile(profile: str, detail: str | None) -> bool:
    return _resolution.is_missing_ccs_profile(profile, detail)


def resolve_role_runner(**kwargs) -> RunnerResolution:
    original_probe = _resolution.probe_ccs_profile
    original_has_command = _resolution.has_command
    try:
        _resolution.probe_ccs_profile = probe_ccs_profile
        _resolution.has_command = has_command
        return _resolution.resolve_role_runner(**kwargs)
    finally:
        _resolution.probe_ccs_profile = original_probe
        _resolution.has_command = original_has_command


def build_ccs_command(role: str, prompt: str, role_config: dict) -> list[str]:
    return _commands.build_ccs_command(role=role, prompt=prompt, role_config=role_config)


def build_claude_command(role: str, prompt: str, role_config: dict, runtime_config: dict | None = None) -> list[str]:
    return _commands.build_claude_command(role=role, prompt=prompt, role_config=role_config, runtime_config=runtime_config)


def build_runner_command(*, runner: str, role: str, prompt: str, role_config: dict, runtime_config: dict | None = None) -> list[str]:
    return _commands.build_runner_command(runner=runner, role=role, prompt=prompt, role_config=role_config, runtime_config=runtime_config)


def command_preview(command: list[str]) -> str:
    return _commands.command_preview(command)


def timeout_for_role(role: str, runtime_config: dict | None = None) -> int:
    return _execution.timeout_for_role(role, runtime_config)


def authentication_hint(runner: str, stderr: str | None) -> str | None:
    return _execution.authentication_hint(runner, stderr)


def run_role(**kwargs) -> RoleResult:
    return _execution.run_role(**kwargs)


def run_role_subprocess(**kwargs) -> RoleResult:
    original_run = _execution.subprocess.run
    try:
        _execution.subprocess.run = subprocess.run
        return _execution.run_role_subprocess(**kwargs)
    finally:
        _execution.subprocess.run = original_run


__all__ = [
    "BUILTIN_CCS_PROFILES",
    "DEFAULT_ROLE_TIMEOUT",
    "MAX_ERROR_OUTPUT_CHARS",
    "RoleResult",
    "RunnerError",
    "RunnerResolution",
    "authentication_hint",
    "build_ccs_command",
    "build_claude_command",
    "build_runner_command",
    "command_preview",
    "has_command",
    "is_missing_ccs_profile",
    "probe_ccs_profile",
    "resolve_role_runner",
    "resolve_runner",
    "run_role",
    "run_role_subprocess",
    "subprocess",
    "timeout_for_role",
]
