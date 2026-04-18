import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".workflow" / "scripts" / "release_handoff.py"
SPEC = importlib.util.spec_from_file_location("so2x_flow_release_handoff", SCRIPT)
release_handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(release_handoff)


def run_script(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_release_handoff_generates_pr_named_markdown_from_git_range(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Hermes")
    git(repo, "config", "user.email", "hermes@example.com")

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "chore: base")
    git(repo, "branch", "base")

    (repo / ".workflow" / "scripts").mkdir(parents=True)
    (repo / ".workflow" / "scripts" / "execute.py").write_text("print('ok')\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_smoke.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "README.md").write_text("updated\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "feat: add releaseable workflow update")

    result = run_script(repo, "--base-ref", "base", "--head-ref", "HEAD", "--output-dir", str(repo), "--pr-number", "7")

    notes = (repo / "RELEASE_NOTES_PR7.md").read_text(encoding="utf-8")
    body = (repo / "RELEASE_BODY_PR7.md").read_text(encoding="utf-8")
    assert "notes_path:" in result.stdout
    assert "body_path:" in result.stdout
    assert "commit_count: 1" in result.stdout
    assert "changed_file_count: 3" in result.stdout
    assert "# Release Notes — PR #7" in notes
    assert "## Commits" in notes
    assert "feat: add releaseable workflow update" in notes
    assert "### workflow scripts" in notes
    assert "`.workflow/scripts/execute.py`" in notes
    assert "### tests" in notes
    assert "`tests/test_smoke.py`" in notes
    assert "### repo docs" in notes
    assert "`README.md`" in notes
    assert "## Latest commits" in body
    assert "## Highlights" in body
    assert "- workflow scripts: `.workflow/scripts/execute.py`" in body
    assert "```bash\npython3 -m pytest -q\n```" in body


def test_release_handoff_handles_empty_diff_range(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Hermes")
    git(repo, "config", "user.email", "hermes@example.com")

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "chore: base")

    run_script(repo, "--base-ref", "HEAD", "--head-ref", "HEAD", "--output-dir", str(repo))

    notes = (repo / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    body = (repo / "RELEASE_BODY.md").read_text(encoding="utf-8")
    assert "No commits found between `HEAD` and `HEAD`." in notes
    assert "## Latest commits\n- (none)" in body


def test_release_handoff_can_publish_pr_body_with_explicit_pr_number(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    body_path = output_dir / "RELEASE_BODY.md"
    body_path.write_text("body\n", encoding="utf-8")

    args = release_handoff.parse_args.__globals__["argparse"].Namespace(
        publish_pr_number=12,
        pr_number=None,
    )

    with patch.object(release_handoff, "run_command") as run_command:
        resolved = release_handoff.resolve_publish_pr_number(tmp_path, args)
        release_handoff.publish_pr_body(tmp_path, resolved, body_path)

    assert resolved == 12
    run_command.assert_called_once_with(tmp_path, "gh", "pr", "edit", "12", "--body-file", str(body_path))


def test_release_handoff_resolves_current_pr_number_when_publishing(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    body_path = output_dir / "RELEASE_BODY.md"
    body_path.write_text("body\n", encoding="utf-8")

    args = release_handoff.parse_args.__globals__["argparse"].Namespace(
        publish_pr_number=None,
        pr_number=None,
    )

    with patch.object(release_handoff, "gh_json", return_value={"number": 34}) as gh_json, patch.object(release_handoff, "run_command") as run_command:
        resolved = release_handoff.resolve_publish_pr_number(tmp_path, args)
        release_handoff.publish_pr_body(tmp_path, resolved, body_path)

    assert resolved == 34
    gh_json.assert_called_once_with(tmp_path, "pr", "view", "--json", "number")
    run_command.assert_called_once_with(tmp_path, "gh", "pr", "edit", "34", "--body-file", str(body_path))
