from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATED_PATHS = [
    ROOT / ".workflow" / "scripts" / "__pycache__",
    ROOT / "tests" / "__pycache__",
    ROOT / ".workflow" / "tasks" / "feature" / "로그인-기능-구현.json",
    ROOT / ".workflow" / "tasks" / "feature" / "세션-만료-처리.json",
    ROOT / ".workflow" / "tasks" / "feature" / "프로필-편집.json",
    ROOT / ".workflow" / "tasks" / "qa" / "qa-001-홈-버튼-클릭-안됨.json",
    ROOT / ".workflow" / "tasks" / "qa" / "qa-009-토글-오동작.json",
]


def _cleanup_generated_files() -> None:
    for path in GENERATED_PATHS:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()


@pytest.fixture(autouse=True)
def cleanup_generated_artifacts():
    _cleanup_generated_files()
    yield
    _cleanup_generated_files()
