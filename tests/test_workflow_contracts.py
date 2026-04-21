import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".workflow" / "scripts" / "workflow_contracts.py"
SCRIPT_DIR = MODULE_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

spec = importlib.util.spec_from_file_location("workflow_contracts", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_role_contracts_capture_handoffs_and_review_lenses():
    planner = module.contract_for_role("planner")
    implementer = module.contract_for_role("implementer")
    reviewer = module.contract_for_role("reviewer")

    assert planner.handoff_to == ("implementer",)
    assert "feature mode planner must not invent a new direction without approved plan context" in planner.dependency_notes
    assert implementer.handoff_to == ("reviewer",)
    assert "Code Reuse Review, Code Quality Review, Efficiency Review." in reviewer.responsibilities[1]
    assert reviewer.emits[-1] == "Verdict"


def test_evaluate_mode_contract_routes_to_reviewer_only():
    evaluate = module.contract_for_mode("evaluate")

    assert evaluate.artifact_kind == "evaluate"
    assert evaluate.roles == ("reviewer",)
    assert "Mechanical Status" in evaluate.output_contract.markers
    assert "Release Readiness" in evaluate.output_contract.markers
