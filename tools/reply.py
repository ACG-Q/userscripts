#!/usr/bin/env python3
"""组装并发布命令执行结果回帖（失败也回帖，语义对齐原 shell 逐字行为）。"""
from __future__ import annotations

import os
import sys

from github_api import api as gh_api
from github_api import require_env


def compose_body(result: str, proj: str, cmd_ok: str) -> str:
    """按原 shell 三态语义拼回帖正文。"""
    body = result if result else "操作完成"
    if cmd_ok not in ("success", "skipped"):
        body = f"⚠️ 命令执行失败（Run command: {cmd_ok}），请查看本次运行日志。\n\n{body}"
    if proj:
        body = f"{body}\n\n{proj}"
    return f"**执行结果：**\n{body}"


def main(api_func=gh_api) -> int:
    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")
    issue_number = require_env("ISSUE_NUMBER")

    body = compose_body(
        os.environ.get("RESULT", ""),
        os.environ.get("PROJ", ""),
        os.environ.get("CMD_OK", "success"),
    )
    status, _ = api_func(
        "POST", f"/repos/{repository}/issues/{issue_number}/comments", token, {"body": body}
    )
    if status not in (200, 201):
        print(f"::error::回帖失败 status={status}", file=sys.stderr)
        return 1
    print("回帖成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
