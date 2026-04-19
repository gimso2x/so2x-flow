from __future__ import annotations

import json

ARTIFACT_SCHEMAS = {
    "doctor": {
        "mode": str,
        "overall_status": str,
        "exact_status": str,
        "blocked_reason": (str, type(None)),
        "latest_summary": str,
        "latest_output_json": (str, type(None)),
        "latest_outputs": dict,
        "latest_tasks": dict,
    },
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

INIT_ALLOWED_STATUSES = {"needs_user_input", "in_progress", "approved"}
PLAN_ALLOWED_STATUSES = {"draft", "approved", "in_progress", "needs_user_input"}
DOCTOR_ALLOWED_OVERALL_STATUSES = {"idle", "ok", "blocked", "waiting"}


def _require_string_list(kind: str, field: str, values: object) -> None:
    if not isinstance(values, list):
        raise ValueError(f"{kind} field '{field}' must be of type list")
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValueError(f"{kind} {field}[{index}] must be a str")


def _validate_init_questions(payload: dict) -> None:
    questions = payload["questions"]
    if not isinstance(questions, list):
        raise ValueError("init field 'questions' must be of type list")
    for index, item in enumerate(questions):
        if not isinstance(item, dict):
            raise ValueError(f"init questions[{index}] must be a dict")
        for key in ("id", "question", "target_doc"):
            if key not in item:
                raise ValueError(f"init questions[{index}] missing required field: {key}")
            if not isinstance(item[key], str):
                raise ValueError(f"init questions[{index}] field '{key}' must be a str")


def _validate_feature_nested(payload: dict) -> None:
    for field in (
        "context",
        "related_docs",
        "approval_gate",
        "implementation_slice",
        "relevant_files",
        "out_of_scope",
        "proposed_steps",
        "acceptance",
        "verification",
        "follow_up_slice",
    ):
        _require_string_list("feature", field, payload[field])
    approved_direction = payload["approved_direction"]
    if not isinstance(approved_direction, dict):
        raise ValueError("feature field 'approved_direction' must be of type dict")
    for key in ("summary", "source_plan_artifact"):
        if key not in approved_direction:
            raise ValueError(f"feature approved_direction missing required field: {key}")
        if not isinstance(approved_direction[key], str):
            raise ValueError(f"feature approved_direction field '{key}' must be a str")


def _validate_plan_nested(payload: dict) -> None:
    if payload["status"] not in PLAN_ALLOWED_STATUSES:
        raise ValueError(f"plan field 'status' must be one of {sorted(PLAN_ALLOWED_STATUSES)}")
    for field in ("related_docs", "open_questions", "draft_plan", "approval_gate"):
        _require_string_list("plan", field, payload[field])
    options = payload["options"]
    if not isinstance(options, dict):
        raise ValueError("plan field 'options' must be of type dict")
    for key, value in options.items():
        if not isinstance(key, str):
            raise ValueError("plan options keys must be str")
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"plan options['{key}'] must be a list[str]")


def _validate_qa_nested(payload: dict) -> None:
    for field in ("references", "reproduction", "expected", "actual", "suspected_scope", "minimal_fix", "regression_checklist"):
        _require_string_list("qa", field, payload[field])


def _validate_review_nested(payload: dict) -> None:
    for field in ("related_docs", "review_focus"):
        _require_string_list("review", field, payload[field])
    findings = payload["findings"]
    if not isinstance(findings, list):
        raise ValueError("review field 'findings' must be of type list")
    for index, item in enumerate(findings):
        if not isinstance(item, (str, dict)):
            raise ValueError(f"review findings[{index}] must be a str or dict")


def _validate_init_nested(payload: dict) -> None:
    if payload["status"] not in INIT_ALLOWED_STATUSES:
        raise ValueError(f"init field 'status' must be one of {sorted(INIT_ALLOWED_STATUSES)}")
    _validate_init_questions(payload)


def _validate_doctor_nested(payload: dict) -> None:
    if payload["mode"] != "doctor":
        raise ValueError("doctor field 'mode' must equal 'doctor'")
    if payload["overall_status"] not in DOCTOR_ALLOWED_OVERALL_STATUSES:
        raise ValueError(f"doctor field 'overall_status' must be one of {sorted(DOCTOR_ALLOWED_OVERALL_STATUSES)}")
    if not payload["exact_status"]:
        raise ValueError("doctor field 'exact_status' must be a non-empty str")
    for field in ("latest_outputs", "latest_tasks"):
        mapping = payload[field]
        if not isinstance(mapping, dict):
            raise ValueError(f"doctor field '{field}' must be of type dict")
        for key, value in mapping.items():
            if not isinstance(key, str):
                raise ValueError(f"doctor {field} keys must be str")
            if not isinstance(value, str):
                raise ValueError(f"doctor {field}['{key}'] must be a str")
    last_event = payload.get("last_event")
    if last_event is not None and not isinstance(last_event, dict):
        raise ValueError("doctor field 'last_event' must be of type dict")


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
            if isinstance(expected_type, tuple):
                names = " | ".join(item.__name__ for item in expected_type)
                raise ValueError(f"{kind} field '{field}' must be of type {names}")
            raise ValueError(f"{kind} field '{field}' must be of type {expected_type.__name__}")
    if kind == "doctor":
        _validate_doctor_nested(payload)
    if kind == "feature":
        _validate_feature_nested(payload)
    elif kind == "qa":
        _validate_qa_nested(payload)
    elif kind == "review":
        _validate_review_nested(payload)
    elif kind == "init":
        _validate_init_nested(payload)
    elif kind == "plan":
        _validate_plan_nested(payload)
    return payload


def write_json(path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
