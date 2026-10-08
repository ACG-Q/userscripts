#!/usr/bin/env python3
"""用 GitHub 官方 GraphQL schema 校验工具仓 Go 源码中的全部查询与变更。

背景：单测里的假客户端按「查询子串」路由，字段名写错照样全绿——
`Query.discussion` 这类不存在的字段只有线上真请求才暴露。本工具在 CI 里提前拦截。

用法::
    python tools/validate_graphql.py --go-dir tool-src
    python tools/validate_graphql.py --go-dir ../userscript-console --offline

schema 来源：docs.github.com/public/fpt/schema.docs.graphql，
缓存于 tools/schema.docs.graphql（已 gitignore），GITHUB_SCHEMA_FILE 可覆盖。
依赖：graphql-core（MIT；GraphQL 校验无标准库实现，见 AGENTS.md §3 说明）。
退出码非 0 = 存在语法错误/非法字段/不存在的 schema 字段。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

SCHEMA_URL = "https://docs.github.com/public/fpt/schema.docs.graphql"
DEFAULT_CACHE = Path(__file__).resolve().parent / "schema.docs.graphql"
BACKTICK_RE = re.compile(r"`([^`]+)`", re.S)
QUERYISH_RE = re.compile(r"\b(query|mutation|subscription)\b")


def collect_go_queries(go_dir: Path) -> dict[str, str]:
    """收集 Go 源码反引号字面量中含 query/mutation 的文本（键=相对路径#序号）。"""
    queries: dict[str, str] = {}
    for path in sorted(go_dir.rglob("*.go")):
        text = path.read_text(encoding="utf-8")
        for i, lit in enumerate(BACKTICK_RE.findall(text)):
            if QUERYISH_RE.search(lit):
                rel = path.relative_to(go_dir).as_posix()
                queries[f"{rel}#{i}"] = lit
    return queries


def download_schema() -> str:
    last = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(SCHEMA_URL, timeout=120) as resp:
                data = resp.read().decode("utf-8")
            if len(data) < 100_000:
                raise RuntimeError(f"下载内容异常：仅 {len(data)} 字节")
            return data
        except Exception as e:
            last = e
            print(f"schema 下载失败（第 {attempt}/3 次）：{e}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise SystemExit(f"schema 下载失败：{last}")


def load_schema(path: Path, offline: bool):
    from graphql import build_schema
    if not path.exists():
        if offline:
            raise SystemExit(f"离线模式下找不到 schema：{path}")
        print(f"下载 schema → {path}", file=sys.stderr)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_text(download_schema(), encoding="utf-8")
        tmp.replace(path)
    # assume_valid：GitHub 官方 schema 自带不一致的 @deprecated 元数据，
    # graphql-core 会拒绝整个 schema；我们只需要字段定义做查询校验。
    return build_schema(path.read_text(encoding="utf-8"), assume_valid=True)


def validate_text(schema, name: str, text: str) -> list[str]:
    """返回错误消息列表；空 = 通过。"""
    from graphql import parse, validate
    try:
        document = parse(text)
    except Exception as e:
        return [f"语法错误 {e}"]
    return [err.message for err in validate(schema, document)]


def main(argv=None) -> int:
    # Windows 控制台默认 GBK，打不出 ✓/✗；重配为 UTF-8 并容错替换。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--go-dir", type=Path, default=None,
                        help="工具仓根（默认 env TOOL_REPO_ROOT 或 ../userscript-console）")
    parser.add_argument("--schema", type=Path,
                        default=Path(os.environ.get("GITHUB_SCHEMA_FILE") or DEFAULT_CACHE),
                        help="schema SDL 路径")
    parser.add_argument("--offline", action="store_true", help="不下载，只用本地 schema")
    args = parser.parse_args(argv)

    go_dir = args.go_dir or Path(os.environ.get("TOOL_REPO_ROOT") or "../userscript-console")
    if not go_dir.is_dir():
        print(f"::error::工具仓目录不存在: {go_dir}", file=sys.stderr)
        return 1
    schema = load_schema(args.schema, args.offline)
    queries = collect_go_queries(go_dir)
    if not queries:
        print(f"::error::在 {go_dir} 未找到任何 GraphQL 文本", file=sys.stderr)
        return 1
    failed = 0
    for name, text in queries.items():
        errs = validate_text(schema, name, text)
        if errs:
            failed += 1
            for e in errs:
                print(f"✗ {name}: {e}", file=sys.stderr)
        else:
            print(f"✓ {name}")
    if failed:
        print(f"\n{failed}/{len(queries)} 个查询未通过 schema 校验", file=sys.stderr)
        return 1
    print(f"\n全部 {len(queries)} 个查询通过 schema 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
