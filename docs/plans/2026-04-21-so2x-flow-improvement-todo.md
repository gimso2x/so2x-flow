# so2x-flow 개선 TODO

**목표:** so2x-flow의 설치 UX, 문서 가독성, 테스트 유지보수성을 우선순위대로 개선한다.

## 우선순위

### P0 — 바로 체감되는 개선

1. **README install 섹션 압축 및 재구성**
   - 빠른 시작 카드
   - 성공 기준 표
   - Claude Code 경로 / shell 경로 분리
   - 반복 해설 축소

2. **install/README 테스트를 의미 기반으로 정리**
   - 장문 exact string assertion 축소
   - 핵심 계약(필수 명령, 성공 기준, next step, patch 검증) 중심으로 재작성
   - misleading test(`--force`)는 실제 overwrite contract에 맞게 수정

### P1 — 유지보수 리스크 감소

3. **`tests/test_execute.py` 중복 테스트명 제거**
   - `test_live_execution_requires_explicit_runtime_opt_in` 중복 제거/의도 분리

4. **README/skill 문서의 계약 테스트 계층화 기반 마련**
   - 이번 작업에서는 최소 정리만 하고, 이후 세분화 포인트를 남긴다.

### P2 — 다음 단계 후보

5. **feature live run fail-closed 강화**
   - 승인된 plan 없는 live feature 차단 강화 검토

6. **plan selection 정확도 개선**
   - slug/token 중심에서 artifact 내용 점수화 확장 검토

7. **doctor snapshot → event log 확장 검토**

---

## 이번 세션 실행 순서

1. 이 TODO 문서 작성
2. README install 섹션 압축
3. install/README 테스트 정리
4. `tests/test_execute.py` 중복 테스트명 제거
5. 관련 테스트 실행
6. 결과 확인 후 커밋 준비
