#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_ROOT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ccs_runner import resolve_runner, run_role, run_role_subprocess

CONFIG_PATH = WORKFLOW_ROOT / "config" / "ccs-map.yaml"
PLAN_TASKS = WORKFLOW_ROOT / "tasks" / "plan"
PROMPTS_DIR = WORKFLOW_ROOT / "prompts"

MODE_ALIASES = {
    "qa-fix": "qa",
    "plan-only": "plan",
}

BOOTSTRAP_ARTIFACTS = [
    "CLAUDE.md",
    "DESIGN.md",
    ".claude/settings.json",
    ".claude/skills/README.md",
    ".claude/skills/flow-init.md",
    ".claude/skills/flow-feature.md",
    ".claude/skills/flow-qa.md",
    ".claude/skills/flow-review.md",
    ".claude/skills/flow-plan.md",
    ".workflow/config/ccs-map.yaml",
    ".workflow/docs/PRD.md",
    ".workflow/docs/ARCHITECTURE.md",
    ".workflow/docs/ADR.md",
    ".workflow/docs/QA.md",
    ".workflow/prompts/planner.md",
    ".workflow/prompts/implementer.md",
    ".workflow/prompts/qa-planner.md",
    ".workflow/prompts/reviewer.md",
    ".workflow/tasks/feature/_template.json",
    ".workflow/tasks/qa/_template.json",
    ".workflow/scripts/hooks/tdd-guard.sh",
    ".workflow/scripts/hooks/dangerous-cmd-guard.sh",
    ".workflow/scripts/hooks/circuit-breaker.sh",
]

BOOTSTRAP_DIRS = [
    ".claude",
    ".claude/skills",
    ".workflow/config",
    ".workflow/docs",
    ".workflow/prompts",
    ".workflow/scripts/hooks",
    ".workflow/tasks/feature",
    ".workflow/tasks/init",
    ".workflow/tasks/qa",
    ".workflow/tasks/plan",
    ".workflow/tasks/review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="so2x-flow execution entrypoint")
    parser.add_argument("mode", choices=["init", "feature", "qa", "qa-fix", "review", "plan", "plan-only"])
    parser.add_argument("request")
    parser.add_argument("--task")
    parser.add_argument("--qa-id")
    parser.add_argument("--docs", nargs="*")
    parser.add_argument("--skip-plan", action="store_true")
    parser.add_argument("--with-design", action="store_true")
    parser.add_argument("--output-name")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def canonical_mode(mode: str) -> str:
    return MODE_ALIASES.get(mode, mode)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9가-힣]+", "-", text)
    return text.strip("-") or "run"


GENERIC_PLAN_TOKENS = {
    "plan",
    "feature",
    "flow",
    "task",
    "tasks",
    "request",
    "요청",
    "기능",
    "설계",
    "확정",
    "작업",
    "분해",
    "구현",
    "개선",
    "초안",
    "버전",
    "v1",
    "v2",
}
PLAN_SIMILARITY_THRESHOLD = 0.34


