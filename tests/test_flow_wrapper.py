import subprocess
import sys
from pathlib import Path

from execute_helpers import ROOT, make_workspace, output_path, read_json


def run_flow(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    flow = workspace / "flow.py"
    return subprocess.run(
        [sys.executable, str(flow), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )


def test_flow_wrapper_is_installed_and_supports_doctor_shortcuts(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    assert (workspace / "flow.py").exists()

    brief = run_flow(workspace, "doctor", "--brief")
    assert "next=/flow-init" in brief.stdout

    json_only = run_flow(workspace, "status", "--json")
    assert json_only.stdout.strip() == ".workflow/outputs/doctor/status.json"


def test_flow_wrapper_runs_execute_modes_and_persists_plan_output(tmp_path: Path):
    workspace = make_workspace(tmp_path)

    result = run_flow(workspace, "plan", "로그인 기능 작업 분해", "--dry-run")
    payload = read_json(output_path(workspace, result.stdout, "output_json"))

    assert payload["mode"] == "plan"
    assert payload["request"] == "로그인 기능 작업 분해"
    assert payload["artifacts"] == [".workflow/tasks/plan/로그인-기능-작업-분해.json"]


def test_codex_wrapper_is_documented_in_repo_surfaces():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    patch_agents = (ROOT / ".workflow" / "scripts" / "patch_agents_md.py").read_text(encoding="utf-8")
    install = (ROOT / ".workflow" / "scripts" / "install.py").read_text(encoding="utf-8")
    prd = (ROOT / ".workflow" / "docs" / "PRD.md").read_text(encoding="utf-8")
    architecture = (ROOT / ".workflow" / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert '"flow.py",' in install
    assert "### Codex에서 바로 쓰기" in readme
    assert "python3 flow.py doctor --brief" in readme
    assert "python3 flow.py status --json" in readme
    assert "python3 flow.py <mode> ..." in agents
    assert "python3 flow.py status --brief" in patch_agents
    assert "Thin root `flow.py` wrapper for Codex or shell users" in prd
    assert "- `flow.py`: root convenience wrapper for Codex/CLI use" in architecture
