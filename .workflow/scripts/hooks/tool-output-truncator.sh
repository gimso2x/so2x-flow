#!/usr/bin/env sh
set -eu

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
case "$tool_name" in
  Bash|Grep|Glob)
    char_limit=12000
    ;;
  WebFetch|Read)
    char_limit=8000
    ;;
  *)
    exit 0
    ;;
esac

tool_output=$(printf '%s' "$input" | jq -r '.tool_response // empty')
[ -n "$tool_output" ] || exit 0

output_len=$(printf '%s' "$tool_output" | wc -c | tr -d ' ')
[ "$output_len" -gt "$char_limit" ] || exit 0

summary=$(printf '%s' "$tool_output" | python3 -c 'import re, sys
text = sys.stdin.read()
head = text[:5000]
tail = text[-2000:] if len(text) > 2000 else text
removed = max(len(text) - 7000, 0)
errs = []
for line in text.splitlines():
    if re.search(r"(Error|error|Traceback|traceback|Exception|exception|WARN|WARNING|failed|FAILED)", line):
        errs.append(line)
    if len(errs) >= 100:
        break
parts = [head, f"\n\n... [SUMMARY ONLY: {removed} chars omitted from additional context] ...\n\n", tail]
if errs:
    parts.extend(["\n\n--- [PRESERVED ERROR LINES] ---\n", "\n".join(errs)])
sys.stdout.write("".join(parts))')

context=$(printf 'Large %s output detected (%s chars). Adding a summarized view to reduce follow-up context pressure.\n\n%s' "$tool_name" "$output_len" "$summary")
jq -n --arg ctx "$context" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
