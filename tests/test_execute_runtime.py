import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

from execute_helpers import ROOT, make_sample_target_repo, make_workspace, output_path, read_json, run_execute

def test_execute_doctor_mode_persists_status_surface(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    run_execute(workspace, "feature", "로그인 기능 구현", "--dry-run")

    result = run_execute(workspace, "doctor")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["mode"] == "doctor"
    assert payload["overall_status"] == "ok"
    assert payload["exact_status"] == "ok:feature"
    assert payload["latest_output_json"] == ".workflow/outputs/feature/로그인-기능-구현.json"
    assert payload["latest_outputs"]["doctor"] == ".workflow/outputs/doctor/status.json"

def test_execute_doctor_mode_uses_default_request_and_prints_doctor_summary(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    result = run_execute(workspace, "doctor")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert "overall_status: idle" in result.stdout
    assert "exact_status: idle" in result.stdout
    assert payload["mode"] == "doctor"
    assert payload["overall_status"] == "idle"

def test_live_execution_requires_explicit_runtime_opt_in(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    execute = workspace / ".workflow" / "scripts" / "execute.py"

    result = subprocess.run(
        [sys.executable, str(execute), "review", "실실행 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "allow_live_run" in result.stderr

def test_live_execution_rejects_non_boolean_allow_live_run_values(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["allow_live_run"] = "true"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "실실행 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "allow_live_run must be a boolean true" in result.stderr

def test_feature_live_execution_requires_approved_plan_even_without_skip_plan(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["allow_live_run"] = True
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "프로필 편집"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "feature live execution requires an explicitly approved plan artifact" in result.stderr

def test_legacy_mode_aliases_still_work(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    qa_payload = read_json(output_path(workspace, run_execute(workspace, "qa-fix", "QA-009 토글 오동작", "--qa-id", "QA-009", "--dry-run").stdout, "output_json"))
    plan_payload = read_json(output_path(workspace, run_execute(workspace, "plan-only", "결제 기능 작업 분해", "--dry-run").stdout, "output_json"))
    assert qa_payload["mode"] == "qa"
    assert plan_payload["mode"] == "plan"

def test_requested_ccs_falls_back_to_claude_when_ccs_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    original = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    updated = json.loads(json.dumps(original))
    updated["runtime"]["runner"] = "ccs"
    config_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = run_execute(workspace, "review", "출력 경로 확인", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["requested_runner"] == "ccs"
    assert payload["selected_runner"] in {"ccs", "claude"}
    if payload["selected_runner"] == "claude":
        assert payload["fallback_used"] is True
        assert "claude -p" in payload["role_results"][0]["command_preview"]

def test_build_payload_leaves_output_json_empty_until_persisted(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Resolution:
        requested_runner = "claude"
        selected_runner = "claude"
        fallback_used = False
        fallback_reason = None

    payload = module.build_payload(
        mode="review",
        request="출력 경로 확인",
        dry_run=True,
        resolution=Resolution(),
        design_doc="DESIGN.md",
        approved_plan_path=None,
        approved_plan_match_reason=None,
        docs_used=[".workflow/docs/QA.md"],
        roles=["reviewer"],
        role_results=[],
        artifacts=[".workflow/tasks/review/출력-경로-확인.json"],
    )

    assert payload["output_json"] == ""

def test_build_payload_keeps_failure_and_fallback_contract_fields(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Resolution:
        requested_runner = "ccs"
        selected_runner = "claude"
        fallback_used = True
        fallback_reason = "ccs not found; falling back to claude -p"

    role_results = [
        {
            "role": "planner",
            "runner": "claude",
            "engine": "claude",
            "model": "claude-sonnet",
            "status": "success",
            "output": "planner ok\n",
            "command": ["claude", "-p", "hello"],
            "command_preview": "claude -p hello",
            "fallback_reason": "role=planner profile 'codex' is not available via ccs",
        }
    ]

    payload = module.build_payload(
        mode="feature",
        request="로그인 기능 구현",
        dry_run=False,
        resolution=Resolution(),
        design_doc="DESIGN.md",
        approved_plan_path=".workflow/tasks/plan/로그인-기능-설계-확정.json",
        approved_plan_match_reason="explicit approval metadata matched latest request",
        docs_used=[".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md"],
        roles=["planner", "implementer"],
        role_results=role_results,
        artifacts=[".workflow/tasks/feature/로그인-기능-구현.json"],
        failed_role="implementer",
        failed_stage="role_execution",
        failure_message="implementer failed after planner success",
    )

    assert payload["requested_runner"] == "ccs"
    assert payload["selected_runner"] == "claude"
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "ccs not found; falling back to claude -p"
    assert payload["approved_plan_path"] == ".workflow/tasks/plan/로그인-기능-설계-확정.json"
    assert payload["failed_role"] == "implementer"
    assert payload["failed_stage"] == "role_execution"
    assert payload["failure_message"] == "implementer failed after planner success"
    assert payload["role_results"][0]["fallback_reason"] == "role=planner profile 'codex' is not available via ccs"
    assert payload["output_json"] == ""

def test_print_summary_emits_fallbacks_failures_and_output_json_lines(tmp_path: Path, capsys):
    workspace = make_workspace(tmp_path)
    payloads_path = workspace / ".workflow" / "scripts" / "payloads.py"
    spec = importlib.util.spec_from_file_location("so2x_flow_payloads", payloads_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    payload = {
        "mode": "feature",
        "artifact_kind": "feature",
        "request": "로그인 기능 구현",
        "dry_run": False,
        "requested_runner": "ccs",
        "selected_runner": "ccs",
        "fallback_used": False,
        "fallback_reason": None,
        "design_doc": "DESIGN.md",
        "approved_plan_path": ".workflow/tasks/plan/로그인-기능-설계-확정.json",
        "approved_plan_match_reason": "token overlap matched approved artifact",
        "docs_used": [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md"],
        "roles": ["planner", "implementer"],
        "role_results": [
            {
                "role": "planner",
                "runner": "ccs",
                "engine": "codex",
                "model": "codex",
                "status": "success",
                "output": "planner ok\n",
                "command": ["ccs", "codex", "prompt"],
                "command_preview": "ccs codex prompt",
                "fallback_reason": None,
            },
            {
                "role": "implementer",
                "runner": "claude",
                "engine": "claude",
                "model": "claude-sonnet",
                "status": "failed",
                "output": "",
                "command": ["claude", "-p", "prompt"],
                "command_preview": "claude -p prompt",
                "fallback_reason": "role=implementer profile 'missing-profile' is not available via ccs",
            },
        ],
        "artifacts": [".workflow/tasks/feature/로그인-기능-구현.json"],
        "failed_role": "implementer",
        "failed_stage": "role_execution",
        "failure_message": "implementer failed after planner success",
        "output_json": ".workflow/outputs/feature/로그인-기능-구현.json",
    }

    module.print_summary(payload)
    stdout = capsys.readouterr().out
    assert "fallback_used: False" in stdout
    assert "fallback_reason: (none)" in stdout
    assert "approved_plan_path: .workflow/tasks/plan/로그인-기능-설계-확정.json" in stdout
    assert "approved_plan_match_reason: token overlap matched approved artifact" in stdout
    assert "role_fallbacks:" in stdout
    assert "  - planner: (none)" in stdout
    assert "  - implementer: role=implementer profile 'missing-profile' is not available via ccs" in stdout
    assert "failed_role: implementer" in stdout
    assert "failed_stage: role_execution" in stdout
    assert "failure_message: implementer failed after planner success" in stdout
    assert "output_json: .workflow/outputs/feature/로그인-기능-구현.json" in stdout

def test_run_roles_reports_runner_resolution_stage_separately(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    runtime_path = workspace / ".workflow" / "scripts" / "execution_runtime.py"
    scripts_dir = str(runtime_path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("so2x_flow_execution_runtime", runtime_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class Resolution:
            selected_runner = "ccs"

        class Context:
            roles = ["implementer"]
            docs_used = [".workflow/docs/PRD.md"]
            docs_bundle = "bundle"
            task_path = None
            task_content = None
            design_doc = "DESIGN.md"
            approved_plan_path = None
            approved_plan_match_reason = None

        def fake_resolve_role_runner(**kwargs):
            raise RuntimeError("probe exploded")

        module.resolve_role_runner = fake_resolve_role_runner

        try:
            module.run_roles(
                config={"roles": {"implementer": {"ccs": {"command": "ccs"}}}},
                resolution=Resolution(),
                runtime_config={},
                prompts_dir=workspace / ".workflow" / "prompts",
                mode="feature",
                request="로그인 기능 구현",
                context=Context(),
                qa_id=None,
                dry_run=True,
            )
        except module.ExecutionFailure as exc:
            assert exc.stage == "runner_resolution"
            assert exc.role == "implementer"
            assert exc.role_results == []
            assert "probe exploded" in exc.message
        else:
            raise AssertionError("Expected ExecutionFailure for runner resolution")
    finally:
        sys.path.remove(scripts_dir)

def test_run_roles_reports_prompt_build_stage_separately(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    runtime_path = workspace / ".workflow" / "scripts" / "execution_runtime.py"
    scripts_dir = str(runtime_path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("so2x_flow_execution_runtime", runtime_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class Resolution:
            selected_runner = "claude"

        class RoleResolution:
            selected_runner = "claude"
            fallback_reason = None

        class Context:
            roles = ["reviewer"]
            docs_used = [".workflow/docs/QA.md"]
            docs_bundle = "bundle"
            task_path = None
            task_content = None
            design_doc = "DESIGN.md"
            approved_plan_path = None
            approved_plan_match_reason = None

        module.resolve_role_runner = lambda **kwargs: RoleResolution()
        module.build_prompt = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("prompt template missing"))

        try:
            module.run_roles(
                config={"roles": {"reviewer": {"claude": {"command": "claude"}}}},
                resolution=Resolution(),
                runtime_config={},
                prompts_dir=workspace / ".workflow" / "prompts",
                mode="review",
                request="QA 관점 점검",
                context=Context(),
                qa_id=None,
                dry_run=True,
            )
        except module.ExecutionFailure as exc:
            assert exc.stage == "prompt_build"
            assert exc.role == "reviewer"
            assert exc.role_results == []
            assert "prompt template missing" in exc.message
        else:
            raise AssertionError("Expected ExecutionFailure for prompt build")
    finally:
        sys.path.remove(scripts_dir)

def test_execute_uses_runner_resolution_layer_and_live_runner_path(tmp_path: Path):
    execute = (ROOT / ".workflow" / "scripts" / "execute.py").read_text(encoding="utf-8")
    execution_runtime = (ROOT / ".workflow" / "scripts" / "execution_runtime.py").read_text(encoding="utf-8")
    prompt_builder = (ROOT / ".workflow" / "scripts" / "prompt_builder.py").read_text(encoding="utf-8")
    mode_handlers = (ROOT / ".workflow" / "scripts" / "mode_handlers.py").read_text(encoding="utf-8")
    payloads = (ROOT / ".workflow" / "scripts" / "payloads.py").read_text(encoding="utf-8")
    workflow_context = (ROOT / ".workflow" / "scripts" / "workflow_context.py").read_text(encoding="utf-8")
    workflow_docs = (ROOT / ".workflow" / "scripts" / "workflow_docs.py").read_text(encoding="utf-8")
    workflow_tasks = (ROOT / ".workflow" / "scripts" / "workflow_tasks.py").read_text(encoding="utf-8")
    assert "from ccs_runner import resolve_runner" in execute
    assert "from execution_runtime import" in execute
    assert "def run_roles(" in execution_runtime
    assert "def validate_runtime_config(" in execution_runtime
    assert "runner_resolution" in execution_runtime
    assert "prompt_build" in execution_runtime
    assert "def build_prompt(" in prompt_builder
    assert "project_root=project_root" not in execution_runtime
    assert "project_root=PROJECT_ROOT,\n            mode=mode,\n            request=args.request,\n            context=context,\n            qa_id=args.qa_id,\n            dry_run=args.dry_run" not in execute
    assert "task_content=context.task_content" in execution_runtime
    assert "task_content: str | None" in mode_handlers
    assert "planner_output: str | None" not in mode_handlers
    assert "load_text(task_file)" not in prompt_builder
    assert "from workflow_docs import collect_docs, load_docs_bundle" in mode_handlers
    assert "from workflow_context import select_approved_plan" in mode_handlers
    assert "from workflow_tasks import (" in mode_handlers
    assert "def build_payload(" in payloads
    assert "def select_approved_plan(" in workflow_context
    assert "def collect_docs(" not in workflow_context
    assert "def load_docs_bundle(" not in workflow_context
    assert "def collect_docs(" in workflow_docs
    assert "def load_docs_bundle(" in workflow_docs
    assert "def write_feature_task(" in workflow_tasks
    assert "def write_init_task(" in workflow_tasks
    assert "def write_plan_mode_task(" in workflow_tasks

    workspace = make_workspace(tmp_path)
    fake_runner = workspace / "fake-claude.sh"
    fake_runner.write_text("#!/usr/bin/env bash\nprintf 'live-ok\\n'\n", encoding="utf-8")
    fake_runner.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "claude"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_runner)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["reviewer"]["claude"]["command"] = str(fake_runner)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = run_execute(workspace, "review", "실실행 테스트")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["role_results"][0]["status"] == "success"
    assert payload["role_results"][0]["output"] == "live-ok\n"

def test_live_execution_requires_explicit_runtime_opt_in_duplicate_guard(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "실실행 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "allow_live_run" in result.stderr

def test_live_execution_uses_role_specific_timeout_and_persists_failure_payload(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    fake_runner = workspace / "fake-timeout.sh"
    fake_runner.write_text("#!/usr/bin/env bash\nsleep 2\n", encoding="utf-8")
    fake_runner.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "claude"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_runner)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["runtime"]["role_timeouts"] = {"reviewer": 1}
    config["roles"]["reviewer"]["claude"]["command"] = str(fake_runner)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "review", "타임아웃 테스트"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "failed_role: reviewer" in result.stdout
    assert "timed out after 1s" in result.stderr
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["failed_role"] == "reviewer"
    assert payload["failed_stage"] == "role_execution"
    assert payload["role_results"] == []
    assert "timed out after 1s" in payload["failure_message"]

def test_live_execution_persists_partial_results_when_later_role_fails(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 구현", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    fake_claude = workspace / "fake-claude.sh"
    fake_claude.write_text("#!/usr/bin/env bash\nprintf 'planner-live-ok\\n'\n", encoding="utf-8")
    fake_claude.chmod(0o755)

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    probe_dir = workspace / "probe-bin"
    probe_dir.mkdir()
    probe = probe_dir / "ccs"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"missing-profile\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  echo \"Profile 'missing-profile' not found\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "if [ \"$1\" = \"codex\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  exit 0\n"
        "fi\n"
        "printf 'planner-live-ok\\n'\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)

    failing_claude = workspace / "fake-failing-claude.sh"
    failing_claude.write_text("#!/usr/bin/env bash\necho 'implementer failed' >&2\nexit 9\n", encoding="utf-8")
    failing_claude.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_claude)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["planner"]["ccs_profile"] = "codex"
    config["roles"]["planner"]["ccs"]["command"] = str(probe)
    config["roles"]["implementer"]["ccs_profile"] = "missing-profile"
    config["roles"]["implementer"]["claude"]["command"] = str(failing_claude)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env = dict(**__import__("os").environ)
    env["PATH"] = f"{probe_dir}:{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "로그인 기능 구현"],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "failed_role: implementer" in result.stdout
    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["failed_role"] == "implementer"
    assert payload["failed_stage"] == "role_execution"
    assert len(payload["role_results"]) == 1
    assert payload["role_results"][0]["role"] == "planner"
    assert payload["role_results"][0]["output"] == "planner-live-ok\n"
    assert "fallback_reason" in payload["failure_message"]
    assert "implementer failed" in payload["failure_message"]

def test_live_ccs_execution_surfaces_codex_auth_guidance(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    fake_ccs = workspace / "fake-ccs.sh"
    fake_ccs.write_text(
        "#!/usr/bin/env bash\n"
        "echo '[X] Failed to start OAuth flow' >&2\n"
        "echo '[X] Authentication required for OpenAI Codex' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_ccs.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["roles"]["planner"]["ccs"]["command"] = str(fake_ccs)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    result = subprocess.run(
        [sys.executable, str(execute), "plan", "결제 기능 작업 분해"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ccs is installed but Codex auth is not configured" in result.stderr
    assert "run `ccs setup` or `ccs codex --auth`" in result.stderr

def test_docs_first_smoke_plan_feature_qa_sequence(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    plan_result = run_execute(workspace, "plan", "로그인 폼 validation과 submit 흐름 추가", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    assert plan_json["request"] == "로그인 폼 validation과 submit 흐름 추가"
    assert plan_json["status"] == "draft"
    assert plan_json["approved"] is False

    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_result = run_execute(workspace, "feature", "로그인 폼 validation과 submit 흐름 추가", "--skip-plan", "--dry-run")
    feature_payload = read_json(output_path(workspace, feature_result.stdout, "output_json"))
    feature_json = read_json(workspace / feature_payload["artifacts"][0])
    assert feature_payload["roles"] == ["implementer"]
    assert feature_payload["approved_plan_path"] == plan_payload["artifacts"][0]
    assert feature_json["latest_approved_flow_plan_output"] == plan_payload["artifacts"][0]
    assert feature_json["approved_direction"]["source_plan_artifact"] == plan_payload["artifacts"][0]
    assert feature_json["verification"] == ["List the checks required before considering this slice done."]

    qa_result = run_execute(workspace, "qa", "로그인 실패시 에러 메시지와 재시도 동작 점검", "--qa-id", "QA-101", "--dry-run")
    qa_payload = read_json(output_path(workspace, qa_result.stdout, "output_json"))
    qa_json = read_json(workspace / qa_payload["artifacts"][0])
    assert qa_payload["docs_used"][0] == ".workflow/docs/QA.md"
    assert qa_payload["roles"] == ["qa_planner", "implementer"]
    assert qa_json["qa_id"] == "QA-101"
    assert qa_json["reproduction"] == ["Describe how to reproduce the issue."]
    assert qa_json["minimal_fix"] == ["Describe the smallest safe repair."]

def test_external_sample_repo_install_init_plan_e2e_smoke(tmp_path: Path):
    repo = make_sample_target_repo(tmp_path)

    init_result = run_execute(repo, "init", "외부 샘플 앱 초기 설정", "--dry-run")
    init_payload = read_json(output_path(repo, init_result.stdout, "output_json"))
    init_json = read_json(repo / init_payload["artifacts"][0])
    assert (repo / "README.md").read_text(encoding="utf-8") == "# sample target\n"
    assert (repo / "app.py").read_text(encoding="utf-8") == "print('sample app')\n"
    assert "## so2x-flow" in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert init_json["status"] == "needs_user_input"
    assert init_json["current_question_id"] is None
    assert init_payload["docs_used"][0] == ".workflow/docs/PRD.md"

    plan_result = run_execute(repo, "plan", "외부 샘플 앱 로그인 흐름 작업 분해", "--dry-run")
    plan_payload = read_json(output_path(repo, plan_result.stdout, "output_json"))
    plan_json = read_json(repo / plan_payload["artifacts"][0])
    assert plan_json["request"] == "외부 샘플 앱 로그인 흐름 작업 분해"
    assert plan_json["status"] == "draft"
    assert plan_json["approved"] is False
    assert (repo / ".workflow" / "scripts" / "execute.py").exists()
    assert (repo / ".claude" / "skills" / "flow-init.md").exists()

def test_live_feature_role_can_fallback_to_claude_when_ccs_profile_missing(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    plan_result = run_execute(workspace, "plan", "로그인 기능 구현", "--dry-run")
    plan_payload = read_json(output_path(workspace, plan_result.stdout, "output_json"))
    plan_path = workspace / plan_payload["artifacts"][0]
    plan_json = read_json(plan_path)
    plan_json["approved"] = True
    plan_json["status"] = "approved"
    plan_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    fake_claude = workspace / "fake-claude.sh"
    fake_claude.write_text("#!/usr/bin/env bash\nprintf 'claude-live-ok\\n'\n", encoding="utf-8")
    fake_claude.chmod(0o755)

    execute = workspace / ".workflow" / "scripts" / "execute.py"
    probe_dir = workspace / "probe-bin"
    probe_dir.mkdir()
    probe = probe_dir / "ccs"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"missing-profile\" ] && [ \"$2\" = \"--help\" ]; then\n"
        "  echo \"Profile 'missing-profile' not found\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "printf 'ccs-live-ok\\n'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)

    config_path = workspace / ".workflow" / "config" / "ccs-map.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["runner"] = "ccs"
    config["runtime"]["allow_live_run"] = True
    config["runtime"]["claude_command"] = str(fake_claude)
    config["runtime"]["claude_headless_flag"] = "--prompt"
    config["roles"]["planner"]["ccs_profile"] = "codex"
    config["roles"]["implementer"]["ccs_profile"] = "missing-profile"
    config["roles"]["planner"]["claude"]["command"] = str(fake_claude)
    config["roles"]["implementer"]["claude"]["command"] = str(fake_claude)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env = dict(**__import__("os").environ)
    env["PATH"] = f"{probe_dir}:{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(execute), "feature", "로그인 기능 구현"],
        cwd=workspace,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    payload = read_json(output_path(workspace, result.stdout, "output_json"))
    assert payload["selected_runner"] == "ccs"
    assert "role_fallbacks:" in result.stdout
    assert "  - planner: (none)" in result.stdout
    assert payload["role_results"][0]["runner"] == "ccs"
    assert payload["role_results"][0]["fallback_reason"] is None
    assert payload["role_results"][0]["output"] == "ccs-live-ok\n"
    assert payload["role_results"][1]["runner"] == "claude"
    assert "role=implementer profile 'missing-profile' is not available via ccs" in payload["role_results"][1]["fallback_reason"]
    assert "role=implementer profile 'missing-profile' is not available via ccs" in result.stdout
    assert payload["role_results"][1]["output"] == "claude-live-ok\n"
