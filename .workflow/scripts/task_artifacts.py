from __future__ import annotations

import json
from pathlib import Path

ARTIFACT_SCHEMAS = {
    "feature": {
        "title": str,
        "summary": str,
        "context": list,
        "related_docs": list,
        "latest_approved_flow_plan_output": str,
        "approved_direction": dict,
        "approval_gate": list,
        "implementation_slice": list,
        "relevant_files": list,
        "out_of_scope": list,
        "proposed_steps": list,
        "acceptance": list,
        "verification": list,
        "follow_up_slice": list,
        "next_step_prompt": str,
    },
    "qa": {
        "title": str,
        "issue_summary": str,
        "qa_id": str,
        "references": list,
        "reproduction": list,
        "expected": list,
        "actual": list,
        "suspected_scope": list,
        "minimal_fix": list,
        "regression_checklist": list,
    },
    "review": {
        "title": str,
        "related_docs": list,
        "review_focus": list,
        "findings": list,
        "next_step_prompt": str,
    },
    "init": {
        "title": str,
        "status": str,
        "questions": list,
        "next_step_prompt": str,
    },
    "plan": {
        "request": str,
        "status": str,
        "approved": bool,
        "related_docs": list,
        "context_snapshot": str,
        "open_questions": list,
        "options": dict,
        "recommendation": str,
        "draft_plan": list,
        "approval_gate": list,
        "next_step_prompt": str,
    },
}


def validate_artifact(kind: str, payload: dict) -> dict:
    schema = ARTIFACT_SCHEMAS.get(kind)
    if schema is None:
        raise ValueError(f"unsupported artifact kind: {kind}")
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} artifact must be a dict")
    for field, expected_type in schema.items():
        if field not in payload:
            raise ValueError(f"{kind} missing required field: {field}")
        if not isinstance(payload[field], expected_type):
            raise ValueError(f"{kind} field '{field}' must be of type {expected_type.__name__}")
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_feature_task(request: str, approved_plan_path: str | None = None) -> dict:
    plan_ref = approved_plan_path or "(none matched request)"
    if approved_plan_path:
        next_step_prompt = "승인된 방향이 있으니, 이번 slice를 진행할까요? (y/n)"
        approval_hint = "승인된 방향이 있으니 이번 실행 여부만 확인하고, 새 범위 제안은 덧붙이지 않는다."
    else:
        next_step_prompt = "이 요청은 아직 승인된 방향이 없으니, /flow-plan으로 먼저 범위를 확정할까요? (y/n)"
        approval_hint = "승인된 plan이 없으면 여기서 멈추고 /flow-plan으로 먼저 범위를 확정할지 묻는다."
    return validate_artifact("feature", {
        "title": request,
        "summary": f"Requested feature: {request}",
        "context": ["Capture user-facing context and constraints here."],
        "related_docs": [
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
            "DESIGN.md",
        ],
        "latest_approved_flow_plan_output": plan_ref,
        "approved_direction": {
            "summary": "Summarize the agreed direction from flow-plan or the latest approval note.",
            "source_plan_artifact": approved_plan_path or "(none)",
        },
        "approval_gate": [approval_hint],
        "implementation_slice": ["Define the smallest implementation slice for this run."],
        "relevant_files": ["List candidate files to inspect or modify."],
        "out_of_scope": ["Explicitly list what this task will not change."],
        "proposed_steps": [
            "Confirm the approved direction and implementation slice.",
            "Identify the smallest implementation change.",
            "Implement and verify the slice.",
        ],
        "acceptance": ["Define the minimum accepted outcome for this slice."],
        "verification": ["List the checks required before considering this slice done."],
        "follow_up_slice": ["Describe the next smallest slice after this one."],
        "next_step_prompt": next_step_prompt,
    })


