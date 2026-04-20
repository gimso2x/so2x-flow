from __future__ import annotations

from workflow_contracts import contract_for_mode
from artifact_schema import validate_artifact


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
        "related_docs": list(contract_for_mode("feature").required_docs) + ["DESIGN.md"],
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
    questions = [
        {"id": "project_name", "question": "프로젝트 이름이 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
        {"id": "goal", "question": "이 프로젝트의 핵심 목표 한 줄은 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
        {"id": "users", "question": "주요 사용자는 누구인가요?", "target_doc": ".workflow/docs/PRD.md"},
        {"id": "scope", "question": "이번 버전에 꼭 포함할 범위는 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
        {"id": "out_of_scope", "question": "이번 버전에서 하지 않을 범위는 무엇인가요?", "target_doc": ".workflow/docs/PRD.md"},
        {"id": "architecture", "question": "예상 기술 스택이나 구조 제약이 있나요?", "target_doc": ".workflow/docs/ARCHITECTURE.md"},
        {"id": "qa", "question": "초기 QA에서 가장 먼저 확인해야 할 시나리오는 무엇인가요?", "target_doc": ".workflow/docs/QA.md"},
        {"id": "design", "question": "디자인/UX 기준이 있나요? 없으면 원하는 분위기를 알려주세요.", "target_doc": "DESIGN.md"},
    ]
    answers: dict[str, str] = {}
    init_mode_options = [
        "auto-fill-now",
        "ask-first",
    ]
    pending_questions = [item["id"] for item in questions]
    return validate_artifact("init", {
        "title": request,
        "status": "needs_user_input",
        "questions": questions,
        "answers": answers,
        "pending_questions": pending_questions,
        "current_question_id": None,
        "init_mode_options": init_mode_options,
        "selected_init_mode": "ask-first",
        "next_mode_prompt": "먼저 방식을 골라주세요: 1. 자동채우기 2. 질문",
        "next_step_prompt": "먼저 1번(자동채우기) 또는 2번(질문) 중 하나를 골라주세요.",
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
