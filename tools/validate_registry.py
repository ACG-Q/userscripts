#!/usr/bin/env python3
"""registry.json 结构校验：可解析、scripts 为列表、每项含 id 且 type ∈ {self, synced}。"""
from __future__ import annotations

import argparse
import json
import sys

VALID_TYPES = ("self", "synced")


def validate(data) -> list[str]:
    """返回错误列表；空列表 = 通过。"""
    if not isinstance(data, dict):
        return ["registry 顶层必须是对象"]
    scripts = data.get("scripts")
    if not isinstance(scripts, list):
        return ["scripts 必须是列表"]
    errors = []
    for i, s in enumerate(scripts):
        if not isinstance(s, dict):
            errors.append(f"scripts[{i}] 必须是对象")
            continue
        if not s.get("id"):
            errors.append(f"scripts[{i}] 缺 id")
        if s.get("type") not in VALID_TYPES:
            errors.append(f"scripts[{i}] type 非法: {s.get('type')!r}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="registry.json 结构校验")
    parser.add_argument("--registry", default="registry.json", help="registry 路径")
    args = parser.parse_args(argv)
    try:
        with open(args.registry, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"::error::registry 无法读取/解析: {e}", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        for e in errors:
            print(f"::error::{e}", file=sys.stderr)
        return 1
    print(f"registry 校验通过：{len(data['scripts'])} 个脚本")
    return 0


if __name__ == "__main__":
    sys.exit(main())
