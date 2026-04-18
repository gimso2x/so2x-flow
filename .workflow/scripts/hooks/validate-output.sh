#!/usr/bin/env sh
set -eu

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
[ "$tool_name" = "Skill" ] || exit 0

skill_name=$(printf '%s' "$input" | jq -r '.tool_input.skill // empty')
[ -n "$skill_name" ] || exit 0

cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -n "$cwd" ] || cwd=$(pwd)

tool_response=$(printf '%s' "$input" | jq -r '.tool_response // empty')

skill_file=""
for candidate in \
  "$cwd/.claude/skills/$skill_name.md" \
  "$cwd/.claude/skills/$skill_name/SKILL.md"
do
  if [ -f "$candidate" ]; then
    skill_file="$candidate"
    break
  fi
done
[ -n "$skill_file" ] || exit 0

response_file=$(mktemp)
trap 'rm -f "$response_file"' EXIT HUP INT TERM
printf '%s' "$tool_response" > "$response_file"

python3 - "$cwd" "$skill_file" "$skill_name" "$response_file" <<'PY'
import importlib.util
import json
import re
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
skill_path = Path(sys.argv[2])
skill_name = sys.argv[3]
response_path = Path(sys.argv[4])
response = response_path.read_text(encoding="utf-8")
text = skill_path.read_text(encoding="utf-8")

validate_prompt = ""
if text.startswith("---\n"):
    parts = text.split("\n---\n", 1)
    if len(parts) == 2:
        frontmatter = parts[0][4:]
        match = re.search(r'(?ms)^validate_prompt:\s*\|\n(?P<body>(?:  .*\n?)*)', frontmatter)
        if match:
            validate_prompt = "\n".join(
                line[2:] if line.startswith("  ") else line
                for line in match.group("body").splitlines()
            ).strip()
if not validate_prompt:
    sys.exit(0)

contracts_path = project_root / ".workflow" / "scripts" / "workflow_contracts.py"
if not contracts_path.exists():
    sys.exit(0)
spec = importlib.util.spec_from_file_location("so2x_workflow_contracts", contracts_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)
contract = module.contract_for_skill(skill_name)
if contract is None or contract.output_contract is None:
    sys.exit(0)

markers = list(contract.output_contract.markers)
missing = []
for token in markers:
    if response and token not in response:
        missing.append(token)

bullet_issues = []
for section, bounds in (contract.output_contract.required_bullets or {}).items():
    if not response or section not in response:
        continue
    min_items, max_items = bounds
    pattern = re.compile(rf"{re.escape(section)}\s*:?(.*?)(?:\n[A-Z][^\n]*:|\Z)", re.S)
    match = pattern.search(response)
    if not match:
        continue
    block = match.group(1)
    count = len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", block))
    if min_items is not None and count < min_items:
        bullet_issues.append(f"{section} has {count} items (< {min_items})")
    if max_items is not None and count > max_items:
        bullet_issues.append(f"{section} has {count} items (> {max_items})")

closed_question_issue = None
if response and contract.output_contract.closed_question:
    next_step_match = re.search(r"Next Step Prompt\s*:?(.*?)(?:\n[A-Z][^\n]*:|\Z)", response, re.S)
    if next_step_match:
        next_step = next_step_match.group(1).strip()
        if next_step and not re.search(r"\((?:y/n|yes/no)\)|\?$", next_step, re.I):
            closed_question_issue = "Next Step Prompt should end as a closed approval question"
    else:
        closed_question_issue = "Next Step Prompt section missing or not parseable"

issues = []
if missing:
    issues.append(f"Missing expected output markers: {', '.join(missing)}")
issues.extend(bullet_issues)
if closed_question_issue:
    issues.append(closed_question_issue)

if response and issues:
    context = (
        f"VALIDATION WARNING [{skill_name}]\n"
        + "\n".join(f"- {issue}" for issue in issues)
        + f"\n\nValidate Prompt:\n{validate_prompt}"
    )
elif response:
    context = f"VALIDATION CHECKED [{skill_name}]\n{validate_prompt}"
else:
    context = f"VALIDATION REMINDER [{skill_name}]\n{validate_prompt}"

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": context,
    }
}))
PY
