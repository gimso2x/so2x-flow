#!/usr/bin/env sh
set -eu

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
[ "$tool_name" = "Edit" ] || [ "$tool_name" = "Write" ] || exit 0

error=$(printf '%s' "$input" | jq -r '.error // empty')
[ -n "$error" ] || exit 0

guidance=""
case "$error" in
  *"not found"*|*"does not contain"*|*"old_string"*)
    guidance="EDIT RECOVERY: old_string을 못 찾았다. 지금 파일을 다시 읽고 exact context를 더 길게 잡아서 다시 시도해라."
    ;;
  *"multiple"*|*"not unique"*|*"ambiguous"*)
    guidance="EDIT RECOVERY: 매치가 여러 군데다. 주변 2~3줄을 더 포함해서 old_string을 유일하게 만들어라."
    ;;
  *"identical"*|*"must be different"*)
    guidance="EDIT RECOVERY: old_string과 new_string이 같다. 실제 변경이 있는지 먼저 확인해라."
    ;;
  *"No such file"*|*"ENOENT"*|*"not exist"*)
    guidance="EDIT RECOVERY: 대상 파일 경로가 틀렸을 가능성이 크다. 파일 경로를 다시 확인해라."
    ;;
  *"Permission denied"*|*"EACCES"*|*"read-only"*)
    guidance="EDIT RECOVERY: 권한 문제다. 파일 권한이나 보호된 경로 여부를 먼저 확인해라."
    ;;
  *)
    exit 0
    ;;
esac

jq -n --arg ctx "$guidance" '{hookSpecificOutput:{hookEventName:"PostToolUseFailure",additionalContext:$ctx}}'
