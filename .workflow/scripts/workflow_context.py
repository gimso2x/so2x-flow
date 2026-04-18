from __future__ import annotations

import json
import re
from pathlib import Path

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
PLAN_SIMILARITY_THRESHOLD = 0.75


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9가-힣]+", "-", text)
    return text.strip("-") or "run"



def canonical_plan_artifacts(plan_tasks: Path) -> list[Path]:
    if not plan_tasks.exists():
        return []
    return sorted(
        [
            path
            for path in plan_tasks.iterdir()
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

    request_overlap = len(shared_tokens) / len(request_tokens)
    plan_overlap = len(shared_tokens) / len(plan_tokens)
    return request_overlap * plan_overlap, shared_tokens



def _match_reason(prefix: str, request_slug: str, plan_slug: str, score: float, shared_tokens: list[str]) -> str:
    shared = ", ".join(shared_tokens) if shared_tokens else "(none)"
    return (
        f"{prefix}: request={request_slug}, candidate={plan_slug}, "
        f"shared_tokens={shared}, score={score:.2f}, threshold={PLAN_SIMILARITY_THRESHOLD:.2f}"
    )



def match_plan_to_request(request: str, plan_path: Path) -> tuple[bool, float, str]:
    request_slug = slugify(request)
    plan_slug = slugify(plan_path.stem)
    score, shared_tokens = plan_similarity_score(request, plan_path)
    if score >= PLAN_SIMILARITY_THRESHOLD:
        if score == 1.0:
            return True, score, _match_reason("matched plan similarity exact slug", request_slug, plan_slug, score, shared_tokens)
        if score >= 0.95:
            return True, score, _match_reason("matched plan similarity by containment", request_slug, plan_slug, score, shared_tokens)
        return True, score, _match_reason("matched plan similarity via topics", request_slug, plan_slug, score, shared_tokens)
    return False, score, _match_reason("no sufficiently similar plan", request_slug, plan_slug, score, shared_tokens)

def is_plan_explicitly_approved(plan_path: Path) -> bool:
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(payload.get("approved") is True or payload.get("status") == "approved")


def select_approved_plan(project_root: Path, plan_tasks: Path, request: str, require_explicit_approval: bool = False) -> tuple[str | None, str]:
    artifacts = canonical_plan_artifacts(plan_tasks)
    if not artifacts:
        return None, "no plan artifacts found"

    if require_explicit_approval:
        artifacts = [artifact for artifact in artifacts if is_plan_explicitly_approved(artifact)]
        if not artifacts:
            return None, "no explicitly approved plan artifacts found"

    best_match: Path | None = None
    best_match_score = -1.0
    best_match_reason = "no sufficiently similar plan"
    best_candidate: Path | None = None
    best_candidate_score = -1.0
    best_candidate_reason = "no sufficiently similar plan"

    for artifact in artifacts:
        matched, score, reason = match_plan_to_request(request, artifact)
        if score > best_candidate_score:
            best_candidate = artifact
            best_candidate_score = score
            best_candidate_reason = reason
        if matched and score > best_match_score:
            best_match = artifact
            best_match_score = score
            best_match_reason = reason

    if best_match is None:
        if best_candidate is None:
            return None, "no plan artifacts found"
        return None, f"{best_candidate_reason}; best_candidate={slugify(best_candidate.stem)}"
    return str(best_match.relative_to(project_root)), best_match_reason


def collect_design_doc(project_root: Path, workflow_root: Path, mode: str, with_design: bool) -> str | None:
    preferred = project_root / "DESIGN.md"
    fallback = workflow_root / "docs" / "UI_GUIDE.md"
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


def collect_docs(project_root: Path, workflow_root: Path, mode: str, extra_docs: list[str] | None, task: str | None = None, with_design: bool = False) -> tuple[list[str], str | None]:
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

    design_doc = collect_design_doc(project_root, workflow_root, mode, with_design)
    if design_doc and design_doc not in docs:
        docs.append(design_doc)
    if task and task not in docs:
        docs.append(task)
    for item in extra_docs or []:
        if item not in docs:
            docs.append(item)
    return docs, design_doc


def load_docs_bundle(project_root: Path, docs_used: list[str], load_text) -> str:
    blocks: list[str] = []
    for rel_path in docs_used:
        path = project_root / rel_path
        if path.exists():
            blocks.append(f"### {rel_path}\n{load_text(path).strip()}")
        else:
            blocks.append(f"### {rel_path}\n(MISSING)")
    return "\n\n".join(blocks) if blocks else "(none)"
