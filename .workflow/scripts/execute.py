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
OUTPUT_RUNS = WORKFLOW_ROOT / "outputs" / "runs"
OUTPUT_PLANS = WORKFLOW_ROOT / "outputs" / "plans"
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
    ".workflow/tasks/feature/_template.md",
    ".workflow/tasks/qa/_template.md",
    ".workflow/scripts/hooks/tdd-guard.sh",
    ".workflow/scripts/hooks/dangerous-cmd-guard.sh",
    ".workflow/scripts/hooks/circuit-breaker.sh",
    ".workflow/outputs/plans/.gitkeep",
    ".workflow/outputs/runs/.gitkeep",
]

BOOTSTRAP_DIRS = [
    ".claude",
    ".claude/skills",
    ".workflow/config",
    ".workflow/docs",
    ".workflow/prompts",
    ".workflow/scripts/hooks",
    ".workflow/tasks/feature",
    ".workflow/tasks/qa",
    ".workflow/outputs/plans",
    ".workflow/outputs/runs",
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


def canonical_plan_artifacts() -> list[Path]:
    if not OUTPUT_PLANS.exists():
        return []
    return sorted(
        [
            path
            for path in OUTPUT_PLANS.glob("*.md")
            if path.name != ".gitkeep" and not path.name.startswith("plan-")
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def slug_tokens(text: str) -> set[str]:
    slug = slugify(text)
    return {token for token in slug.split("-") if token and token not in GENERIC_PLAN_TOKENS}


def match_plan_to_request(request: str, plan_path: Path) -> tuple[bool, str]:
    request_slug = slugify(request)
    plan_slug = slugify(plan_path.stem)
    request_tokens = slug_tokens(request)
    plan_tokens = slug_tokens(plan_path.stem)
    shared_tokens = sorted(request_tokens & plan_tokens)

    if request_slug == plan_slug:
        return True, f"matched plan slug exactly: {plan_slug}"
    if request_slug and plan_slug and (request_slug in plan_slug or plan_slug in request_slug):
        return True, f"matched plan slug by containment: {plan_slug}"
    if shared_tokens:
        return True, f"matched plan topic tokens: {', '.join(shared_tokens)}"
    return False, f"latest plan slug mismatch: request={request_slug}, latest_plan={plan_slug}"


def select_approved_plan(request: str) -> tuple[str | None, str]:
    artifacts = canonical_plan_artifacts()
    if not artifacts:
        return None, "no plan artifacts found"
    latest = artifacts[0]
    matched, reason = match_plan_to_request(request, latest)
    if not matched:
        return None, reason
    return str(latest.relative_to(PROJECT_ROOT)), reason


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def latest_plan_artifact() -> str | None:
    plans_dir = PROJECT_ROOT / ".workflow" / "outputs" / "plans"
    if not plans_dir.exists():
        return None
    preferred = [
        path for path in plans_dir.glob("*.md")
        if path.name != ".gitkeep" and path.is_file() and not path.name.startswith("plan-")
    ]
    candidates = preferred or [
        path for path in plans_dir.glob("*.md")
        if path.name != ".gitkeep" and path.is_file()
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return str(latest.relative_to(PROJECT_ROOT))


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
        docs = []
    elif mode == "feature":
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    elif mode == "qa":
        docs = [".workflow/docs/QA.md", ".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md"]
    elif mode == "review":
        docs = [".workflow/docs/PRD.md", ".workflow/docs/ARCHITECTURE.md", ".workflow/docs/ADR.md", ".workflow/docs/QA.md"]
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


def render_feature_task(request: str, approved_plan_path: str | None = None) -> str:
    plan_ref = approved_plan_path or "(none matched request)"
    return f'''# Feature Task

## Title
{request}

## Summary
- Requested feature: {request}

## Context
- Capture user-facing context and constraints here.

## Related Docs
- .workflow/docs/PRD.md
- .workflow/docs/ARCHITECTURE.md
- .workflow/docs/ADR.md
- DESIGN.md
- Latest approved flow-plan output: {plan_ref}

## Approved Direction
- Summarize the agreed direction from flow-plan or the latest approval note.
- Source plan artifact: {approved_plan_path or "(none)"}

## Implementation Slice
- Define the smallest implementation slice for this run.

## Relevant Files
- List candidate files to inspect or modify.

## Out of Scope
- Explicitly list what this task will not change.

## Proposed Steps
1. Confirm the approved direction and implementation slice.
2. Identify the smallest implementation change.
3. Implement and verify the slice.

## Acceptance
- Define the minimum accepted outcome for this slice.

## Verification
- List the checks required before considering this slice done.

## Follow-up Slice
- Describe the next smallest slice after this one.

## Next Step Prompt
- 다음으로 <남은 slice 요약>까지 이어서 진행하시겠습니까? (y/n)
'''


def render_qa_task(request: str, qa_id: str | None) -> str:
    qa_label = qa_id or "QA-TBD"
    return f'''# QA Fix Task

## Title
{request}

## Issue Summary
- Summarize the bug and affected user flow.

## QA ID
{qa_label}

## References
- .workflow/docs/QA.md
- Related screenshots, issues, or logs if available.

## Reproduction
- Describe how to reproduce the issue.

## Expected
- Describe the intended behavior.

## Actual
- Describe the current broken behavior.

## Suspected Scope
- List the likely files, modules, or UI areas involved.

## Minimal Fix
- Describe the smallest safe repair.

## Regression Checklist
- [ ] Original issue no longer reproduces
- [ ] Adjacent flow still works
- [ ] No broader scope added without approval
'''


def render_plan_doc(request: str, docs_used: list[str]) -> str:
    return "\n".join([
        "# Plan",
        "",
        f"## Request\n{request}",
        "",
        "## Related Docs",
        *[f"- {doc}" for doc in docs_used],
        "",
        "## Context Snapshot",
        "- 현재 프로젝트 구조와 관련 문서를 기준으로 핵심 맥락을 요약한다.",
        "",
        "## Open Questions",
        "- 한 번에 하나씩 확인이 필요한 질문을 적는다.",
        "",
        "## Options",
        "### Option A",
        "- 가장 작은 MVP 접근",
        "",
        "### Option B",
        "- 상호작용이나 범위를 조금 더 포함한 접근",
        "",
        "## Recommendation",
        "- 추천안을 한 줄로 명시하고 이유를 붙인다.",
        "",
        "## Draft Plan",
        "1. 컨텍스트를 확인한다.",
        "2. 범위를 분해한다.",
        "3. 질문과 대안을 정리한다.",
        "4. 추천안을 기준으로 설계 초안을 확정한다.",
        "5. 구현 전 검증 기준을 적는다.",
        "",
        "## Approval Gate",
        "- 이 설계 방향으로 확정할지 사용자 승인을 요청한다.",
        "",
        "## Next Step Prompt",
        "- 다음으로 /flow-feature <요청 요약> 구현 계획까지 이어가시겠습니까? (y/n)",
    ])


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


def save_run_outputs(payload: dict, markdown: str, output_name: str) -> tuple[Path, Path]:
    target_dir = OUTPUT_PLANS if payload["mode"] == "plan" else OUTPUT_RUNS
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / f"{output_name}.json"
    md_path = target_dir / f"{output_name}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return json_path, md_path


def render_markdown_summary(payload: dict) -> str:
    docs_used = payload["docs_used"] or ["(none)"]
    artifacts = payload["artifacts"] or ["(none)"]
    return "\n".join(
        [
            "# Run Summary",
            "",
            "## Request Summary",
            f"- Mode: {payload['mode']}",
            f"- Request: {payload['request']}",
            f"- Dry Run: {payload['dry_run']}",
            f"- Requested Runner: {payload['requested_runner']}",
            f"- Selected Runner: {payload['selected_runner']}",
            f"- Fallback Used: {payload['fallback_used']}",
            f"- Fallback Reason: {payload['fallback_reason'] or '(none)'}",
            f"- Design Doc: {payload['design_doc'] or '(none)'}",
            f"- Approved Plan: {payload.get('approved_plan_path') or '(none)'}",
            f"- Approved Plan Match Reason: {payload.get('approved_plan_match_reason') or '(none)'}",
            "",
            "## Docs Used",
            *[f"- {doc}" for doc in docs_used],
            "",
            "## Roles Executed",
            *[
                f"- {item['role']} ({item['runner']} / {item['engine']}:{item['model']}) -> {item['status']}"
                for item in payload['role_results']
            ],
            "",
            "## Artifact List",
            *[f"- {item}" for item in artifacts],
            "",
            "## Final Summary",
            f"- Output JSON: {payload['output_json']}",
            f"- Output MD: {payload['output_md']}",
            "",
        ]
    )


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
    print("artifacts:")
    for artifact in payload["artifacts"]:
        print(f"  - {artifact}")
    print(f"output_json: {payload['output_json']}")
    print(f"output_md: {payload['output_md']}")


def main() -> int:
    args = parse_args()
    mode = canonical_mode(args.mode)
    artifacts = ensure_bootstrap_files() if mode == "init" else []
    config = load_config()
    docs_used, design_doc = collect_docs(mode, args.docs, args.task, args.with_design)
    docs_bundle = load_docs_bundle(docs_used)
    configured_roles = config["modes"][mode]["roles"]
    skip_roles = {"planner", "qa_planner"} if args.skip_plan else set()
    roles = [role for role in configured_roles if role not in skip_roles]
    planner_output = None
    task_path = None
    approved_plan_path = None
    approved_plan_match_reason = None

    if mode == "feature":
        approved_plan_path, approved_plan_match_reason = select_approved_plan(args.request)
        if approved_plan_path and approved_plan_path not in docs_used:
            docs_used.append(approved_plan_path)
            docs_bundle = load_docs_bundle(docs_used)
        task_path = f".workflow/tasks/feature/{slugify(args.request)}.md"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_feature_task(args.request, approved_plan_path), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "qa":
        task_path = f".workflow/tasks/qa/{slugify(args.request)}.md"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_qa_task(args.request, args.qa_id), encoding="utf-8")
        artifacts.append(task_path)
    elif mode == "plan":
        task_path = f".workflow/outputs/plans/{slugify(args.request)}.md"
        path = PROJECT_ROOT / task_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_plan_doc(args.request, docs_used), encoding="utf-8")
        artifacts.append(task_path)

    runtime_config = config.get("runtime", {})
    allow_live_run = bool(runtime_config.get("allow_live_run", False))
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

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_name = args.output_name or f"{mode}-{slugify(args.request)}-{timestamp}"
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
        "output_json": "",
        "output_md": "",
    }
    json_path, md_path = save_run_outputs(payload, render_markdown_summary(payload), output_name)
    payload["output_json"] = str(json_path.relative_to(PROJECT_ROOT))
    payload["output_md"] = str(md_path.relative_to(PROJECT_ROOT))
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_summary(payload), encoding="utf-8")
    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