def canonical_plan_artifacts() -> list[Path]:
    if not PLAN_TASKS.exists():
        return []
    return sorted(
        [
            path
            for path in PLAN_TASKS.iterdir()
            if path.is_file() and path.suffix == ".json" and path.name != ".gitkeep"
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def slug_tokens(text: str) -> set[str]:
    slug = slugify(text)
    return {token for token in slug.split("-") if token and token not in GENERIC_PLAN_TOKENS}


def plan_similarity_score(request: str, plan_path: Path) -> tuple[float, list[str]]:
    request_slug = slugify(request)
    plan_slug = slugify(plan_path.stem)
    request_tokens = slug_tokens(request)
    plan_tokens = slug_tokens(plan_path.stem)
    shared_tokens = sorted(request_tokens & plan_tokens)

    if request_slug == plan_slug:
        return 1.0, shared_tokens
    if request_slug and plan_slug and (request_slug in plan_slug or plan_slug in request_slug):
        return 0.95, shared_tokens
    if not request_tokens or not plan_tokens or not shared_tokens:
        return 0.0, shared_tokens

    union_size = len(request_tokens | plan_tokens)
    if union_size == 0:
        return 0.0, shared_tokens
    return len(shared_tokens) / union_size, shared_tokens


def match_plan_to_request(request: str, plan_path: Path) -> tuple[bool, float, str]:
    request_slug = slugify(request)
    plan_slug = slugify(plan_path.stem)
    score, shared_tokens = plan_similarity_score(request, plan_path)
    if score >= PLAN_SIMILARITY_THRESHOLD:
        if score == 1.0:
            return True, score, f"matched plan similarity exact slug: {plan_slug} (score={score:.2f})"
        if score >= 0.95:
            return True, score, f"matched plan similarity by containment: {plan_slug} (score={score:.2f})"
        return True, score, f"matched plan similarity via topics: {', '.join(shared_tokens)} (score={score:.2f})"
    return False, score, (
        "no sufficiently similar plan: "
        f"request={request_slug}, candidate={plan_slug}, score={score:.2f}, threshold={PLAN_SIMILARITY_THRESHOLD:.2f}"
    )


def is_plan_explicitly_approved(plan_path: Path) -> bool:
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(payload.get("approved") is True or payload.get("status") == "approved")


def select_approved_plan(request: str, require_explicit_approval: bool = False) -> tuple[str | None, str]:
    artifacts = canonical_plan_artifacts()
    if not artifacts:
        return None, "no plan artifacts found"

    if require_explicit_approval:
        artifacts = [artifact for artifact in artifacts if is_plan_explicitly_approved(artifact)]
        if not artifacts:
            return None, "no explicitly approved plan artifacts found"

    best_match: Path | None = None
    best_score = -1.0
    best_reason = "no sufficiently similar plan"

    for artifact in artifacts:
        matched, score, reason = match_plan_to_request(request, artifact)
        if matched and score > best_score:
            best_match = artifact
            best_score = score
            best_reason = reason

    if best_match is None:
        latest = artifacts[0]
        _, _, latest_reason = match_plan_to_request(request, latest)
        return None, latest_reason
    return str(best_match.relative_to(PROJECT_ROOT)), best_reason


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"config not found: {CONFIG_PATH}")
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def ensure_bootstrap_files() -> list[str]:
    artifacts: list[str] = []
    for rel_dir in BOOTSTRAP_DIRS:
        (PROJECT_ROOT / rel_dir).mkdir(parents=True, exist_ok=True)
    for rel_path in BOOTSTRAP_ARTIFACTS:
        path = PROJECT_ROOT / rel_path
        if path.exists():
            artifacts.append(rel_path)
    return artifacts


def collect_design_doc(mode: str, with_design: bool) -> str | None:
    preferred = PROJECT_ROOT / "DESIGN.md"
    fallback = WORKFLOW_ROOT / "docs" / "UI_GUIDE.md"
    if with_design or mode in {"feature", "review", "plan"}:
        if preferred.exists():
            return "DESIGN.md"
        if fallback.exists():
            return ".workflow/docs/UI_GUIDE.md"
    if mode == "qa" and with_design:
        if preferred.exists():
            return "DESIGN.md"
        if fallback.exists():
            return ".workflow/docs/UI_GUIDE.md"
    return None


def collect_docs(mode: str, extra_docs: list[str] | None, task: str | None = None, with_design: bool = False) -> tuple[list[str], str | None]:
    if mode == "init":
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md", ".workflow/docs/QA.md", "DESIGN.md"]
    elif mode == "feature":
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    elif mode == "qa":
        docs = [".workflow/docs/QA.md", ".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    elif mode == "plan":
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    elif mode == "review":
        docs = [".workflow/docs/QA.md", ".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    else:
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]

    design_doc = collect_design_doc(mode, with_design)
    if design_doc and design_doc not in docs:
        docs.append(design_doc)
    if task and task not in docs:
        docs.append(task)
    for item in extra_docs or []:
        if item not in docs:
            docs.append(item)
    return docs, design_doc


def load_docs_bundle(docs_used: list[str]) -> str:
    blocks: list[str] = []
    for rel_path in docs_used:
        path = PROJECT_ROOT / rel_path
        if path.exists():
            blocks.append(f"### {rel_path}\n{load_text(path).strip()}")
        else:
            blocks.append(f"### {rel_path}\n(MISSING)")
    return "\n\n".join(blocks) if blocks else "(none)"


def prompt_path_for_role(role: str) -> Path:
    mapping = {
        "planner": "planner.md",
        "implementer": "implementer.md",
        "qa_planner": "qa-planner.md",
        "reviewer": "reviewer.md",
    }
    return PROMPTS_DIR / mapping[role]


def load_prompt_template(role: str) -> str:
    return load_text(prompt_path_for_role(role))


def render_feature_task(request: str, approved_plan_path: str | None = None) -> dict:
    plan_ref = approved_plan_path or "(none matched request)"
    if approved_plan_path:
        next_step_prompt = "승인된 방향이 있으니, 이번 slice를 진행할까요? (y/n)"
        approval_hint = "승인된 방향이 있으니 이번 실행 여부만 확인하고, 새 범위 제안은 덧붙이지 않는다."
    else:
        next_step_prompt = "이 요청은 아직 승인된 방향이 없으니, /flow-plan으로 먼저 범위를 확정할까요? (y/n)"
        approval_hint = "승인된 plan이 없으면 여기서 멈추고 /flow-plan으로 먼저 범위를 확정할지 묻는다."
    return {
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
    }


def render_qa_task(request: str, qa_id: str | None) -> dict:
    qa_label = qa_id or "QA-TBD"
    return {
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
    }


def render_review_task(request: str, docs_used: list[str], task: str | None = None) -> dict:
    return {
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


def render_init_task(request: str) -> dict:
    return {
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
            {"id": "design", "question": "디자인/UX 기준이 있나요? 없으면 원하는 분위기를 알려주세요.", "target_doc": "DESIGN.md"}
        ],
        "next_step_prompt": "위 질문들에 답해주면 flow-init이 문서를 하나씩 채워갈게요."
    }


def render_plan_doc(request: str, docs_used: list[str]) -> dict:
    return {
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
    }


def build_prompt(
    role: str,
    mode: str,
    request: str,
    docs_used: list[str],
    docs_bundle: str,
    task_path: str | None,
    qa_id: str | None,
    planner_output: str | None,
    design_doc: str | None,
    approved_plan_path: str | None = None,
    approved_plan_match_reason: str | None = None,
) -> str:
    prompt_template = load_prompt_template(role)
    lines = [
        f"role: {role}",
        f"mode: {mode}",
        f"request: {request}",
        f"docs_used: {', '.join(docs_used) if docs_used else '(none)'}",
        f"design_doc: {design_doc or '(none)'}",
        f"approved_plan_path: {approved_plan_path or '(none)'}",
        f"approved_plan_match_reason: {approved_plan_match_reason or '(none)'}",
        "",
        "prompt_template:",
        prompt_template.strip(),
        "",
        "docs_content:",
        docs_bundle,
    ]
    if task_path:
        task_file = PROJECT_ROOT / task_path
        lines.extend(["", f"task_path: {task_path}", "task_content:", load_text(task_file).strip()])
    if qa_id:
        lines.append(f"qa_id: {qa_id}")
    if planner_output:
        lines.extend(["", "planner_output:", planner_output])
    return "\n".join(lines)


def save_task_payload(payload: dict) -> Path | None:
    artifacts = payload.get("artifacts") or []
    if not artifacts or not artifacts[0].endswith(".json"):
        return None
    target_path = PROJECT_ROOT / artifacts[0]
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
    if preserve_existing and path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        merged = {**existing}
        merged.setdefault("title", content["title"])
        answers = existing.get("answers")
        has_answers = bool(answers)
        merged["status"] = existing.get("status", "needs_user_input") if has_answers else "needs_user_input"
        merged["questions"] = content["questions"]
        merged["next_step_prompt"] = content["next_step_prompt"]
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def write_plan_task(path: Path, content: dict) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("approved") is True:
            content["approved"] = True
        if existing.get("status") == "approved":
            content["status"] = "approved"
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def print_summary(payload: dict) -> None:
    print(f"mode: {payload['mode']}")
    print(f"request: {payload['request']}")
    print(f"dry_run: {payload['dry_run']}")
    print(f"requested_runner: {payload['requested_runner']}")
    print(f"selected_runner: {payload['selected_runner']}")
    print(f"fallback_used: {payload['fallback_used']}")
    print(f"fallback_reason: {payload['fallback_reason'] or '(none)'}")
    print(f"design_doc: {payload['design_doc'] or '(none)'}")
    print(f"approved_plan_path: {payload.get('approved_plan_path') or '(none)'}")
    print(f"approved_plan_match_reason: {payload.get('approved_plan_match_reason') or '(none)'}")
    print("docs_used:")
    for doc in payload["docs_used"]:
        print(f"  - {doc}")
    print("roles:")
    for item in payload["role_results"]:
        print(f"  - {item['role']} ({item['status']})")
    print("commands:")
    for item in payload["role_results"]:
        print(f"  - {item['role']}: {item['command_preview']}")
    print("role_outputs:")
    for item in payload["role_results"]:
        print(f"  - {item['role']} output:")
        if item["output"]:
            for line in item["output"].splitlines():
                print(f"    {line}")
        else:
            print("    ")
    print("artifacts:")
    for artifact in payload["artifacts"]:
        print(f"  - {artifact}")
    print(f"output_json: {payload['output_json']}")


def main() -> int:
    args = parse_args()
    mode = canonical_mode(args.mode)
    bootstrap_artifacts = ensure_bootstrap_files() if mode == "init" else []
    artifacts = list(bootstrap_artifacts) if mode == "init" else []
    config = load_config()
    docs_used, design_doc = collect_docs(mode, args.docs, args.task, args.with_design)
    docs_bundle = load_docs_bundle(docs_used)
    configured_roles = config["modes"][mode]["roles"]
    skip_roles = {"planner", "qa_planner"} if args.skip_plan else set()
    roles = [] if mode == "init" else [role for role in configured_roles if role not in skip_roles]
    planner_output = None
    task_path = None
    approved_plan_path = None
    approved_plan_match_reason = None

    if mode == "feature":
        approved_plan_path, approved_plan_match_reason = select_approved_plan(args.request, require_explicit_approval=args.skip_plan)
        if approved_plan_path and approved_plan_path not in docs_used:
            docs_used.append(approved_plan_path)
            docs_bundle = load_docs_bundle(docs_used)
        if args.skip_plan and approved_plan_path is None:
            raise SystemExit("skip-plan requires an explicitly approved plan artifact; run /flow-plan, mark it approved, or omit --skip-plan")
        task_path = f".workflow/tasks/feature/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_feature_task(args.request, approved_plan_path), ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "init":
        task_path = f".workflow/tasks/init/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_initial_task(path, render_init_task(args.request), preserve_existing=True)
        artifacts = [task_path]
    elif mode == "qa":
        task_path = f".workflow/tasks/qa/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(render_qa_task(args.request, args.qa_id), ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "plan":
        task_path = f".workflow/tasks/plan/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_plan_task(path, render_plan_doc(args.request, docs_used))
        artifacts.append(task_path)
    elif mode == "review":
        task_path = f".workflow/tasks/review/{slugify(args.request)}.json"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(render_review_task(args.request, docs_used, args.task), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        artifacts.append(task_path)

    runtime_config = config.get("runtime", {})
    allow_live_run_raw = runtime_config.get("allow_live_run", False)
    if not isinstance(allow_live_run_raw, bool):
        raise SystemExit("live execution blocked: runtime.allow_live_run must be a boolean true/false value")
    allow_live_run = allow_live_run_raw
    if not args.dry_run and not allow_live_run:
        raise SystemExit("live execution blocked: set runtime.allow_live_run=true or use --dry-run")
    resolution = resolve_runner(runtime_config.get("runner", "auto"))
    role_results = []
    for role in roles:
        role_config = config["roles"][role][resolution.selected_runner]
        shared_role_config = {
            **config["roles"][role],
            **role_config,
        }
        prompt = build_prompt(role, mode, args.request, docs_used, docs_bundle, task_path, args.qa_id, planner_output, design_doc, approved_plan_path, approved_plan_match_reason)
        if args.dry_run:
            result = run_role(
                runner=resolution.selected_runner,
                role=role,
                prompt=prompt,
                role_config=shared_role_config,
                runtime_config=runtime_config,
                dry_run=True,
            )
        else:
            result = run_role_subprocess(
                runner=resolution.selected_runner,
                role=role,
                prompt=prompt,
                role_config=shared_role_config,
                runtime_config=runtime_config,
            )
        role_results.append(
            {
                "role": result.role,
                "runner": result.runner,
                "engine": result.engine,
                "model": result.model,
                "status": result.status,
                "output": result.output,
                "command": result.command,
                "command_preview": result.command_preview,
            }
        )
        if role in {"planner", "qa_planner"}:
            planner_output = result.output

    payload = {
        "mode": mode,
        "request": args.request,
        "dry_run": args.dry_run,
        "requested_runner": resolution.requested_runner,
        "selected_runner": resolution.selected_runner,
        "fallback_used": resolution.fallback_used,
        "fallback_reason": resolution.fallback_reason,
        "design_doc": design_doc,
        "approved_plan_path": approved_plan_path,
        "approved_plan_match_reason": approved_plan_match_reason,
        "docs_used": docs_used,
        "roles": roles,
        "role_results": role_results,
        "artifacts": artifacts,
        "output_json": artifacts[0] if artifacts and artifacts[0].endswith(".json") else "",
    }
    json_path = save_task_payload(payload)
    if json_path is not None:
        payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
