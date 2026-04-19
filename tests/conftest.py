from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIRS = [
    ROOT / ".workflow" / "scripts" / "__pycache__",
    ROOT / "tests" / "__pycache__",
    ROOT / ".workflow" / "outputs",
]
TASK_TEMPLATE_NAMES = {"_template.json", ".gitkeep"}
TASK_DIRS = [
    ROOT / ".workflow" / "tasks" / "feature",
    ROOT / ".workflow" / "tasks" / "init",
    ROOT / ".workflow" / "tasks" / "plan",
    ROOT / ".workflow" / "tasks" / "qa",
    ROOT / ".workflow" / "tasks" / "review",
]


def _cleanup_generated_files() -> None:
    for path in GENERATED_DIRS:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
    for task_dir in TASK_DIRS:
        if not task_dir.exists():
            continue
        for path in task_dir.glob("*.json"):
            if path.name in TASK_TEMPLATE_NAMES:
                continue
            path.unlink()


@pytest.fixture(autouse=True)
def cleanup_generated_artifacts():
    _cleanup_generated_files()
    yield
    _cleanup_generated_files()
