#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from collections import OrderedDict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release notes and PR handoff body from git history")
    parser.add_argument("--base-ref", default="origin/main", help="Base git ref to diff against (default: origin/main)")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref to summarize (default: HEAD)")
    parser.add_argument("--output-dir", default=".", help="Directory to write generated markdown files")
    parser.add_argument("--pr-number", type=int, help="Optional PR number used in output filenames and title")
    parser.add_argument("--title", help="Optional release title override")
    parser.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--publish-pr-body", action="store_true", help="Publish generated PR body to GitHub via gh pr edit")
    parser.add_argument("--publish-pr-number", type=int, help="Explicit PR number to publish with gh pr edit")
    parser.add_argument("--create-pr", action="store_true", help="Create a PR with gh pr create using the generated body")
    parser.add_argument("--draft", action="store_true", help="Create PR as draft when used with --create-pr")
    parser.add_argument("--base-branch", help="Base branch for gh pr create")
    parser.add_argument("--head-branch", help="Head branch for gh pr create")
    parser.add_argument("--watch-checks", action="store_true", help="Watch PR checks with gh pr checks --watch")
    return parser.parse_args()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def run_command(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def gh_json(repo: Path, *args: str) -> Any:
    result = run_command(repo, "gh", *args)
    import json

    return json.loads(result.stdout)


def diff_range(base_ref: str, head_ref: str) -> str:
    return f"{base_ref}..{head_ref}"


def collect_commits(repo: Path, base_ref: str, head_ref: str) -> list[str]:
    output = git(repo, "log", "--format=%h %s", diff_range(base_ref, head_ref))
    return [line for line in output.splitlines() if line.strip()]


def collect_changed_files(repo: Path, base_ref: str, head_ref: str) -> list[str]:
    output = git(repo, "diff", "--name-only", diff_range(base_ref, head_ref))
    return [line for line in output.splitlines() if line.strip()]


def classify_files(files: list[str]) -> OrderedDict[str, list[str]]:
    buckets: OrderedDict[str, list[str]] = OrderedDict(
        [
            ("workflow scripts", []),
            ("workflow docs", []),
            ("claude workflow assets", []),
            ("tests", []),
            ("repo docs", []),
            ("other", []),
        ]
    )
    for path in files:
        if path.startswith(".workflow/scripts/"):
            buckets["workflow scripts"].append(path)
        elif path.startswith(".workflow/docs/") or path.startswith(".workflow/prompts/") or path.startswith(".workflow/tasks/"):
            buckets["workflow docs"].append(path)
        elif path.startswith(".claude/") or path == "CLAUDE.md":
            buckets["claude workflow assets"].append(path)
        elif path.startswith("tests/"):
            buckets["tests"].append(path)
        elif path.endswith(".md"):
            buckets["repo docs"].append(path)
        else:
            buckets["other"].append(path)
    return OrderedDict((name, items) for name, items in buckets.items() if items)


def build_summary(commits: list[str], changed_files: list[str], base_ref: str, head_ref: str) -> str:
    if not commits:
        return f"No commits found between `{base_ref}` and `{head_ref}`."
    areas = []
    if any(path.startswith(".workflow/scripts/") for path in changed_files):
        areas.append("workflow scripts")
    if any(path.startswith(".workflow/docs/") or path.startswith(".workflow/tasks/") or path.startswith(".workflow/prompts/") for path in changed_files):
        areas.append("docs-first workflow assets")
    if any(path.startswith("tests/") for path in changed_files):
        areas.append("tests")
    if any(path.endswith(".md") and not path.startswith(".workflow/") for path in changed_files):
        areas.append("README/release docs")
    if not areas:
        areas.append("repo files")
    area_text = ", ".join(areas)
    return f"This handoff summarizes {len(commits)} commit(s) across {area_text} between `{base_ref}` and `{head_ref}`."


def markdown_list(items: list[str], indent: str = "- ") -> str:
    if not items:
        return "- (none)"
    return "\n".join(f"{indent}{item}" for item in items)


def build_release_notes(*, title: str, summary: str, commits: list[str], grouped_files: OrderedDict[str, list[str]], verify_cmd: str) -> str:
    sections = [f"# {title}", "", "## Summary", summary, "", "## Commits", markdown_list(commits)]
    sections.extend(["", "## Changed files"])
    for group_name, files in grouped_files.items():
        sections.append(f"### {group_name}")
        sections.append(markdown_list([f"`{path}`" for path in files]))
        sections.append("")
    sections.extend(["## Verification", "```bash", verify_cmd, "```"])
    return "\n".join(sections).rstrip() + "\n"


def build_release_body(summary: str, commits: list[str], grouped_files: OrderedDict[str, list[str]], verify_cmd: str) -> str:
    highlights = []
    for group_name, files in grouped_files.items():
        preview = ", ".join(f"`{path}`" for path in files[:3])
        if len(files) > 3:
            preview += f" 외 {len(files) - 3}개"
        highlights.append(f"- {group_name}: {preview}")
    sections = ["## Summary", summary, "", "## Latest commits", markdown_list(commits)]
    if highlights:
        sections.extend(["", "## Highlights", *highlights])
    sections.extend(["", "## Verification", "```bash", verify_cmd, "```"])
    return "\n".join(sections).rstrip() + "\n"


def output_paths(output_dir: Path, pr_number: int | None) -> tuple[Path, Path, str]:
    suffix = f"_PR{pr_number}" if pr_number is not None else ""
    title = f"Release Notes — PR #{pr_number}" if pr_number is not None else "Release Notes"
    return output_dir / f"RELEASE_NOTES{suffix}.md", output_dir / f"RELEASE_BODY{suffix}.md", title


def current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current")


def resolve_create_pr_title(args: argparse.Namespace, commits: list[str], head_ref: str) -> str:
    if args.title:
        return args.title
    if commits:
        first = commits[0]
        if " " in first:
            return first.split(" ", 1)[1]
        return first
    return f"handoff: {head_ref}"


def create_pr(repo: Path, args: argparse.Namespace, title: str, body_path: Path) -> int:
    command = ["gh", "pr", "create", "--title", title, "--body-file", str(body_path)]
    if args.draft:
        command.append("--draft")
    if args.base_branch:
        command.extend(["--base", args.base_branch])
    if args.head_branch:
        command.extend(["--head", args.head_branch])
    result = run_command(repo, *command)
    data = gh_json(repo, "pr", "view", "--json", "number")
    number = data.get("number")
    if not isinstance(number, int):
        raise SystemExit(f"Created PR but could not resolve number. Output: {result.stdout.strip()}")
    return number


def watch_pr_checks(repo: Path, pr_number: int) -> None:
    run_command(repo, "gh", "pr", "checks", str(pr_number), "--watch")


def resolve_publish_pr_number(repo: Path, args: argparse.Namespace) -> int:
    if args.publish_pr_number is not None:
        return args.publish_pr_number
    if args.pr_number is not None:
        return args.pr_number
    data = gh_json(repo, "pr", "view", "--json", "number")
    number = data.get("number")
    if not isinstance(number, int):
        raise SystemExit("Could not resolve PR number for `gh pr edit`. Pass --publish-pr-number.")
    return number


def publish_pr_body(repo: Path, pr_number: int, body_path: Path) -> None:
    run_command(repo, "gh", "pr", "edit", str(pr_number), "--body-file", str(body_path))


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    commits = collect_commits(repo, args.base_ref, args.head_ref)
    changed_files = collect_changed_files(repo, args.base_ref, args.head_ref)
    grouped_files = classify_files(changed_files)
    summary = build_summary(commits, changed_files, args.base_ref, args.head_ref)
    notes_path, body_path, default_title = output_paths(output_dir, args.pr_number)
    title = args.title or default_title
    verify_cmd = "python3 -m pytest -q"

    notes = build_release_notes(
        title=title,
        summary=summary,
        commits=commits,
        grouped_files=grouped_files,
        verify_cmd=verify_cmd,
    )
    body = build_release_body(
        summary=summary,
        commits=commits,
        grouped_files=grouped_files,
        verify_cmd=verify_cmd,
    )
    notes_path.write_text(notes, encoding="utf-8")
    body_path.write_text(body, encoding="utf-8")

    publish_pr_number: int | None = None
    if args.create_pr:
        create_title = resolve_create_pr_title(args, commits, args.head_ref)
        publish_pr_number = create_pr(repo, args, create_title, body_path)
    elif args.publish_pr_body:
        publish_pr_number = resolve_publish_pr_number(repo, args)
        publish_pr_body(repo, publish_pr_number, body_path)

    if args.watch_checks:
        if publish_pr_number is None:
            publish_pr_number = resolve_publish_pr_number(repo, args)
        watch_pr_checks(repo, publish_pr_number)

    print(f"notes_path: {notes_path}")
    print(f"body_path: {body_path}")
    print(f"commit_count: {len(commits)}")
    print(f"changed_file_count: {len(changed_files)}")
    print(f"current_branch: {current_branch(repo)}")
    if args.create_pr:
        print("created_pr: true")
        print(f"created_pr_number: {publish_pr_number}")
    else:
        print("created_pr: false")
    if args.publish_pr_body:
        print(f"published_pr_body: true")
        print(f"published_pr_number: {publish_pr_number}")
    else:
        print("published_pr_body: false")
    print(f"watched_checks: {args.watch_checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
