#!/usr/bin/env python3
"""共享副作用收口：GitHub REST 调用、GITHUB_OUTPUT 写入、必需环境变量读取。

测试时可把 ``api`` 替换为 fake（同签名可调用对象），不触网。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

API_ROOT = "https://api.github.com"


def require_env(name: str) -> str:
    """读取必需环境变量；缺失视为用法错误，退出码 2。"""
    value = os.environ.get(name, "")
    if not value:
        print(f"::error::缺少必需环境变量 {name}", file=sys.stderr)
        sys.exit(2)
    return value


ApiFunc = Callable[..., tuple[int, Any]]


def api(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, Any]:
    """调用 GitHub REST API，返回 ``(status, parsed_json)``。

    4xx/5xx 不抛异常、不退出，语义由调用方决定（如派发失败只警告）；
    网络层不可达视为运行时错误，退出码 1。
    """
    url = f"{API_ROOT}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = None
        return e.code, parsed
    except urllib.error.URLError as e:
        print(f"::error::GitHub API 网络错误 {method} {path}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def write_output(key: str, value: str) -> None:
    """写步骤输出：CI 写 ``$GITHUB_OUTPUT``，本地无该变量时降级为打印。"""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    else:
        print(f"{key}={value}")
