import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / ".workflow" / "scripts" / "install.py"


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(workspace), "--patch-claude-md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return workspace


def run_execute(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    execute = workspace / ".workflow" / "scripts" / "execute.py"
    return subprocess.run(
        [sys.executable, str(execute), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )


def make_sample_target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-target"
    repo.mkdir()
    (repo / "README.md").write_text("# sample target\n", encoding="utf-8")
    (repo / "app.py").write_text("print('sample app')\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("# local target guide\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Hermes"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "hermes@example.com"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(["git", "commit", "-m", "chore: sample target bootstrap"], cwd=repo, capture_output=True, text=True, check=True)
    subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(repo), "--patch-claude-md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return repo


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def output_path(workspace: Path, stdout: str, label: str) -> Path:
    prefix = f"{label}: "
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return workspace / line[len(prefix) :]
    raise AssertionError(f"Could not find {label} in stdout:\n{stdout}")
