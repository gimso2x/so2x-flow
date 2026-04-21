#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

START = "<!-- so2x-flow:managed:start -->"
END = "<!-- so2x-flow:managed:end -->"
SECTION_BODY = """## so2x-flow
- docs-first 실행에는 현재 프로젝트의 `.claude/skills` 아래 `flow-init`, `flow-feature`, `flow-fix`(=`flow-qa`), `flow-review`, `flow-plan`을 사용한다.
- 구현 전에 항상 `.workflow/tasks` 아래 task 문서를 먼저 만든다.
- scaffold 자체를 다룰 때는 `DESIGN.md`를 굳이 읽지 않아도 된다. 이 파일은 타깃 프로젝트 UI 기준 문서다.
- `.workflow/docs/UI_GUIDE.md`는 legacy fallback이다. 존재하지 않으면 이 파일은 무시한다.
- runner 선택은 `.workflow/config/ccs-map.yaml`을 따른다. `auto`면 `ccs`가 있으면 `ccs`, 없으면 `claude -p`를 사용한다.
- v0에서는 live 실행보다 `--dry-run` 검증을 기본으로 본다.
"""
SECTION = f"{START}\n{SECTION_BODY}{END}\n"
MANAGED_BLOCK_RE = re.compile(r"\n?<!-- so2x-flow:managed:start -->.*?<!-- so2x-flow:managed:end -->\n?", re.S)


def patch_claude_md(target_root: Path) -> bool:
    path = target_root / "CLAUDE.md"
    base = path.read_text(encoding="utf-8") if path.exists() else ""

    if START in base and END in base:
        updated = MANAGED_BLOCK_RE.sub(f"\n{SECTION}", base, count=1)
        if updated != base:
            path.write_text(updated, encoding="utf-8")
            return True
        return False

    if "## so2x-flow" in base:
        return False

    if base and not base.endswith("\n"):
        base += "\n"
    if base and not base.endswith("\n\n"):
        base += "\n"
    path.write_text(f"{base}{SECTION}", encoding="utf-8")
    return True


if __name__ == "__main__":
    changed = patch_claude_md(Path.cwd())
    print("patched" if changed else "skipped")
