import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / ".workflow" / "scripts" / "ccs_runner.py"

spec = importlib.util.spec_from_file_location("so2x_flow_ccs_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
assert spec.loader is not None
spec.loader.exec_module(runner)


def test_resolve_runner_prefers_ccs_when_auto_and_available():
    result = runner.resolve_runner("auto", has_ccs=True)
    assert result.selected_runner == "ccs"
    assert result.fallback_used is False


def test_resolve_runner_falls_back_to_claude_when_ccs_missing():
    result = runner.resolve_runner("ccs", has_ccs=False)
    assert result.requested_runner == "ccs"
    assert result.selected_runner == "claude"
    assert result.fallback_used is True
    assert "ccs not found" in result.fallback_reason


def test_build_ccs_command_uses_ccs_profile_as_invocation_target_without_profile_flag():
    command = runner.build_ccs_command(
        role="implementer",
        prompt="hello",
        role_config={
            "engine": "glm",
            "model": "glm-4.5",
            "profile": "impl",
            "ccs_profile": "codex",
            "command": "ccs",
            "extra_args": ["--json"],
        },
    )
    assert command[:2] == ["ccs", "codex"]
    assert "--profile" not in command
    assert "-p" not in command
    assert command[-1] == "hello"


def test_build_claude_command_uses_headless_flag_and_role_hint():
    command = runner.build_claude_command(
        role="planner",
        prompt="hello",
        role_config={"command": "claude", "claude_role": "planner", "extra_args": ["--verbose"]},
        runtime_config={"claude_headless_flag": "-p"},
    )
    assert command[:1] == ["claude"]
    assert "--append-system-prompt" in command
    assert command[-2:] == ["-p", "hello"]


def test_run_role_dry_run_includes_runner_and_command_preview():
    result = runner.run_role(
        runner="ccs",
        role="planner",
        prompt="hello",
        role_config={"engine": "codex", "model": "codex", "command": "ccs"},
        dry_run=True,
    )
    assert result.status == "dry-run"
    assert result.runner == "ccs"
    assert "runner=ccs" in result.output
    assert "command=ccs codex" in result.output


def test_run_role_live_path_delegates_to_subprocess_runner(monkeypatch):
    captured = {}

    def fake_subprocess(**kwargs):
        captured.update(kwargs)
        return runner.RoleResult(
            role=kwargs["role"],
            runner=kwargs["runner"],
            engine="planner",
            model="claude",
            status="success",
            output="live-ok\n",
            command=["claude", "-p", "hello"],
            command_preview="claude -p hello",
            fallback_reason=kwargs.get("fallback_reason"),
        )

    monkeypatch.setattr(runner._execution, "run_role_subprocess", fake_subprocess)

    result = runner.run_role(
        runner="claude",
        role="planner",
        prompt="hello",
        role_config={"command": "claude", "claude_role": "planner"},
        runtime_config={"claude_headless_flag": "-p"},
        dry_run=False,
    )

    assert result.status == "success"
    assert result.output == "live-ok\n"
    assert captured["runner"] == "claude"
    assert captured["role"] == "planner"
    assert captured["prompt"] == "hello"


def test_run_role_subprocess_timeout_raises_runner_error_with_command_preview(monkeypatch):
    def fake_run(*args, **kwargs):
        raise runner.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 300))

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    try:
        runner.run_role_subprocess(
            runner="claude",
            role="reviewer",
            prompt="hello",
            role_config={"command": "claude", "claude_role": "reviewer"},
            runtime_config={"claude_headless_flag": "-p"},
            timeout=7,
        )
    except runner.RunnerError as exc:
        message = str(exc)
        assert "runner=claude role=reviewer timed out after 7s" in message
        assert "claude --append-system-prompt role=reviewer -p hello" in message
    else:
        raise AssertionError("Expected RunnerError for timeout path")



def test_timeout_for_role_uses_role_specific_config_when_present():
    assert runner.timeout_for_role("reviewer", {"role_timeouts": {"reviewer": 12}}) == 12
    assert runner.timeout_for_role("reviewer", {"role_timeouts": {"planner": 5}}) == 300



def test_timeout_for_role_rejects_non_positive_or_non_integer_values():
    for bad in (0, -1, "5"):
        try:
            runner.timeout_for_role("reviewer", {"role_timeouts": {"reviewer": bad}})
        except runner.RunnerError as exc:
            assert "role_timeouts.reviewer" in str(exc)
        else:
            raise AssertionError("Expected RunnerError for invalid role timeout")



