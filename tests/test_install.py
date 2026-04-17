import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / ".workflow" / "scripts" / "install.py"


def run_install(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(target), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def test_install_copies_flow_scaffold_into_target_project(tmp_path: Path):
    target = tmp_path / "app"
    result = run_install(target)
    assert "copied_count:" in result.stdout
    assert (target / ".claude" / "commands" / "flow-init.md").exists()
    assert (target / ".claude" / "skills" / "flow-feature.md").exists()
    assert (target / ".workflow" / "config" / "ccs-map.yaml").exists()
    assert (target / ".workflow" / "docs" / "PRD.md").exists()
    assert (target / ".workflow" / "prompts" / "planner.md").exists()
    assert (target / ".workflow" / "tasks" / "feature" / "_template.md").exists()
    assert (target / ".workflow" / "scripts" / "execute.py").exists()
    assert (target / "DESIGN.md").exists()
    settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert settings["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["type"] == "command"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == ".workflow/scripts/hooks/dangerous-cmd-guard.sh"


def test_install_does_not_overwrite_existing_files_without_force(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("keep me\n", encoding="utf-8")
    run_install(target)
    assert existing.read_text(encoding="utf-8") == "keep me\n"


def test_install_force_overwrites_existing_files(tmp_path: Path):
    target = tmp_path / "app"
    target.mkdir()
    existing = target / "CLAUDE.md"
    existing.write_text("old\n", encoding="utf-8")
    run_install(target, "--force")
    assert "so2x-flow workspace guide" in existing.read_text(encoding="utf-8")


def test_install_does_not_copy_generated_task_artifacts(tmp_path: Path):
    target = tmp_path / "app"
    run_install(target)
    assert not (target / ".workflow" / "tasks" / "feature" / "로그인-기능-구현.md").exists()
    assert not (target / ".workflow" / "tasks" / "qa" / "qa-001-홈-버튼-클릭-안됨.md").exists()