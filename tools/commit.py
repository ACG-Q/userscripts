#!/usr/bin/env python3
"""按路径白名单提交变更：git add <有变更的白名单路径> → 仅在有暂存变更时 commit/push。

先用 ``git status --porcelain`` 过滤白名单：不存在且未跟踪的路径（如新仓尚无
dist/archive 目录）直接传给 git add 会因 pathspec 不匹配而失败（fatal, rc=128）。
输出 ``committed=true/false``；无变更是正常短路（退出 0），不是错误。
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from github_api import write_output

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


def run_git(*args: str) -> subprocess.CompletedProcess:
    """执行 git 子命令并回显输出；失败由调用方按 returncode 处理。"""
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc


def changed_subset(git, paths: list[str]) -> tuple[list[str], str | None]:
    """返回白名单中存在未提交变更的子集；status 异常时返回错误消息。

    不存在且无跟踪文件的路径不产生 status 输出，因此被自然剔除。
    """
    wanted: list[str] = []
    for p in paths:
        proc = git("status", "--porcelain", "--", p)
        if proc.returncode != 0:
            return [], f"git status 异常（{p}，rc={proc.returncode}）"
        if proc.stdout.strip():
            wanted.append(p)
    return wanted, None


def main(argv=None, git=run_git) -> int:
    parser = argparse.ArgumentParser(description="按路径白名单提交变更")
    parser.add_argument("--allowlist", nargs="+", required=True, help="允许提交的路径")
    parser.add_argument("--message", required=True, help="commit message")
    args = parser.parse_args(argv)

    wanted, err = changed_subset(git, args.allowlist)
    if err:
        print(f"::error::{err}", file=sys.stderr)
        return 1
    if not wanted:
        print("无变更，跳过提交")
        write_output("committed", "false")
        return 0
    skipped = [p for p in args.allowlist if p not in wanted]
    if skipped:
        print(f"跳过无变更路径: {' '.join(skipped)}")

    if git("config", "user.name", BOT_NAME).returncode != 0:
        print("::error::git config user.name 失败", file=sys.stderr)
        return 1
    if git("config", "user.email", BOT_EMAIL).returncode != 0:
        print("::error::git config user.email 失败", file=sys.stderr)
        return 1
    if git("add", *wanted).returncode != 0:
        print("::error::git add 失败", file=sys.stderr)
        return 1

    diff_rc = git("diff", "--staged", "--quiet").returncode
    if diff_rc == 0:
        print("无变更，跳过提交")
        write_output("committed", "false")
        return 0
    if diff_rc != 1:
        print(f"::error::git diff --staged 异常（rc={diff_rc}）", file=sys.stderr)
        return 1

    if git("commit", "-m", args.message).returncode != 0:
        print("::error::git commit 失败", file=sys.stderr)
        return 1
    if git("push", "origin", "HEAD").returncode != 0:
        print("::error::git push 失败", file=sys.stderr)
        return 1
    write_output("committed", "true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
