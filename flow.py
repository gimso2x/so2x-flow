#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKFLOW_SCRIPTS = ROOT / ".workflow" / "scripts"
EXECUTE = WORKFLOW_SCRIPTS / "execute.py"
DOCTOR = WORKFLOW_SCRIPTS / "doctor.py"

HELP_TEXT = """so2x-flow shortcut wrapper

Usage:
  python3 flow.py doctor [--brief|--json]
  python3 flow.py status [--brief|--json]
  python3 flow.py <mode> <request> [options]

Modes:
  init, plan, feature, qa, flow-fix, review, evaluate

Examples:
  python3 flow.py doctor --brief
  python3 flow.py init "외부 샘플 앱 초기 설정" --dry-run
  python3 flow.py plan "로그인 기능 작업 분해" --dry-run
  python3 flow.py feature "로그인 기능 구현" --dry-run
"""


def _run(script: Path, args: list[str]) -> int:
    completed = subprocess.run([sys.executable, str(script), *args], cwd=ROOT)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not EXECUTE.exists() or not DOCTOR.exists():
        print("flow.py requires .workflow/scripts/execute.py and .workflow/scripts/doctor.py", file=sys.stderr)
        return 1

    if not args or args[0] in {"-h", "--help", "help"}:
        print(HELP_TEXT)
        return 0

    mode = args[0]
    if mode in {"doctor", "status"}:
        return _run(DOCTOR, args[1:])
    return _run(EXECUTE, args)


if __name__ == "__main__":
    raise SystemExit(main())
