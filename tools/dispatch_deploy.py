#!/usr/bin/env python3
"""显式派发 workflow_dispatch（GITHUB_TOKEN 的 push 不触发 workflow）。

派发失败只打 ::warning:: 并退出 0 —— 保持原 shell「不阻断」语义。
"""
from __future__ import annotations

import argparse
import os
import sys

from github_api import api as gh_api
from github_api import require_env


def main(api_func=gh_api, argv=None) -> int:
    parser = argparse.ArgumentParser(description="派发 GitHub workflow_dispatch")
    parser.add_argument("--workflow", required=True, help="workflow 文件名，如 deploy-pages.yml")
    parser.add_argument("--ref", default=None, help="分支（默认 GITHUB_REF_NAME，再退 master）")
    args = parser.parse_args(argv)

    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")
    ref = args.ref or os.environ.get("GITHUB_REF_NAME") or "master"

    status, body = api_func(
        "POST", f"/repos/{repository}/workflows/{args.workflow}/dispatches", token, {"ref": ref}
    )
    if status in (200, 201, 204):
        print(f"已派发 {args.workflow} @ {ref}")
        return 0
    print(f"::warning::站点部署派发失败（不阻断），可手动触发 {args.workflow} status={status} body={body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
