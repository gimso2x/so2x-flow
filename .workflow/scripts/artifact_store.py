from __future__ import annotations

import json
from pathlib import Path

from artifact_schema import validate_artifact, write_json


def save_task_payload(project_root: Path, payload: dict) -> Path | None:
    artifacts = payload.get("artifacts") or []
    mode = payload.get("mode") or "run"
    stem = "run"
    if mode == "doctor":
        target_path = project_root / ".workflow" / "outputs" / "doctor" / "status.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(target_path, payload)
        return target_path
    if artifacts:
        first_artifact = Path(artifacts[0])
        if first_artifact.suffix == ".json":
            stem = first_artifact.stem
    target_path = project_root / ".workflow" / "outputs" / str(mode) / f"{stem}.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(target_path, payload)
    return target_path


def write_initial_task(path: Path, content: dict, preserve_existing: bool = False) -> None:
    validate_artifact("init", content)
    if preserve_existing and path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        validate_artifact("init", existing)
        merged = {**existing}
        merged.setdefault("title", content["title"])
        answers = existing.get("answers")
        has_answers = bool(answers)
        merged["status"] = existing.get("status", "needs_user_input") if has_answers else "needs_user_input"
        merged["questions"] = content["questions"]
        merged["next_step_prompt"] = content["next_step_prompt"]
        validate_artifact("init", merged)
        write_json(path, merged)
        return
    write_json(path, content)


def write_plan_task(path: Path, content: dict) -> None:
    validate_artifact("plan", content)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        validate_artifact("plan", existing)
        if existing.get("approved") is True:
            content["approved"] = True
        if existing.get("status") == "approved":
            content["status"] = "approved"
    validate_artifact("plan", content)
    write_json(path, content)
