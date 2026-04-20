# /flow-init

이 명령은 `.claude/skills/flow-init.md`를 호출하는 얇은 진입점이다.

## 역할
- so2x-flow 초기화 요청을 `flow-init` skill로 넘긴다.
- 실제 절차, 규칙, 생성물 기준은 skill과 `.workflow/scripts/execute.py`가 기준이다.

## 입력
- 프로젝트 초기화 요청
- 필요하면 bootstrap 목적 설명

## 출력
- `.workflow/tasks/init/<slug>.json` 질문지 산출물
- PRD/ARCHITECTURE/QA/DESIGN에 매핑된 질문 목록
- dry-run 또는 실행 결과 요약
- 시작 시 `1. 자동채우기 / 2. 질문` 중 하나를 고를 수 있음
- 초안으로 채울 수 있는 값은 먼저 반영하고, 남은 질문만 한 턴에 하나씩 이어가는 대화 흐름

## 참고
- 본체: `.claude/skills/flow-init.md`
- 실행기: `.workflow/scripts/execute.py`
