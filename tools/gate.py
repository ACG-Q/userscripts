#!/usr/bin/env python3
"""权限门禁：评论者 == 仓库拥有者；未授权则删除该评论并输出 authorized=false。"""
from __future__ import annotations

import sys

from github_api import api as gh_api
from github_api import require_env, write_output


def decide(comment_user: str, repo_owner: str) -> bool:
    """门禁判定：仅仓库拥有者被授权。"""
    return comment_user == repo_owner


def main(api_func=gh_api) -> int:
    comment_user = require_env("COMMENT_USER")
    repo_owner = require_env("REPO_OWNER")
    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")
    comment_id = require_env("COMMENT_ID")

    authorized = decide(comment_user, repo_owner)
    # 先写输出再删评论：删除失败时 job 变红，但 authorized=false 已落盘
    write_output("authorized", "true" if authorized else "false")
    if authorized:
        print(f"授权通过：{comment_user}")
        return 0

    status, body = api_func(
        "DELETE", f"/repos/{repository}/issues/comments/{comment_id}", token
    )
    if status != 204:
        print(f"::error::删除未授权评论失败 status={status} body={body}", file=sys.stderr)
        return 1
    print(f"未授权评论已删除：{comment_user}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
