#!/usr/bin/env python3
"""把 dist/* 组装为 Pages 的 _site 结构：*.user.js → _site/dist/，其余 → _site/。"""
from __future__ import annotations

import argparse
import os
import shutil
import sys


def assemble(root: str) -> list[str]:
    """移动 dist 内容到 _site，返回落位路径列表；dist 缺失或为空抛 FileNotFoundError。"""
    dist = os.path.join(root, "dist")
    if not os.path.isdir(dist):
        raise FileNotFoundError("dist/ 不存在 —— build 未产出任何内容")
    entries = sorted(os.listdir(dist))
    if not entries:
        raise FileNotFoundError("dist/ 为空 —— build 未产出任何内容")
    site = os.path.join(root, "_site")
    site_dist = os.path.join(site, "dist")
    os.makedirs(site_dist, exist_ok=True)
    placed = []
    for name in entries:
        dst_dir = site_dist if name.endswith(".user.js") else site
        shutil.move(os.path.join(dist, name), os.path.join(dst_dir, name))
        placed.append(os.path.join(dst_dir, name))
    return placed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="组装 Pages 的 _site 目录")
    parser.add_argument("--root", default=".", help="仓库根目录（默认当前目录）")
    args = parser.parse_args(argv)
    try:
        placed = assemble(args.root)
    except FileNotFoundError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    print("--- _site 结构 ---")
    for path in placed:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
