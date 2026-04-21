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



def _score_slug_similarity(request: str, candidate_text: str) -> tuple[float, list[str], str]:
    request_slug = slugify(request)
    candidate_slug = slugify(candidate_text)
    request_tokens = slug_tokens(request)
    candidate_tokens = slug_tokens(candidate_text)
    shared_tokens = sorted(request_tokens & candidate_tokens)

    if request_slug == candidate_slug:
        return 1.0, shared_tokens, "exact slug"
    if request_slug and candidate_slug and (request_slug in candidate_slug or candidate_slug in request_slug):
        return 0.95, shared_tokens, "containment"
    if not request_tokens or not candidate_tokens or not shared_tokens:
        return 0.0, shared_tokens, "insufficient overlap"

    request_overlap = len(shared_tokens) / len(request_tokens)
    candidate_overlap = len(shared_tokens) / len(candidate_tokens)
    return request_overlap * candidate_overlap, shared_tokens, "topics"



def _plan_match_candidates(plan_path: Path) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [(plan_path.stem, "filename")]
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return candidates

    if isinstance(payload, dict):
        for key in ("request", "title"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append((value.strip(), f"artifact {key}"))
    return candidates



def _match_reason(prefix: str, request_slug: str, plan_slug: str, score: float, shared_tokens: list[str], source: str) -> str:
    shared = ", ".join(shared_tokens) if shared_tokens else "(none)"
    return (
        f"{prefix}: request={request_slug}, candidate={plan_slug}, source={source}, "
        f"shared_tokens={shared}, score={score:.2f}, threshold={PLAN_SIMILARITY_THRESHOLD:.2f}"
    )



def match_plan_to_request(request: str, plan_path: Path) -> tuple[bool, float, str]:
    request_slug = slugify(request)
    best_score = -1.0
    best_reason = _match_reason("no sufficiently similar plan", request_slug, slugify(plan_path.stem), 0.0, [], "filename")

    for candidate_text, source in _plan_match_candidates(plan_path):
        plan_slug = slugify(candidate_text)
        score, shared_tokens, _strategy = _score_slug_similarity(request, candidate_text)
        if score < best_score:
            continue
        if score >= PLAN_SIMILARITY_THRESHOLD:
            if score == 1.0:
                best_reason = _match_reason(f"matched plan similarity exact slug via {source}", request_slug, plan_slug, score, shared_tokens, source)
            elif score >= 0.95:
                best_reason = _match_reason(f"matched plan similarity by containment via {source}", request_slug, plan_slug, score, shared_tokens, source)
            else:
                best_reason = _match_reason(f"matched plan similarity via topics via {source}", request_slug, plan_slug, score, shared_tokens, source)
        else:
            best_reason = _match_reason(f"no sufficiently similar plan via {source}", request_slug, plan_slug, score, shared_tokens, source)
        best_score = score

    return best_score >= PLAN_SIMILARITY_THRESHOLD, max(best_score, 0.0), best_reason

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
