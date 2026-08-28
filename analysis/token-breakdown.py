#!/usr/bin/env python3
"""Reconstruct the tool-call cost breakdown from a coding-agent session log (JSON lines).

Answers the only two questions that matter after a delegation run:
  1. How many tokens did the delegated model consume?
  2. How much of that was raw tool output vs the model's own exploration loop?

Usage:
  python3 token-breakdown.py session.jsonl
"""

import json
import sys
from collections import defaultdict


def main(path: str) -> None:
    calls = 0
    total_output_bytes = 0
    per_tool_bytes: dict[str, int] = defaultdict(int)
    per_tool_calls: dict[str, int] = defaultdict(int)
    biggest: list[tuple[int, str]] = []

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = entry.get("part") or entry
            if entry.get("type") != "tool_use" and part.get("type") != "tool_use":
                continue
            tool = part.get("tool") or part.get("state", {}).get("tool") or "unknown"
            state = part.get("state", {})
            output = state.get("output", "")
            if isinstance(output, dict):
                output = json.dumps(output)
            size = len(output) if isinstance(output, str) else 0
            calls += 1
            per_tool_calls[tool] += 1
            per_tool_bytes[tool] += size
            total_output_bytes += size
            biggest.append((size, str(tool)))

    biggest.sort(reverse=True)
    print(f"tool calls:            {calls}")
    print(f"total output bytes:    {total_output_bytes:,}")
    print(f"approx raw tokens:     ~{total_output_bytes // 4:,} (rough 4 bytes/token)")
    print()
    print("per-tool breakdown (calls, output bytes):")
    for tool, size in sorted(per_tool_bytes.items(), key=lambda kv: -kv[1]):
        print(f"  {tool:<40} {per_tool_calls[tool]:>4} calls  {size:>12,} bytes")
    print()
    print("top 5 largest single tool outputs:")
    for size, tool in biggest[:5]:
        print(f"  {size:>12,} bytes  {tool}")
    print()
    print("Reading: if raw output is a small fraction of the session's token bill,")
    print("the rest is the model's exploration loop (re-reads, re-derivation) —")
    print("the cost lever is prompt design, not a bigger context.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
