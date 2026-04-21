from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputContract:
    markers: tuple[str, ...]
    closed_question: bool = False
    required_bullets: dict[str, tuple[int | None, int | None]] | None = None
    required_patterns: tuple[tuple[str, str], ...] = ()
    required_sections: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModeContract:
    mode: str
    artifact_kind: str
    roles: tuple[str, ...]
    required_docs: tuple[str, ...]
    output_contract: OutputContract | None = None


@dataclass(frozen=True)
class RoleContract:
    role: str
    modes: tuple[str, ...]
    responsibilities: tuple[str, ...]
    receives: tuple[str, ...]
    emits: tuple[str, ...]
    handoff_to: tuple[str, ...]
    dependency_notes: tuple[str, ...]


ROLE_CONTRACTS: dict[str, RoleContract] = {
    "planner": RoleContract(
        role="planner",
        modes=("plan", "feature"),
        responsibilities=(
            "Freeze scope into an approved direction or minimal implementation slice.",
            "Turn docs-first context into a concrete execution checklist.",
        ),
        receives=(
            "request",
            "required docs bundle",
            "approved plan context when present",
            "feature task artifact",
        ),
        emits=(
            "plan artifact sections or feature Proposed Steps",
            "verification gates",
            "closed next-step prompt",
        ),
        handoff_to=("implementer",),
        dependency_notes=(
            "feature mode planner must not invent a new direction without approved plan context",
            "plan mode stops at approval and does not auto-transition into implementation",
        ),
    ),
    "qa_planner": RoleContract(
        role="qa_planner",
        modes=("qa",),
        responsibilities=(
            "Reduce a bug report to a reproducible root-cause-first repair slice.",
            "Define the smallest safe fix and regression checklist.",
        ),
        receives=(
            "QA task artifact",
            "QA/PRD/ARCHITECTURE/ADR docs",
            "reproduction context and qa_id when available",
        ),
        emits=(
            "root cause hypothesis",
            "minimal fix plan",
            "verification and residual-risk checklist",
        ),
        handoff_to=("implementer",),
        dependency_notes=(
            "must establish reproduction/expected/actual before implementation",
        ),
    ),
    "implementer": RoleContract(
        role="implementer",
        modes=("feature", "qa"),
        responsibilities=(
            "Execute only the approved or planned minimal slice.",
            "Keep verification attached to the exact change made.",
        ),
        receives=(
            "planner or qa_planner output",
            "task artifact",
            "docs bundle",
            "approved plan path when present",
        ),
        emits=(
            "implemented slice summary",
            "verification evidence",
            "follow-up slice or residual risk notes",
        ),
        handoff_to=("reviewer",),
        dependency_notes=(
            "feature mode implementer follows planner output rather than redefining scope",
            "qa mode implementer fixes root cause only and avoids speculative expansion",
        ),
    ),
    "reviewer": RoleContract(
        role="reviewer",
        modes=("review",),
        responsibilities=(
            "Review work independently against docs, task artifacts, and regression risk.",
            "Keep the three explicit lenses visible: Code Reuse Review, Code Quality Review, Efficiency Review.",
        ),
        receives=(
            "review task artifact",
            "docs bundle",
            "related task path when provided",
        ),
        emits=(
            "Spec Gap",
            "Architecture Concern",
            "Test Gap",
            "QA Watchpoints",
            "Security / Regression Risk",
            "Verdict",
        ),
        handoff_to=(),
        dependency_notes=(
            "review stays fail-closed and does not rewrite the implementation plan",
        ),
    ),
}


