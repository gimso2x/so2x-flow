from __future__ import annotations

import shlex


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
