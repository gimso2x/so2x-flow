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
