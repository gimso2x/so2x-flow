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
        selected_mode = existing.get("selected_init_mode", content["selected_init_mode"])
        if selected_mode == "auto-fill-now":
            base_answers = {"project_name": content["title"], "goal": content["title"]}
            merged_answers = {**base_answers, **existing.get("answers", {})}
            pending_questions = [item["id"] for item in content["questions"] if item["id"] not in merged_answers]
            if pending_questions:
                merged_status = existing.get("status", content["status"])
                if merged_status == "approved":
                    status = "approved"
                elif merged_status == "in_progress" and existing.get("answers"):
                    status = "in_progress"
                elif merged_answers:
                    status = "draft_auto_filled"
                else:
                    status = "needs_user_input"
            else:
                status = "ready_for_review"
            next_step_prompt = "자동으로 채운 초안을 확인했고, 남은 질문은 한 번에 하나씩 이어서 물어보면 돼요."
            current_question_id = pending_questions[0] if pending_questions else None
        elif selected_mode == "auto-fill-after-work":
            merged_answers = existing.get("answers", {})
            pending_questions = [item["id"] for item in content["questions"] if item["id"] not in merged_answers]
            status = "in_progress"
            current_question_id = None
            next_step_prompt = "작업을 먼저 진행하세요. 구현 맥락이 쌓인 뒤 init 초안을 자동으로 채웁니다."
        else:
            merged_answers = existing.get("answers", {})
            pending_questions = [item["id"] for item in content["questions"] if item["id"] not in merged_answers]
            status = existing.get("status", "needs_user_input") if merged_answers else "needs_user_input"
            current_question_id = None
            next_step_prompt = "먼저 초기화 방식을 골라주세요. 기본값은 질문부터 시작입니다."
        merged["status"] = status
        merged["questions"] = content["questions"]
        merged["answers"] = merged_answers
        merged["pending_questions"] = pending_questions
        merged["current_question_id"] = current_question_id
        merged["init_mode_options"] = content["init_mode_options"]
        merged["selected_init_mode"] = selected_mode
        merged["next_mode_prompt"] = content["next_mode_prompt"]
        merged["next_step_prompt"] = next_step_prompt
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