def render_qa_task(request: str, qa_id: str | None) -> dict:
    qa_label = qa_id or "QA-TBD"
    return validate_artifact("qa", {
        "title": request,
        "issue_summary": "Summarize the bug and affected user flow.",
        "qa_id": qa_label,
        "references": [
            ".workflow/docs/QA.md",
            "Related screenshots, issues, or logs if available.",
        ],
        "reproduction": ["Describe how to reproduce the issue."],
        "expected": ["Describe the intended behavior."],
        "actual": ["Describe the current broken behavior."],
        "suspected_scope": ["List the likely files, modules, or UI areas involved."],
        "minimal_fix": ["Describe the smallest safe repair."],
        "regression_checklist": [
            "Original issue no longer reproduces",
            "Adjacent flow still works",
            "No broader scope added without approval",
        ],
    })


def render_review_task(request: str, docs_used: list[str], task: str | None = None) -> dict:
    payload = {
        "title": request,
        "related_docs": docs_used,
        "related_task": task,
        "review_focus": [
            "Spec Gap",
            "Architecture Concern",
            "Test Gap",
            "QA Watchpoints",
        ],
        "findings": [],
        "next_step_prompt": "이 리뷰 결과를 기준으로 후속 수정이 필요할까요? (y/n)",
    }
    validate_artifact("review", payload)
    return payload


def render_init_task(request: str) -> dict:
    return validate_artifact("init", {
        "title": request,
        "status": "needs_user_input",
        "questions": [
            {"id": "project_name", "question": "프로젝트 이름이 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
            {"id": "goal", "question": "이 프로젝트의 핵심 목표 한 줄은 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
            {"id": "users", "question": "주요 사용자는 누구인가요?", "target_doc": ".workflow/docs/PRD.md"},
            {"id": "scope", "question": "이번 버전에 꼭 포함할 범위는 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
            {"id": "out_of_scope", "question": "이번 버전에서 하지 않을 범위는 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
            {"id": "architecture", "question": "예상 기술 스택이나 구조 제약이 있나요?", "target_doc": ".workflow/docs/ARCHITECTURE.md"},
            {"id": "qa", "question": "초기 QA에서 가장 먼저 확인해야 할 시나리오는 무엇인가요?", "target_doc": ".workflow/docs/QA.md"},
            {"id": "design", "question": "디자인/UX 기준이 있나요? 없으면 원하는 분위기를 알려주세요.", "target_doc": "DESIGN.md"},
        ],
        "next_step_prompt": "위 질문들에 답해주면 flow-init이 문서를 하나씩 채워갈게요.",
    })


def render_plan_doc(request: str, docs_used: list[str]) -> dict:
    return validate_artifact("plan", {
        "request": request,
        "status": "draft",
        "approved": False,
        "related_docs": docs_used,
        "context_snapshot": "현재 프로젝트 구조와 관련 문서를 기준으로 핵심 맥락을 요약한다.",
        "open_questions": ["한 번에 하나씩 확인이 필요한 질문을 적는다."],
        "options": {
            "Option A": ["가장 작은 MVP 접근"],
            "Option B": ["상호작용이나 범위를 조금 더 포함한 접근"],
        },
        "recommendation": "추천안을 한 줄로 명시하고 이유를 붙인다.",
        "draft_plan": [
            "컨텍스트를 확인한다.",
            "범위를 분해한다.",
            "질문과 대안을 정리한다.",
            "추천안을 기준으로 설계 초안을 확정한다.",
            "구현 전 검증 기준을 적는다.",
        ],
        "approval_gate": [
            "이 설계 방향 자체를 확정할지 사용자 승인을 요청한다.",
            "승인 전에는 /flow-feature로 자동 전환하거나 다음 실행을 기정사실화하지 않는다.",
        ],
        "next_step_prompt": "이 설계 방향으로 확정할까요? (y/n)",
    })


def save_task_payload(project_root: Path, payload: dict) -> Path | None:
    artifacts = payload.get("artifacts") or []
    if not artifacts or not artifacts[0].endswith(".json"):
        return None
    target_path = project_root / artifacts[0]
    existing = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else {}
    merged = {**existing, **payload}
    if payload.get("mode") == "plan" and existing:
        if existing.get("approved") is True:
            merged["approved"] = True
        if existing.get("status") == "approved":
            merged["status"] = "approved"
    target_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
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
