#!/usr/bin/env python3
"""命令面板幂等初始化：open issue 中已存在「命令面板」则跳过，否则创建。"""
from __future__ import annotations

import argparse
import sys

from github_api import api as gh_api
from github_api import require_env

DEFAULT_TITLE = "命令面板"
DEFAULT_BODY = "在此 Issue 下发送命令（如 `/list`、`/add <URL>`）以管理脚本。"
DEFAULT_LABEL = "command-panel"


def find_panel(api_func, repository: str, token: str):
    """返回 (panel|None, status)。只看 open issue，过滤 PR（issues 接口会混入 PR）。"""
    status, data = api_func("GET", f"/repos/{repository}/issues?state=open&per_page=100", token)
    if status != 200:
        return None, status
    for item in data or []:
        if "pull_request" in item:
            continue
        if DEFAULT_TITLE in (item.get("title") or ""):
            return item, 200
    return None, 200


def main(api_func=gh_api, argv=None) -> int:
    parser = argparse.ArgumentParser(description="命令面板幂等初始化")
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--body", default=DEFAULT_BODY)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    args = parser.parse_args(argv)

    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")

    panel, status = find_panel(api_func, repository, token)
    if status != 200:
        print(f"::error::查询面板失败 status={status}", file=sys.stderr)
        return 1
    if panel is not None:
        print(f"面板已存在：#{panel.get('number')}，跳过创建")
        return 0

    status, data = api_func(
        "POST", f"/repos/{repository}/issues", token,
        {"title": args.title, "body": args.body, "labels": [args.label]},
    )
    if status not in (200, 201):
        print(f"::error::创建面板失败 status={status} body={data}", file=sys.stderr)
        return 1
    print(f"面板已创建：#{(data or {}).get('number')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
