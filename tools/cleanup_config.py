#!/usr/bin/env python3
"""归一化清理输入：手动触发用 inputs（默认 dry-run），定时触发固定 apply=true keep=10。"""
from __future__ import annotations

import os
import sys

from github_api import write_output


def normalize(event: str, dispatch_apply: str, keep: str) -> tuple[str, str]:
    """按触发来源计算 (apply, keep)，两个值都是字符串（供 Action input 引用）。"""
    if event == "workflow_dispatch":
        apply = "true" if dispatch_apply == "true" else "false"
        return apply, (keep or "10")
    return "true", "10"


def main() -> int:
    event = os.environ.get("EVENT", "schedule")
    apply_value, keep_value = normalize(
        event,
        os.environ.get("DISPATCH_APPLY", ""),
        os.environ.get("KEEP", ""),
    )
    print(f"触发={event} apply={apply_value} keep={keep_value}")
    write_output("apply", apply_value)
    write_output("keep", keep_value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
