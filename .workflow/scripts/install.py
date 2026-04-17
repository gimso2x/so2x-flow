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
    "CLAUDE.md",
    "DESIGN.md",
]
SKIP_NAMES = {"__pycache__", ".git", ".pytest_cache", "outputs", "tests", "README.md"}
TASK_TEMPLATE_NAMES = {"_template.md"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install so2x-flow into a target project")
    parser.add_argument("--target", default=".", help="Target project root (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    parts = path.parts
    if ".workflow" in parts and "outputs" in parts:
        return True
    if len(parts) >= 4 and parts[0] == ".workflow" and parts[1] == "tasks" and path.name not in TASK_TEMPLATE_NAMES:
        return True
    return any(part in SKIP_NAMES for part in path.parts)


def copy_file(src: Path, dst: Path, force: bool) -> bool:
    if should_skip(src):
        return False
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def install_tree(target_root: Path, force: bool) -> list[str]:
    copied: list[str] = []

    for rel in COPY_FILES:
        src = SOURCE_ROOT / rel
        dst = target_root / rel
        if copy_file(src, dst, force):
            copied.append(rel)

    for rel_dir in COPY_DIRS:
        src_root = SOURCE_ROOT / rel_dir
        for src in sorted(src_root.rglob("*")):
            if src.is_dir() or should_skip(src.relative_to(SOURCE_ROOT)):
                continue
            rel = src.relative_to(SOURCE_ROOT)
            dst = target_root / rel
            if copy_file(src, dst, force):
                copied.append(rel.as_posix())

    return copied


def main() -> int:
    args = parse_args()
    target_root = Path(args.target).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    copied = install_tree(target_root, force=args.force)
    print(f"target: {target_root}")
    print(f"copied_count: {len(copied)}")
    for item in copied:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())