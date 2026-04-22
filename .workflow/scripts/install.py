#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
COPY_DIRS = [
    ".claude",
    ".workflow",
]
COPY_FILES = [
    "AGENTS.md",
    "DESIGN.md",
]
SKIP_NAMES = {"__pycache__", ".git", ".pytest_cache", "outputs", "tests", "README.md"}
TASK_TEMPLATE_NAMES = {"_template.json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install so2x-flow into a target project")
    parser.add_argument("--target", default=".", help="Target project root (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--patch-agents-md", action="store_true", help="Append a so2x-flow section to target AGENTS.md if missing")
    parser.add_argument("--patch-claude-md", action="store_true", help="Append a so2x-flow section to target CLAUDE.md if missing")
    parser.add_argument(
        "--verbose-copied-files",
        action="store_true",
        help="Print every copied path after the install summary",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    parts = path.parts
    if ".workflow" in parts and "outputs" in parts:
        return True
    if len(parts) >= 4 and parts[0] == ".workflow" and parts[1] == "tasks" and path.name not in TASK_TEMPLATE_NAMES:
        return True
    return any(part in SKIP_NAMES for part in path.parts)


def copy_file(src: Path, dst: Path, force: bool) -> str:
    if not src.exists():
        return "missing"
    if should_skip(src):
        return "skipped"
    if dst.exists() and not force:
        return "existing"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "copied"


def install_tree(target_root: Path, force: bool) -> dict[str, list[str]]:
    copied: list[str] = []
    skipped_existing: list[str] = []
    skipped_missing: list[str] = []

    for rel in COPY_FILES:
        src = SOURCE_ROOT / rel
        dst = target_root / rel
        status = copy_file(src, dst, force)
        if status == "copied":
            copied.append(rel)
        elif status == "existing":
            skipped_existing.append(rel)
        elif status == "missing":
            skipped_missing.append(rel)

    for rel_dir in COPY_DIRS:
        src_root = SOURCE_ROOT / rel_dir
        for src in sorted(src_root.rglob("*")):
            if src.is_dir() or should_skip(src.relative_to(SOURCE_ROOT)):
                continue
            rel = src.relative_to(SOURCE_ROOT)
            rel_posix = rel.as_posix()
            dst = target_root / rel
            status = copy_file(src, dst, force)
            if status == "copied":
                copied.append(rel_posix)
            elif status == "existing":
                skipped_existing.append(rel_posix)
            elif status == "missing":
                skipped_missing.append(rel_posix)

    return {
        "copied": copied,
        "skipped_existing": skipped_existing,
        "skipped_missing": skipped_missing,
    }


def patch_claude_md(target_root: Path) -> bool:
    from patch_claude_md import patch_claude_md as apply_patch

    return apply_patch(target_root)


def patch_agents_md(target_root: Path) -> bool:
    from patch_agents_md import patch_agents_md as apply_patch

    return apply_patch(target_root)


def verify_install(target_root: Path) -> list[str]:
    required = [
        ".claude/skills/flow-init.md",
        ".workflow/scripts/execute.py",
        ".workflow/scripts/doctor.py",
        ".workflow/config/ccs-map.yaml",
    ]
    missing = [rel for rel in required if not (target_root / rel).exists()]
    return missing


def main() -> int:
    args = parse_args()
    target_root = Path(args.target).resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    print("step 1/4: copy scaffold files")
    install_result = install_tree(target_root, force=args.force)
    copied = install_result["copied"]
    skipped_existing = install_result["skipped_existing"]
    skipped_missing = install_result["skipped_missing"]

    print("step 2/4: verify required files")
    missing = verify_install(target_root)
    if missing:
        for rel in missing:
            print(f"missing: {rel}")
        raise SystemExit(1)

    print("step 3/4: patch agent guides")
    agents_patched = patch_agents_md(target_root) if args.patch_agents_md else False
    claude_patched = patch_claude_md(target_root) if args.patch_claude_md else False
    print(f"agents_md_patched: {agents_patched}")
    print(f"claude_md_patched: {claude_patched}")

    print("step 4/4: install complete")
    print("next_step: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.")
    print("next_step_cli: /flow-init")
    print("next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.")
    print("first_run_path: /flow-init -> /flow-plan -> /flow-feature")
    print(f"target: {target_root}")
    print(f"copied_count: {len(copied)}")
    print(f"skipped_existing_count: {len(skipped_existing)}")
    print(f"skipped_missing_count: {len(skipped_missing)}")
    if args.patch_agents_md:
        print(f"agents_md_status: {'created_or_updated' if agents_patched else 'already_present'}")
    elif (target_root / "AGENTS.md").exists():
        print("agents_md_status: available")
    else:
        print("agents_md_status: not created (rerun with --patch-agents-md to create/update)")
    if args.patch_claude_md:
        print(f"claude_md_status: {'created_or_updated' if claude_patched else 'already_present'}")
    else:
        print("claude_md_status: not created (rerun with --patch-claude-md to create/update)")
    if args.verbose_copied_files:
        print("copied_files:")
        for item in copied:
            print(item)
    else:
        print("copied_files: hidden (rerun with --verbose-copied-files to inspect each path)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
