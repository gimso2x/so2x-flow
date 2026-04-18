#!/usr/bin/env sh
set -eu

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
[ -n "$session_id" ] || exit 0

tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
[ -n "$tool_name" ] || exit 0

root_dir="$HOME/.so2x-flow/hooks"
state_dir="$root_dir/$session_id"
state_file="$state_dir/failure-counts.json"
mkdir -p "$state_dir"
find "$root_dir" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null || true

count=$(python3 - "$state_file" "$tool_name" <<'PY'
import json, os, sys, time
path, tool = sys.argv[1:3]
now = int(time.time())
window = 60
state = {"failures": []}
if os.path.exists(path):
    try:
        state = json.load(open(path, encoding='utf-8'))
    except Exception:
        state = {"failures": []}
failures = [f for f in state.get("failures", []) if f.get("ts", 0) >= now - window]
failures.append({"tool": tool, "ts": now})
state["failures"] = failures
with open(path, 'w', encoding='utf-8') as fh:
    json.dump(state, fh, ensure_ascii=False)
print(sum(1 for f in failures if f.get('tool') == tool))
PY
)

guidance=""
if [ "$count" -ge 5 ]; then
  guidance="STAGNATION DETECTED: $tool_name 실패가 최근 60초에 $count회 반복됐다. 같은 방식 재시도 말고 파일 재읽기/로그 확인/다른 접근으로 바꿔라."
elif [ "$count" -ge 3 ]; then
  guidance="REPEATED FAILURE: $tool_name 실패가 최근 60초에 $count회 반복됐다. 같은 전략을 멈추고 컨텍스트를 다시 읽은 뒤 다른 접근으로 바꿔라."
else
  exit 0
fi

jq -n --arg ctx "$guidance" '{hookSpecificOutput:{hookEventName:"PostToolUseFailure",additionalContext:$ctx}}'
