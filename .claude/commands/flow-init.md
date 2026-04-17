# /flow-init

이 명령은 `.claude/skills/flow-init.md`를 호출하는 얇은 진입점이다.

## 역할
- so2x-flow 초기화 요청을 `flow-init` skill로 넘긴다.
- 실제 절차, 규칙, 생성물 기준은 skill과 `scripts/execute.py`가 기준이다.

## 입력
- 프로젝트 초기화 요청
- 필요하면 bootstrap 목적 설명

## 출력
- 초기화 관련 문서/설정 skeleton
- dry-run 또는 실행 결과 요약

## 참고
- 본체: `.claude/skills/flow-init.md`
- 실행기: `scripts/execute.py`
