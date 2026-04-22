#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

START = "<!-- so2x-flow:managed:start -->"
END = "<!-- so2x-flow:managed:end -->"
SECTION_BODY = """## so2x-flow
- 공용 agent surface는 루트 `AGENTS.md`와 `.workflow/` 문서다.
- Claude Code를 쓸 때는 `.claude/skills` 아래 `flow-init`, `flow-feature`, `flow-fix`(=`flow-qa`), `flow-review`, `flow-evaluate`, `flow-plan`을 추가로 사용할 수 있다.
- Codex 같은 다른 에이전트에서도 같은 계약을 `AGENTS.md`와 `.workflow/` 기준으로 그대로 따른다.
- Codex나 셸에서 바로 쓸 때는 `python3 flow.py <mode> ...`를 기본 진입점으로 본다. 이 파일은 `.workflow/scripts/execute.py`와 `.workflow/scripts/doctor.py`를 감싼 얇은 래퍼다.
- 상태만 읽고 싶으면 `python3 flow.py doctor --brief` 또는 `python3 flow.py status --brief`를 쓴다.
- 구현 전에 항상 `.workflow/tasks` 아래 task 문서를 먼저 만든다.
- scaffold 자체를 다룰 때는 `DESIGN.md`를 굳이 읽지 않아도 된다. 이 파일은 타깃 프로젝트 UI 기준 문서다.
- `.workflow/docs/UI_GUIDE.md`는 legacy fallback이다. 존재하지 않으면 이 파일은 무시한다.
- runner 선택은 `.workflow/config/ccs-map.yaml`을 따른다. `auto`면 `ccs`가 있으면 `ccs`, 없으면 `claude -p`를 사용한다.
- v0에서는 live 실행보다 `--dry-run` 검증을 기본으로 본다.
"""
SECTION = f"{START}\n{SECTION_BODY}{END}\n"
MANAGED_BLOCK_RE = re.compile(r"\n?<!-- so2x-flow:managed:start -->.*?<!-- so2x-flow:managed:end -->\n?", re.S)
UNMANAGED_SECTION_RE = re.compile(r"(?ms)^## so2x-flow\n.*?(?=^#{1,2}\s|\Z)")


def has_so2x_flow_section(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return (
        START in text and END in text
        or "## so2x-flow" in text
        or "# so2x-flow workspace guide" in text
    )


def patch_agents_md(target_root: Path) -> bool:
    path = target_root / "AGENTS.md"
    base = path.read_text(encoding="utf-8") if path.exists() else ""

    if START in base and END in base:
        updated = MANAGED_BLOCK_RE.sub(f"\n{SECTION}", base, count=1)
        if updated != base:
            path.write_text(updated, encoding="utf-8")
            return True
        return False

    if "## so2x-flow" in base:
        updated = UNMANAGED_SECTION_RE.sub(SECTION.rstrip(), base, count=1)
        if updated != base:
            if not updated.endswith("\n"):
                updated += "\n"
            path.write_text(updated, encoding="utf-8")
            return True
        return False

    if base and not base.endswith("\n"):
        base += "\n"
    if base and not base.endswith("\n\n"):
        base += "\n"
    path.write_text(f"{base}{SECTION}", encoding="utf-8")
    return True


if __name__ == "__main__":
    changed = patch_agents_md(Path.cwd())
    print("patched" if changed else "skipped")