def test_runner_error_summary_truncates_large_output_and_keeps_fallback_reason(monkeypatch):
    def fake_run(*args, **kwargs):
        raise runner.subprocess.CalledProcessError(
            returncode=9,
            cmd=args[0],
            output="x" * 900,
            stderr="y" * 900,
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    try:
        runner.run_role_subprocess(
            runner="claude",
            role="implementer",
            prompt="hello",
            role_config={"command": "claude", "claude_role": "implementer"},
            runtime_config={"claude_headless_flag": "-p"},
            timeout=11,
            fallback_reason="role=implementer profile 'glm' is not available via ccs",
        )
    except runner.RunnerError as exc:
        message = str(exc)
        assert "stdout: " in message and "...(truncated" in message
        assert "stderr: " in message and "...(truncated" in message
        assert "fallback_reason: role=implementer profile 'glm' is not available via ccs" in message
    else:
        raise AssertionError("Expected RunnerError for subprocess failure path")



def test_run_role_subprocess_command_failure_raises_runner_error_with_stderr(monkeypatch):
    def fake_run(*args, **kwargs):
        raise runner.subprocess.CalledProcessError(
            returncode=17,
            cmd=args[0],
            stderr="boom",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    try:
        runner.run_role_subprocess(
            runner="ccs",
            role="planner",
            prompt="hello",
            role_config={"command": "ccs", "engine": "codex", "model": "codex"},
            timeout=11,
        )
    except runner.RunnerError as exc:
        message = str(exc)
        assert "runner=ccs role=planner exited 17" in message
        assert "stderr: boom" in message
        assert "stdout: (none)" in message
        assert "ccs codex hello" in message
    else:
        raise AssertionError("Expected RunnerError for subprocess failure path")


def test_run_role_subprocess_command_failure_includes_stdout_and_fallback_reason(monkeypatch):
    def fake_run(*args, **kwargs):
        raise runner.subprocess.CalledProcessError(
            returncode=9,
            cmd=args[0],
            output="partial-output",
            stderr="bad things happened",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    try:
        runner.run_role_subprocess(
            runner="claude",
            role="implementer",
            prompt="hello",
            role_config={"command": "claude", "claude_role": "implementer"},
            runtime_config={"claude_headless_flag": "-p"},
            timeout=11,
            fallback_reason="role=implementer profile 'glm' is not available via ccs",
        )
    except runner.RunnerError as exc:
        message = str(exc)
        assert "runner=claude role=implementer exited 9" in message
        assert "stdout: partial-output" in message
        assert "stderr: bad things happened" in message
        assert "fallback_reason: role=implementer profile 'glm' is not available via ccs" in message
    else:
        raise AssertionError("Expected RunnerError for subprocess failure path")


def test_run_role_subprocess_surfaces_ccs_codex_auth_hint(monkeypatch):
    def fake_run(*args, **kwargs):
        raise runner.subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0],
            stderr="[X] Failed to start OAuth flow\n[X] Authentication required for OpenAI Codex",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    try:
        runner.run_role_subprocess(
            runner="ccs",
            role="planner",
            prompt="hello",
            role_config={"command": "ccs", "engine": "codex", "model": "codex", "profile": "codex"},
            timeout=11,
        )
    except runner.RunnerError as exc:
        message = str(exc)
        assert "Authentication required for OpenAI Codex" in message
        assert "ccs is installed but Codex auth is not configured" in message
        assert "run `ccs setup` or `ccs codex --auth`" in message
    else:
        raise AssertionError("Expected RunnerError for ccs auth failure path")


def test_resolve_role_runner_keeps_builtin_ccs_profile_without_role_fallback():
    result = runner.resolve_role_runner(
        requested_runner="ccs",
        role="planner",
        role_config={
            "ccs_profile": "codex",
            "ccs": {"command": "ccs", "engine": "codex", "model": "codex"},
            "claude": {"command": "claude"},
        },
        runtime_config={"claude_command": "claude", "claude_headless_flag": "-p"},
        has_ccs=True,
        has_claude=True,
    )
    assert result.selected_runner == "ccs"
    assert result.fallback_used is False
    assert result.fallback_reason is None


def test_resolve_role_runner_falls_back_to_claude_when_ccs_profile_missing(monkeypatch):
    monkeypatch.setattr(runner, "probe_ccs_profile", lambda profile, command="ccs": (False, "Profile 'glm' not found"))

    result = runner.resolve_role_runner(
        requested_runner="ccs",
        role="implementer",
        role_config={
            "ccs_profile": "glm",
            "ccs": {"command": "ccs", "engine": "glm", "model": "glm"},
            "claude": {"command": "claude"},
        },
        runtime_config={"claude_command": "claude", "claude_headless_flag": "-p"},
        has_ccs=True,
        has_claude=True,
    )
    assert result.selected_runner == "claude"
    assert result.fallback_used is True
    assert "profile 'glm' is not available via ccs" in result.fallback_reason


def test_resolve_role_runner_probes_with_nested_ccs_command(monkeypatch):
    captured = {}

    def fake_probe(profile, command="ccs"):
        captured["profile"] = profile
        captured["command"] = command
        return False, "Profile 'glm' not found"

    monkeypatch.setattr(runner, "probe_ccs_profile", fake_probe)

    result = runner.resolve_role_runner(
        requested_runner="ccs",
        role="implementer",
        role_config={
            "ccs_profile": "glm",
            "ccs": {"command": "/tmp/custom-ccs", "engine": "glm", "model": "glm"},
            "claude": {"command": "claude"},
        },
        runtime_config={"claude_command": "claude", "claude_headless_flag": "-p"},
        has_ccs=True,
        has_claude=True,
    )

    assert captured == {"profile": "glm", "command": "/tmp/custom-ccs"}
    assert result.selected_runner == "claude"
    assert result.fallback_used is True
    assert "profile 'glm' is not available via ccs" in result.fallback_reason


def test_resolve_role_runner_raises_when_ccs_profile_missing_and_no_claude_available(monkeypatch):
    monkeypatch.setattr(runner, "probe_ccs_profile", lambda profile, command="ccs": (False, "Profile 'glm' not found"))

    try:
        runner.resolve_role_runner(
            requested_runner="ccs",
            role="implementer",
            role_config={
                "ccs_profile": "glm",
                "ccs": {"command": "ccs", "engine": "glm", "model": "glm"},
                "claude": {"command": "claude"},
            },
            runtime_config={"claude_command": "claude", "claude_headless_flag": "-p"},
            has_ccs=True,
            has_claude=False,
        )
    except runner.RunnerError as exc:
        assert "profile 'glm' is not available via ccs" in str(exc)
        assert "claude fallback is unavailable" in str(exc)
    else:
        raise AssertionError("Expected RunnerError when ccs profile is missing and claude fallback is unavailable")


def test_resolve_role_runner_uses_role_specific_claude_command_for_fallback(monkeypatch):
    monkeypatch.setattr(runner, "probe_ccs_profile", lambda profile, command="ccs": (False, "Profile 'glm' not found"))
    monkeypatch.setattr(runner, "has_command", lambda command: command == "/tmp/fake-claude")

    result = runner.resolve_role_runner(
        requested_runner="ccs",
        role="implementer",
        role_config={
            "ccs_profile": "glm",
            "command": "ccs",
            "ccs": {"command": "ccs", "engine": "glm", "model": "glm"},
            "claude": {"command": "/tmp/fake-claude"},
        },
        runtime_config={"claude_command": "/tmp/runtime-claude", "claude_headless_flag": "-p"},
        has_ccs=True,
    )
    assert result.selected_runner == "claude"
    assert result.fallback_used is True
    assert "profile 'glm' is not available via ccs" in result.fallback_reason


def test_resolve_role_runner_does_not_fallback_on_non_profile_probe_failure(monkeypatch):
    monkeypatch.setattr(runner, "probe_ccs_profile", lambda profile, command="ccs": (False, "timed out while probing ccs profile"))

    try:
        runner.resolve_role_runner(
            requested_runner="ccs",
            role="implementer",
            role_config={
                "ccs_profile": "glm",
                "command": "ccs",
                "ccs": {"command": "ccs", "engine": "glm", "model": "glm"},
                "claude": {"command": "claude"},
            },
            runtime_config={"claude_command": "claude", "claude_headless_flag": "-p"},
            has_ccs=True,
            has_claude=True,
        )
    except runner.RunnerError as exc:
        assert "timed out while probing ccs profile" in str(exc)
        assert "claude fallback is unavailable" not in str(exc)
    else:
        raise AssertionError("Expected RunnerError for non-profile probe failures")