MODE_CONTRACTS: dict[str, ModeContract] = {
    "init": ModeContract(
        mode="init",
        artifact_kind="init",
        roles=(),
        required_docs=(
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
            ".workflow/docs/QA.md",
            "DESIGN.md",
        ),
        output_contract=OutputContract(
            markers=(
                ".workflow/tasks/init/",
                "needs_user_input",
                ".workflow/docs/PRD.md",
                ".workflow/docs/ARCHITECTURE.md",
                ".workflow/docs/QA.md",
                "DESIGN",
            ),
            required_patterns=(
                (r"\.workflow/tasks/init/[^\s]+\.json", "canonical init artifact path"),
            ),
        ),
    ),
    "feature": ModeContract(
        mode="feature",
        artifact_kind="feature",
        roles=("planner", "implementer"),
        required_docs=(
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
        ),
        output_contract=OutputContract(
            markers=(
                "Approved Direction",
                "Implementation Slice",
                "Out of Scope",
                "Proposed Steps",
                "Verification",
                "Review Gate",
                "Follow-up Slice",
                "Next Step Prompt",
            ),
            closed_question=True,
            required_bullets={"Proposed Steps": (3, 7)},
            required_patterns=(
                (r"\.workflow/tasks/feature/[^\s]+\.json", "canonical feature task artifact path"),
            ),
            required_sections=(
                "Approved Direction",
                "Implementation Slice",
                "Out of Scope",
                "Proposed Steps",
                "Verification",
                "Review Gate",
                "Follow-up Slice",
            ),
        ),
    ),
    "qa": ModeContract(
        mode="qa",
        artifact_kind="qa",
        roles=("qa_planner", "implementer"),
        required_docs=(
            ".workflow/docs/QA.md",
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
        ),
        output_contract=OutputContract(
            markers=(
                "Reproduction",
                "Expected",
                "Actual",
                "Root Cause Hypothesis",
                "Minimal Fix",
                "Verification",
                "Residual Risk",
            ),
            required_patterns=(
                (r"\.workflow/tasks/qa/[^\s]+\.json", "canonical QA task artifact path"),
            ),
            required_sections=(
                "Reproduction",
                "Expected",
                "Actual",
                "Root Cause Hypothesis",
                "Minimal Fix",
                "Verification",
                "Residual Risk",
            ),
        ),
    ),
    "review": ModeContract(
        mode="review",
        artifact_kind="review",
        roles=("reviewer",),
        required_docs=(
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
            ".workflow/docs/QA.md",
        ),
        output_contract=OutputContract(
            markers=(
                "Spec Gap",
                "Architecture Concern",
                "Test Gap",
                "QA Watchpoints",
                "Security / Regression Risk",
                "Verdict",
            ),
            required_patterns=(
                (r"\.workflow/tasks/review/[^\s]+\.json", "canonical review task artifact path"),
            ),
            required_sections=(
                "Spec Gap",
                "Architecture Concern",
                "Test Gap",
                "QA Watchpoints",
                "Security / Regression Risk",
                "Verdict",
            ),
        ),
    ),
    "plan": ModeContract(
        mode="plan",
        artifact_kind="plan",
        roles=("planner",),
        required_docs=(
            ".workflow/docs/PRD.md",
            ".workflow/docs/ARCHITECTURE.md",
            ".workflow/docs/ADR.md",
        ),
        output_contract=OutputContract(
            markers=(
                "Context Snapshot",
                "Open Questions",
                "Options",
                "Recommendation",
                "Implementation Slices",
                "Verification Gates",
                "Draft Plan",
                "Approval Gate",
                "Next Step Prompt",
            ),
            closed_question=True,
            required_patterns=(
                (r"\.workflow/tasks/plan/[^\s]+\.json", "canonical plan artifact path"),
            ),
            required_sections=(
                "Context Snapshot",
                "Options",
                "Recommendation",
                "Implementation Slices",
                "Verification Gates",
                "Draft Plan",
                "Approval Gate",
            ),
            required_bullets={
                "Options": (2, 3),
                "Implementation Slices": (1, None),
            },
        ),
    ),
}

SKILL_TO_MODE = {
    "flow-init": "init",
    "flow-feature": "feature",
    "flow-qa": "qa",
    "flow-review": "review",
    "flow-plan": "plan",
}


def contract_for_mode(mode: str) -> ModeContract:
    return MODE_CONTRACTS[mode]


def contract_for_skill(skill_name: str) -> ModeContract | None:
    mode = SKILL_TO_MODE.get(skill_name)
    if mode is None:
        return None
    return contract_for_mode(mode)


def contract_for_role(role: str) -> RoleContract:
    return ROLE_CONTRACTS[role]
