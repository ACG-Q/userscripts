# userscripts 辅助功能 Python 化与 workflow 去 shell 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
>
> **工作目录**：所有命令在 `C:\Users\LiuJi\Desktop\project-06\userscripts`（git 仓，remote = `ACG-Q/userscripts`）下执行（下文用 `<repo>` 表示）。
> **⚠️ 提交纪律**：仓里有一个**预先存在的** ` M README.md` 改动（与本计划无关）。每个任务只 `git add` 该任务列出的文件，**禁止 `git add -A`/`git add .`**。
> **规格**：`docs/superpowers/specs/2026-10-06-tools-aux-python-design.md`（设计决策 D1–D4 见其 §2）。

**目标：** 把 6 条 workflow 里 13 处内联 shell 逻辑全部下沉为 `tools/*.py`（本地可跑、带单元测试），yml 只剩一行式 `run: python tools/*.py`。

**架构：** 三层——yml 薄壳（触发/权限/if 门禁）→ `tools/*.py` 辅助脚本（纯标准库 + 注入式副作用）→ `acg-q/userscript-console` Action（核心功能，不动）。共享副作用收在 `tools/github_api.py`，测试注入 fake。

**技术栈：** Python 3（标准库；`validate_workflows.py` 沿用既有 `PyYAML`）、`unittest`（零新增依赖）、GitHub Actions。

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `tools/github_api.py` | 创建 | 副作用收口：GitHub REST 调用、`GITHUB_OUTPUT` 写入、`require_env` |
| `tools/gate.py` | 创建 | 权限门禁：评论者==拥有者；否则 DELETE 评论 |
| `tools/commit.py` | 创建 | 白名单 git 提交（add→有变更才 commit/push），输出 `committed` |
| `tools/dispatch_deploy.py` | 创建 | 派发 workflow_dispatch（失败只 `::warning::` 不阻断） |
| `tools/reply.py` | 创建 | 组装回帖正文（三态语义）并发布 |
| `tools/cleanup_config.py` | 创建 | 归一 apply/keep（dispatch 用 input，schedule 固定 true/10） |
| `tools/assemble_site.py` | 创建 | `dist/*` → `_site/`（`*.user.js` → `_site/dist/`） |
| `tools/init_panel.py` | 创建 | 面板 Issue 幂等检查 + 创建 |
| `tools/validate_registry.py` | 创建 | registry 结构校验（替内联 `python -c`） |
| `tools/tests/test_*.py` | 创建 | 每脚本对应单测（`unittest.TestCase`） |
| `.github/workflows/*.yml` | 修改 ×6 | 去内联 shell → 一行式 python 调用 |
| `tools/validate_workflows.py` | 修改 | 权限表 + 新"一行式 python"规则 |
| `docs-ownership.md` / `PLAN.md` / `SPEC-WORKFLOWS.md` | 修改 | 消除"tools 迁出/删除 Python/shell 纪律"三处规格冲突 |

**导入约定（必须遵守）**：脚本互引用**平级模块名**（`from github_api import ...`，因 `python tools/x.py` 时 `sys.path[0]=tools/`）；测试文件开头 `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))` 后 `import gate`。两类路径都靠 `tools/` 目录，**不要建 `tools/__init__.py`、不要用 `from tools import ...`**（两种运行方式会互相打架）。

---

## 任务 1：`tools/github_api.py` 共享辅助

**文件：**
- 创建：`tools/github_api.py`
- 测试：`tools/tests/test_github_api.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_github_api.py
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import github_api


class RequireEnvTest(unittest.TestCase):
    def test_present_returns_value(self):
        with mock.patch.dict(os.environ, {"FOO": "bar"}):
            self.assertEqual(github_api.require_env("FOO"), "bar")

    def test_missing_exits_2(self):
        env = dict(os.environ)
        env.pop("FOO", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                github_api.require_env("FOO")
        self.assertEqual(cm.exception.code, 2)


class WriteOutputTest(unittest.TestCase):
    def test_writes_to_github_output_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": path}):
                github_api.write_output("k", "v")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "k=v\n")

    def test_falls_back_to_stdout_without_env(self):
        env = dict(os.environ)
        env.pop("GITHUB_OUTPUT", None)
        with mock.patch.dict(os.environ, env, clear=True):
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                github_api.write_output("k", "v")
        self.assertEqual(buf.getvalue(), "k=v\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'github_api'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/github_api.py tools/tests/test_github_api.py
git commit -m "feat(tools): 新增 github_api 共享辅助（API 调用 / 输出写入 / env 读取）"
```

---

## 任务 2：`tools/gate.py` 权限门禁

**文件：**
- 创建：`tools/gate.py`
- 测试：`tools/tests/test_gate.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_gate.py
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gate


class FakeApi:
    def __init__(self, status=204):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, token))
        return self.status, None


def base_env(**extra):
    env = {
        "COMMENT_USER": "alice",
        "REPO_OWNER": "alice",
        "GITHUB_TOKEN": "tk",
        "GITHUB_REPOSITORY": "o/r",
        "COMMENT_ID": "42",
    }
    env.update(extra)
    return env


class GateTest(unittest.TestCase):
    def _run(self, api, extra=None):
        env = base_env(**(extra or {}))
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            env["GITHUB_OUTPUT"] = out
            with mock.patch.dict(os.environ, env, clear=False):
                code = gate.main(api_func=api)
            with open(out, encoding="utf-8") as f:
                content = f.read()
        return code, content

    def test_authorized_writes_true_and_calls_nothing(self):
        api = FakeApi()
        code, content = self._run(api)
        self.assertEqual(code, 0)
        self.assertEqual(content, "authorized=true\n")
        self.assertEqual(api.calls, [])

    def test_unauthorized_writes_false_and_deletes_comment(self):
        api = FakeApi()
        code, content = self._run(api, {"COMMENT_USER": "mallory"})
        self.assertEqual(code, 0)
        self.assertEqual(content, "authorized=false\n")
        self.assertEqual(api.calls, [("DELETE", "/repos/o/r/issues/comments/42", "tk")])

    def test_delete_failure_returns_1(self):
        api = FakeApi(status=500)
        code, _ = self._run(api, {"COMMENT_USER": "mallory"})
        self.assertEqual(code, 1)

    def test_missing_comment_id_exits_2(self):
        env = base_env(COMMENT_ID="")
        with tempfile.TemporaryDirectory() as td:
            env["GITHUB_OUTPUT"] = os.path.join(td, "out")
            with mock.patch.dict(os.environ, env, clear=False):
                with self.assertRaises(SystemExit) as cm:
                    gate.main(api_func=FakeApi())
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'gate'`（其余测试仍绿）

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/gate.py tools/tests/test_gate.py
git commit -m "feat(tools): 新增 gate.py 权限门禁（未授权删评论）"
```

---

## 任务 3：`tools/commit.py` 白名单提交

**文件：**
- 创建：`tools/commit.py`
- 测试：`tools/tests/test_commit.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_commit.py
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import commit

ARGV = ["--allowlist", "registry.json", "scripts", "--message", "test msg"]


class CommitTest(unittest.TestCase):
    def _run(self, rcs, argv=None):
        """rcs：按调用顺序消费的返回码；返回 (退出码, 输出内容, git 调用记录)。"""
        calls = []

        def fake_git(*args):
            calls.append(args)
            rc = rcs.pop(0) if rcs else 0
            return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": out}):
                code = commit.main(argv or ARGV, git=fake_git)
            content = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
        return code, content, calls

    def test_no_changes_writes_committed_false_and_skips(self):
        # git config ×2, git add, git diff --staged --quiet → 0（无差异）
        code, content, calls = self._run([0, 0, 0, 0])
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=false\n")
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_changes_commit_and_push(self):
        # ..., diff → 1（有差异）, commit → 0, push → 0
        code, content, calls = self._run([0, 0, 0, 1, 0, 0])
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=true\n")
        self.assertTrue(any(c[0] == "commit" and c[1] == "-m" for c in calls))
        self.assertTrue(any(c == ("push",) for c in calls))

    def test_add_failure_returns_1(self):
        code, _, calls = self._run([0, 0, 1])
        self.assertEqual(code, 1)
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_diff_error_returns_1(self):
        code, _, _ = self._run([0, 0, 0, 2])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'commit'`

- [ ] **步骤 3：编写最少实现代码**

```python
#!/usr/bin/env python3
"""按路径白名单提交变更：git add <allowlist> → 仅在有暂存变更时 commit/push。

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


def main(argv=None, git=run_git) -> int:
    parser = argparse.ArgumentParser(description="按路径白名单提交变更")
    parser.add_argument("--allowlist", nargs="+", required=True, help="允许提交的路径")
    parser.add_argument("--message", required=True, help="commit message")
    args = parser.parse_args(argv)

    if git("config", "user.name", BOT_NAME).returncode != 0:
        print("::error::git config user.name 失败", file=sys.stderr)
        return 1
    if git("config", "user.email", BOT_EMAIL).returncode != 0:
        print("::error::git config user.email 失败", file=sys.stderr)
        return 1
    if git("add", *args.allowlist).returncode != 0:
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
    if git("push").returncode != 0:
        print("::error::git push 失败", file=sys.stderr)
        return 1
    write_output("committed", "true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/commit.py tools/tests/test_commit.py
git commit -m "feat(tools): 新增 commit.py 白名单提交（committed 短路输出）"
```

---

## 任务 4：`tools/dispatch_deploy.py` 派发部署

**文件：**
- 创建：`tools/dispatch_deploy.py`
- 测试：`tools/tests/test_dispatch_deploy.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_dispatch_deploy.py
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dispatch_deploy


class FakeApi:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.status, None


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r", "GITHUB_REF_NAME": "master"}


class DispatchTest(unittest.TestCase):
    def _run(self, status, argv=None):
        api = FakeApi(status)
        with mock.patch.dict(os.environ, ENV, clear=False):
            code = dispatch_deploy.main(
                api_func=api, argv=argv or ["--workflow", "deploy-pages.yml"]
            )
        return code, api

    def test_success_posts_dispatches(self):
        code, api = self._run(204)
        self.assertEqual(code, 0)
        self.assertEqual(
            api.calls, [("POST", "/repos/o/r/workflows/deploy-pages.yml/dispatches",
                         {"ref": "master"})]
        )

    def test_failure_still_returns_0(self):
        code, api = self._run(404)
        self.assertEqual(code, 0)
        self.assertEqual(len(api.calls), 1)

    def test_explicit_ref_overrides_env(self):
        code, api = self._run(204, ["--workflow", "deploy-pages.yml", "--ref", "dev"])
        self.assertEqual(code, 0)
        self.assertEqual(api.calls[0][2], {"ref": "dev"})

    def test_missing_token_exits_2(self):
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                dispatch_deploy.main(api_func=FakeApi(204), argv=["--workflow", "w.yml"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'dispatch_deploy'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/dispatch_deploy.py tools/tests/test_dispatch_deploy.py
git commit -m "feat(tools): 新增 dispatch_deploy.py（派发失败不阻断）"
```

---

## 任务 5：`tools/reply.py` 回帖

**文件：**
- 创建：`tools/reply.py`
- 测试：`tools/tests/test_reply.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_reply.py
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import reply


class FakeApi:
    def __init__(self, status=201):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.status, None


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r", "ISSUE_NUMBER": "7"}


class ComposeTest(unittest.TestCase):
    def test_success_empty_result(self):
        self.assertEqual(reply.compose_body("", "", "success"), "**执行结果：**\n操作完成")

    def test_failure_prefix(self):
        body = reply.compose_body("部分结果", "", "failure")
        self.assertTrue(body.startswith("**执行结果：**\n⚠️ 命令执行失败（Run command: failure）"))
        self.assertIn("部分结果", body)

    def test_proj_appended(self):
        body = reply.compose_body("结果X", "投影Y", "success")
        self.assertEqual(body, "**执行结果：**\n结果X\n\n投影Y")

    def test_skipped_counts_as_success(self):
        self.assertEqual(reply.compose_body("R", "", "skipped"), "**执行结果：**\nR")


class MainTest(unittest.TestCase):
    def _run(self, extra, api):
        env = dict(ENV)
        env.update(extra)
        with mock.patch.dict(os.environ, env, clear=False):
            return reply.main(api_func=api)

    def test_posts_composed_body(self):
        api = FakeApi()
        code = self._run({"RESULT": "hello", "PROJ": "", "CMD_OK": "success"}, api)
        self.assertEqual(code, 0)
        method, path, payload = api.calls[0]
        self.assertEqual((method, path), ("POST", "/repos/o/r/issues/7/comments"))
        self.assertEqual(payload, {"body": "**执行结果：**\nhello"})

    def test_api_failure_returns_1(self):
        code = self._run({"RESULT": "", "PROJ": "", "CMD_OK": "success"}, FakeApi(500))
        self.assertEqual(code, 1)

    def test_missing_issue_number_exits_2(self):
        env = dict(ENV)
        env.pop("ISSUE_NUMBER")
        with mock.patch.dict(os.environ, env, clear=False):
            with self.assertRaises(SystemExit) as cm:
                reply.main(api_func=FakeApi())
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'reply'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
    status, _ = api_func("POST", f"/repos/{repository}/issues/{issue_number}/comments",
                         token, {"body": body})
    if status not in (200, 201):
        print(f"::error::回帖失败 status={status}", file=sys.stderr)
        return 1
    print("回帖成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/reply.py tools/tests/test_reply.py
git commit -m "feat(tools): 新增 reply.py 回帖（三态正文语义）"
```

---

## 任务 6：`tools/cleanup_config.py` 清理输入归一

**文件：**
- 创建：`tools/cleanup_config.py`
- 测试：`tools/tests/test_cleanup_config.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_cleanup_config.py
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cleanup_config


class NormalizeTest(unittest.TestCase):
    def test_schedule_is_always_real_cleanup(self):
        self.assertEqual(cleanup_config.normalize("schedule", "", ""), ("true", "10"))

    def test_dispatch_defaults_to_dry_run(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "", "5"), ("false", "5")
        )

    def test_dispatch_explicit_true(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "true", "20"), ("true", "20")
        )

    def test_dispatch_explicit_false(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "false", "10"), ("false", "10")
        )

    def test_dispatch_empty_keep_falls_back_to_10(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "false", ""), ("false", "10")
        )


class MainTest(unittest.TestCase):
    def test_main_writes_both_outputs(self):
        env = {"EVENT": "schedule", "DISPATCH_APPLY": "", "KEEP": ""}
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            env["GITHUB_OUTPUT"] = out
            with mock.patch.dict(os.environ, env, clear=False):
                code = cleanup_config.main()
            with open(out, encoding="utf-8") as f:
                content = f.read()
        self.assertEqual(code, 0)
        self.assertEqual(content, "apply=true\nkeep=10\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'cleanup_config'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/cleanup_config.py tools/tests/test_cleanup_config.py
git commit -m "feat(tools): 新增 cleanup_config.py 清理输入归一"
```

---

## 任务 7：`tools/assemble_site.py` `_site` 组装

**文件：**
- 创建：`tools/assemble_site.py`
- 测试：`tools/tests/test_assemble_site.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_assemble_site.py
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import assemble_site


class AssembleTest(unittest.TestCase):
    def _make_repo(self, td, entries):
        dist = os.path.join(td, "dist")
        os.makedirs(dist, exist_ok=True)
        for name in entries:
            path = os.path.join(dist, name)
            if name.endswith("/"):
                os.makedirs(path, exist_ok=True)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("x")
        return dist

    def test_user_js_to_site_dist_rest_to_site(self):
        with tempfile.TemporaryDirectory() as td:
            self._make_repo(td, ["a.user.js", "b.user.js", "index.html", "scripts/"])
            placed = assemble_site.assemble(td)
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "dist", "a.user.js")))
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "dist", "b.user.js")))
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "index.html")))
            self.assertTrue(os.path.isdir(os.path.join(td, "_site", "scripts")))
            self.assertEqual(len(placed), 4)

    def test_missing_dist_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                assemble_site.assemble(td)

    def test_empty_dist_raises(self):
        with tempfile.TemporaryDirectory() as td:
            self._make_repo(td, [])
            with self.assertRaises(FileNotFoundError):
                assemble_site.assemble(td)

    def test_main_returns_1_on_missing_dist(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(assemble_site.main(["--root", td]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'assemble_site'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/assemble_site.py tools/tests/test_assemble_site.py
git commit -m "feat(tools): 新增 assemble_site.py（dist → _site 组装）"
```

---

## 任务 8：`tools/init_panel.py` 面板初始化

**文件：**
- 创建：`tools/init_panel.py`
- 测试：`tools/tests/test_init_panel.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_init_panel.py
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import init_panel


class SeqApi:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.responses.pop(0)


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r"}
ISSUES_PATH = "/repos/o/r/issues?state=open&per_page=100"


class InitPanelTest(unittest.TestCase):
    def _run(self, api):
        with mock.patch.dict(os.environ, ENV, clear=False):
            return init_panel.main(api_func=api, argv=[])

    def test_existing_panel_skips_create(self):
        api = SeqApi([(200, [{"number": 1, "title": "命令面板"}])])
        self.assertEqual(self._run(api), 0)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][0], "GET")

    def test_missing_panel_creates_issue(self):
        api = SeqApi([(200, []), (201, {"number": 9})])
        self.assertEqual(self._run(api), 0)
        method, path, payload = api.calls[1]
        self.assertEqual((method, path), ("POST", "/repos/o/r/issues"))
        self.assertEqual(payload["title"], "命令面板")
        self.assertEqual(payload["labels"], ["command-panel"])
        self.assertIn("/list", payload["body"])

    def test_pull_request_with_same_title_is_ignored(self):
        api = SeqApi([(200, [{"number": 3, "title": "命令面板", "pull_request": {}}]),
                      (201, {"number": 9})])
        self.assertEqual(self._run(api), 0)
        self.assertEqual(len(api.calls), 2)

    def test_list_failure_returns_1(self):
        api = SeqApi([(500, None)])
        self.assertEqual(self._run(api), 1)

    def test_missing_token_exits_2(self):
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                init_panel.main(api_func=SeqApi([]), argv=[])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'init_panel'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/init_panel.py tools/tests/test_init_panel.py
git commit -m "feat(tools): 新增 init_panel.py 面板幂等初始化"
```

---

## 任务 9：`tools/validate_registry.py` registry 校验

**文件：**
- 创建：`tools/validate_registry.py`
- 测试：`tools/tests/test_validate_registry.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tools/tests/test_validate_registry.py
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import validate_registry

OK = {"schema": 1, "scripts": [{"id": "a", "type": "self"}]}


class ValidateTest(unittest.TestCase):
    def test_valid_returns_no_errors(self):
        self.assertEqual(validate_registry.validate(OK), [])

    def test_empty_registry_is_valid(self):
        self.assertEqual(validate_registry.validate({"schema": 1, "scripts": []}), [])

    def test_top_level_must_be_object(self):
        self.assertTrue(validate_registry.validate([]))

    def test_scripts_must_be_list(self):
        self.assertTrue(validate_registry.validate({"scripts": {"a": 1}}))

    def test_missing_id_reported(self):
        errors = validate_registry.validate({"scripts": [{"type": "self"}]})
        self.assertTrue(any("缺 id" in e for e in errors))

    def test_invalid_type_reported(self):
        errors = validate_registry.validate({"scripts": [{"id": "a", "type": "evil"}]})
        self.assertTrue(any("type 非法" in e for e in errors))


class MainTest(unittest.TestCase):
    def _run(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "registry.json"
            if data is not None:
                path.write_text(json.dumps(data), encoding="utf-8")
            return validate_registry.main(["--registry", str(path)])

    def test_valid_file_returns_0(self):
        self.assertEqual(self._run(OK), 0)

    def test_invalid_entry_returns_1(self):
        self.assertEqual(self._run({"scripts": [{"type": "synced"}]}), 1)

    def test_unparsable_file_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "registry.json"
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(validate_registry.main(["--registry", str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 1，`ModuleNotFoundError: No module named 'validate_registry'`

- [ ] **步骤 3：编写最少实现代码**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/validate_registry.py tools/tests/test_validate_registry.py
git commit -m "feat(tools): 新增 validate_registry.py（替内联 python -c）"
```

---

## 任务 10：重写 `issue-commands.yml`

**文件：**
- 修改：`.github/workflows/issue-commands.yml`（整体替换）

- [ ] **步骤 1：替换文件内容**

```yaml
name: Issue Commands Manager

on:
  issue_comment: { types: [created] }
permissions:
  contents: write
  issues: write
  actions: write
  discussions: write
concurrency:
  group: issue-commands
  cancel-in-progress: false

jobs:
  execute:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    # 仅命令面板 Issue #1、排除 PR 评论
    # Only command panel Issue #1, exclude PR comments
    if: ${{ !github.event.issue.pull_request && github.event.issue.number == 1 }}
    steps:
      # ① 统一先 checkout（设计 D2：门禁脚本 tools/gate.py 在仓库内）
      # Checkout first (D2: gate script lives in the repo)
      - uses: actions/checkout@v5

      # ② 权限门禁：未授权删除该评论（tools/gate.py）
      # Permission gate: delete comment if unauthorized (tools/gate.py)
      - name: Permission gate
        id: gate
        env:
          COMMENT_USER: ${{ github.event.comment.user.login }}
          REPO_OWNER: ${{ github.repository_owner }}
          COMMENT_ID: ${{ github.event.comment.id }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python tools/gate.py

      # ③ 执行命令（零手填二进制：@v1.1.0 + use-binary: true）
      # Run command (zero-config binary: @v1.1.0 + use-binary: true)
      - name: Run command
        id: cmd
        if: steps.gate.outputs.authorized == 'true'
        uses: acg-q/userscript-console@v1.1.0
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: ${{ github.event.comment.body }}
          comment-user: ${{ github.event.comment.user.login }}
          issue-number: ${{ github.event.issue.number }}
          use-binary: true

      # ④ 投影对账（命令可能改了 registry）
      # Project issues (command may have changed registry)
      - name: Project issues
        id: proj
        if: steps.gate.outputs.authorized == 'true'
        uses: acg-q/userscript-console@v1.1.0
        with:
          command: project
          github-token: ${{ secrets.GITHUB_TOKEN }}
          use-binary: true

      # ⑤ 提交（路径白名单，changed=false 时不提交）
      # Commit (path allowlist, skip if changed=false)
      - name: Commit changes
        id: commit
        if: steps.gate.outputs.authorized == 'true' && steps.cmd.outputs.changed == 'true'
        run: >-
          python tools/commit.py --allowlist registry.json scripts dist archive
          --message "Apply command: ${{ github.event.comment.user.login }}"

      # ⑥ 派发部署（GITHUB_TOKEN push 不触发 workflow，需显式派发）
      # Trigger deploy (GITHUB_TOKEN push doesn't trigger workflow, must dispatch explicitly)
      - name: Trigger site deploy
        if: steps.gate.outputs.authorized == 'true' && steps.commit.outputs.committed == 'true'
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: python tools/dispatch_deploy.py --workflow deploy-pages.yml

      # ⑦ 失败也回帖（逐字沿用现规范）
      # Reply even on failure (keep existing spec)
      - name: Reply to comment
        if: ${{ !cancelled() && steps.gate.outputs.authorized == 'true' }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          RESULT: ${{ steps.cmd.outputs.result }}
          PROJ: ${{ steps.proj.outputs.result }}
          CMD_OK: ${{ steps.cmd.outcome }}
        run: python tools/reply.py
```

- [ ] **步骤 2：跑 workflow 校验**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`（旧规则 6 只检查 `run: |` 块，一步式 python 会跳过；权限/触发器/超时/`!cancelled`/pin/use-binary 均不变）

- [ ] **步骤 3：跑全量测试确认无回归**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/issue-commands.yml
git commit -m "ci: issue-commands 去内联 shell，门禁/提交/派发/回帖改调 tools/*.py"
```

---

## 任务 11：重写 `sync-scheduled.yml`

**文件：**
- 修改：`.github/workflows/sync-scheduled.yml`（整体替换）

- [ ] **步骤 1：替换文件内容**

```yaml
name: Scheduled Sync

on:
  workflow_dispatch:

permissions:
  contents: write
  issues: write
  actions: write
  discussions: write
concurrency:
  group: scheduled-sync
  cancel-in-progress: false

jobs:
  sync-all:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5

      # 执行 /sync-all（身份注入与原版一致：以仓库拥有者名义执行）
      # Run /sync-all (identity injected as repo owner, same as before)
      - name: Run /sync-all
        id: cmd
        uses: acg-q/userscript-console@v1.1.0
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: /sync-all
          comment-user: ${{ github.repository_owner }}
          issue-number: '1'
          use-binary: true

      # 投影对账
      # Project issues
      - name: Project issues
        id: proj
        uses: acg-q/userscript-console@v1.1.0
        with:
          command: project
          github-token: ${{ secrets.GITHUB_TOKEN }}
          use-binary: true

      # 提交变更（白名单 registry/scripts/dist；无更新则 committed=false 短路）
      # Commit changes (allowlist; committed=false short-circuits when no update)
      - name: Commit changes
        id: commit
        run: python tools/commit.py --allowlist registry.json scripts dist --message "chore: 同步第三方脚本"

      # 派发站点部署（仅在真提交后）
      # Trigger site deploy (only after a real commit)
      - name: Trigger site deploy
        if: steps.commit.outputs.committed == 'true'
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: python tools/dispatch_deploy.py --workflow deploy-pages.yml
```

> 注意输出名变更：原 `pushed` → 统一为 `committed`（与另两条 workflow 一致）。

- [ ] **步骤 2：跑 workflow 校验**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`

- [ ] **步骤 3：跑全量测试**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/sync-scheduled.yml
git commit -m "ci: sync-scheduled 去内联 shell，输出名 pushed 统一为 committed"
```

---

## 任务 12：重写 `cleanup-panel.yml`

**文件：**
- 修改：`.github/workflows/cleanup-panel.yml`（整体替换）

- [ ] **步骤 1：替换文件内容**

```yaml
name: Cleanup Command Panel
on:
  schedule:
    - cron: '0 3 * * *'
  workflow_dispatch:
    inputs:
      apply:
        description: 'true=真正删除超期评论；false=dry-run 只体检（默认 dry-run，更安全）'
        type: boolean
        default: false
        required: false
      keep:
        description: '每个命令组保留的最近评论数（≤ 组内评论总数时不会删除任何评论）'
        type: string
        default: '10'
        required: false

permissions:
  contents: write   # 提交 archive/commands.json
  issues: write     # 删除命令面板历史评论
  actions: write    # 派发 deploy-pages.yml

concurrency:
  group: cleanup-panel
  # 不取消：定时任务撞车时排队执行，避免「清理到一半被取消」留下半截归档
  # Don't cancel: queue scheduled runs to avoid partial archive from cancellation
  cancel-in-progress: false

jobs:
  cleanup:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v5
        with:
          # 归档是累积文件，历史可能被并发 push 改动；浅克隆下 git push 会被拒，要完整历史。
          # Archive is cumulative; shallow clone causes push rejection, need full history.
          fetch-depth: 0

      # 清理输入归一（手动触发用 inputs 默认 dry-run；定时触发固定 apply=true keep=10）
      # Normalize inputs (dispatch uses inputs, schedule forces apply=true keep=10)
      - name: 清理输入 / Cleanup inputs
        id: cfg
        env:
          EVENT: ${{ github.event_name }}
          DISPATCH_APPLY: ${{ inputs.apply }}
          KEEP: ${{ inputs.keep }}
        run: python tools/cleanup_config.py

      # 零手填二进制：@v1.1.0 + use-binary: true
      # Zero-config binary: @v1.1.0 + use-binary: true
      - name: Archive and clean / 归档与清理
        id: clean
        uses: acg-q/userscript-console@v1.1.0
        with:
          command: cleanup
          github-token: ${{ secrets.GITHUB_TOKEN }}
          keep: ${{ steps.cfg.outputs.keep }}
          apply: ${{ steps.cfg.outputs.apply }}
          use-binary: true

      # 提交归档（changed=false 或归档无差异 → committed=false 短路）
      # Commit archive (changed=false or no archive diff → committed=false)
      - name: 提交归档 / Commit archive
        id: commit
        if: steps.clean.outputs.changed == 'true'
        run: python tools/commit.py --allowlist archive --message "chore(archive): 归档命令面板历史评论"

      # 派发站点重建（仅在真的提交了归档时；GITHUB_TOKEN push 不触发 workflow）
      # Dispatch rebuild (only after archive commit; GITHUB_TOKEN push doesn't trigger)
      - name: 派发站点重建 / Dispatch site rebuild
        if: steps.commit.outputs.committed == 'true'
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: python tools/dispatch_deploy.py --workflow deploy-pages.yml
```

> 变更说明：删除原 `if: always()` 汇总步骤（信息由各脚本自身日志覆盖，见设计 §4.2）。

- [ ] **步骤 2：跑 workflow 校验**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`

- [ ] **步骤 3：跑全量测试**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/cleanup-panel.yml
git commit -m "ci: cleanup-panel 去内联 shell，删除汇总步骤（日志由脚本输出）"
```

---

## 任务 13：重写 `deploy-pages.yml`

**文件：**
- 修改：`.github/workflows/deploy-pages.yml:40-59`（仅"组装 _site"步骤）

- [ ] **步骤 1：替换组装步骤**

把这一段：

```yaml
      # 组装 _site 目录结构（Pages 特有，属本仓）
      # Assemble _site directory structure (Pages-specific, belongs to this repo)
      - name: 组装 _site / Assemble _site
        shell: bash
        run: |
          set -euo pipefail
          if [ ! -d dist ]; then
            echo "::error::dist/ 不存在 —— build 未产出任何内容"
            exit 1
          fi
          mkdir -p _site/dist
          # 站点页面：index.html / scripts.json / scripts/ / commands/
          # Site pages: index.html / scripts.json / scripts/ / commands/
          for item in dist/*; do
            base=$(basename "$item")
            case "$base" in
              *.user.js) mv "$item" _site/dist/ ;;   # 安装包放 _site/dist/ / Install packages to _site/dist/
              *)          mv "$item" _site/ ;;         # 其余是站点产物 / Rest are site artifacts
            esac
          done
          echo "--- _site 结构 / _site structure ---"
          find _site -maxdepth 2 | head -30
```

替换为（文件其余部分一字不动，替换范围严格限定为上面整块）：

```yaml
      # 组装 _site 目录结构（Pages 特有，属本仓）
      # Assemble _site directory structure (Pages-specific, belongs to this repo)
      - name: 组装 _site / Assemble _site
        run: python tools/assemble_site.py
```

- [ ] **步骤 2：跑 workflow 校验**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`

- [ ] **步骤 3：跑全量测试**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/deploy-pages.yml
git commit -m "ci: deploy-pages 的 _site 组装改调 tools/assemble_site.py"
```

---

## 任务 14：重写 `validate.yml`

**文件：**
- 修改：`.github/workflows/validate.yml:18-22`

- [ ] **步骤 1：替换 registry 校验步骤**

把：

```yaml
      # registry 可解析且结构合法
      # registry is parseable and structurally valid
      - name: registry 可解析且结构合法 / Validate registry structure
        run: |
          python -c "import json,sys; d=json.load(open('registry.json',encoding='utf-8')); assert isinstance(d.get('scripts'),list); [_ for s in d['scripts'] if not s.get('id') or s.get('type') not in ('self','synced') and (_ for _ in ()).throw(SystemExit('缺 id/type: '+str(s)))]"
```

替换为：

```yaml
      # registry 可解析且结构合法（本地可直接跑：python tools/validate_registry.py）
      # registry is parseable and structurally valid (runnable locally too)
      - name: registry 可解析且结构合法 / Validate registry structure
        run: python tools/validate_registry.py
```

doctor Action 步骤与文件其余部分不动。

- [ ] **步骤 2：本地真跑一次该校验**

运行：`python tools/validate_registry.py`
预期：退出码 0，`registry 校验通过：0 个脚本`（当前 registry 为空）

- [ ] **步骤 3：跑 workflow 校验 + 全量测试**

运行：`python tools/validate_workflows.py; python -m unittest discover tools/tests -q`
预期：两者均退出码 0

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/validate.yml
git commit -m "ci: validate 的 registry 内联 python -c 改调 tools/validate_registry.py"
```

---

## 任务 15：重写 `init-command-panel.yml` + 同步权限表（同一提交）

**文件：**
- 修改：`.github/workflows/init-command-panel.yml`（整体替换）
- 修改：`tools/validate_workflows.py:27`（`SPEC_PERMS` 的 init 行）

> 必须同任务改：新 workflow 加 `contents: read` 会让旧权限校验变红，规则表必须原子同步。

- [ ] **步骤 1：替换 workflow 文件内容**

```yaml
name: Init Command Panel
on:
  workflow_dispatch:
permissions:
  issues: write
  contents: read   # 设计 D2：先 checkout 才能跑 tools/init_panel.py

jobs:
  init:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      # 统一先 checkout（D2；原「刻意不 checkout」设计已由 tools/init_panel.py 取代）
      # Checkout first (D2; replaces the old no-checkout design)
      - uses: actions/checkout@v5

      # 面板存在性检查 + 创建（幂等：已存在则跳过）
      # Check existence + create (idempotent: skip when present)
      - name: Init command panel / 初始化面板
        run: python tools/init_panel.py
```

- [ ] **步骤 2：同步权限表**

`tools/validate_workflows.py` 中：

```python
    'init-command-panel.yml':  {'issues':'write'},
```

改为：

```python
    'init-command-panel.yml':  {'issues':'write','contents':'read'},
```

- [ ] **步骤 3：跑 workflow 校验 + 全量测试**

运行：`python tools/validate_workflows.py; python -m unittest discover tools/tests -q`
预期：两者均退出码 0（权限表与新 workflow 一致）

- [ ] **步骤 4：Commit**

```powershell
git add .github/workflows/init-command-panel.yml tools/validate_workflows.py
git commit -m "ci: init-command-panel 接入 checkout + tools/init_panel.py，权限表同步 contents: read"
```

---

## 任务 16：`validate_workflows.py` 新规则（run 必须是一行式 python）

**文件：**
- 修改：`tools/validate_workflows.py:66-87`（第 6 节整体替换）
- 修改：`tools/validate_workflows.py:187`（汇总输出行）

- [ ] **步骤 1：替换第 6 节**

把第 6 节（原 `# ── 6. set -euo pipefail on run steps ──` 到第 87 行 `errors.append(...missing set -euo pipefail...)` 为止的整块）替换为：

```python
# ── 6. run 步骤必须是一行式 python tools/*.py（禁止内联 shell 逻辑） ────────
# 设计 D1：辅助功能下沉 tools/*.py；yml 只留调用，不留 bash 逻辑。
RUN_PATTERN = re.compile(r'python tools/[a-z_]+\.py( .*)?')
for f in SPEC_PERMS:  # 全部 6 条 workflow
    _, doc, _ = load_wf(f)
    for job_name, job in (doc.get('jobs') or {}).items():
        for step in job.get('steps') or []:
            run = step.get('run')
            if run is None:
                continue
            line = str(run).strip()
            if not RUN_PATTERN.fullmatch(line):
                errors.append(
                    f'{f} [{job_name}]: run 步骤必须是一行式 python tools/*.py，'
                    f'实际: {line[:80]!r}')
```

- [ ] **步骤 2：更新汇总输出**

第 187 行：

```python
print('  euo pipefail: critical run steps covered')
```

改为：

```python
print('  run steps:    one-line python tools/*.py (6 workflows)')
```

- [ ] **步骤 3：验证新规则双向生效**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`

然后临时把 `.github/workflows/validate.yml` 的 `run: python tools/validate_registry.py` 改成两行 `run: |` 形式，再运行：
预期：退出码 1，错误信息含 `run 步骤必须是一行式`
改回原样后再运行：预期退出码 0。

- [ ] **步骤 4：跑全量测试**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`

- [ ] **步骤 5：Commit**

```powershell
git add tools/validate_workflows.py
git commit -m "ci(validate): 规则 6 从 set -euo pipefail 改为一行式 python tools/*.py 校验"
```

---

## 任务 17：文档同步（消除三处规格冲突）

**文件：**
- 修改：`docs-ownership.md`
- 修改：`PLAN.md`
- 修改：`SPEC-WORKFLOWS.md`

- [ ] **步骤 1：改 `docs-ownership.md`**

1. 「迁出 → 工具仓」表中删除这一行：
   ```markdown
   | `tools/**` | 工具脚本（含 `validate_graphql.py`） |
   ```
2. 「保留在本仓」表中 `docs/index.md` 行之前插入：
   ```markdown
   | `tools/**` | 辅助 Python 脚本（gate/commit/dispatch_deploy/reply/assemble_site/cleanup_config/init_panel/validate_registry/validate_workflows）+ `tools/tests/` 单元测试 |
   ```
3. 「核对」小节的 grep 正则里删掉 `tools/|`（注意保留其余模式），并把"本仓检查保留路径"命令改为：
   ```bash
   ls registry.json scripts/ dist/ archive/ docs/index.md README.md .github/workflows/ tools/*.py 2>/dev/null && echo "✓ 保留路径存在"
   ```

- [ ] **步骤 2：改 `PLAN.md`**

1. U1-1 任务单元格末尾追加（该行清单里有 `tools/`）：
   ```markdown
   **（U4-1 修订：`tools/` 不迁，保留本仓作辅助脚本，见 2026-10-06 设计）**
   ```
2. U4-1 行整行替换为：
   ```markdown
   | U4-1 | 删除迁出路径（`U0-3` 清单中的全部项，**但 `tools/` 除外**） | 本仓只剩数据 + workflow + 辅助 Python + 用户文档 | 业务 Python（`manager.py` 等）不存在；`tools/*.py` 保留；`tests/` 不存在 | ⏳ 待观察期结束后 |
   ```
3. U4-2 行整行替换为：
   ```markdown
   | U4-2 | 删除 `requirements.txt`、`ruff.toml`、`mypy.ini`、`.coveragerc`；`.gitignore` 去掉测试相关条目 | 配置瘦身 | CI 不再 `pip install`（`tools/*.py` 纯标准库；本地 `validate_workflows.py` 沿用既有 `PyYAML`） | ⏳ 待观察期结束后 |
   ```

- [ ] **步骤 3：改 `SPEC-WORKFLOWS.md`**

1. **§0 四条纪律 → 五条**，第 3、4 条替换，并加第 5 条：
   ```markdown
   3. 失败路径必须有回帖/告警（`!cancelled()` 回帖步骤；脚本失败以非 0 退出码让 job 变红）；
   4. `GITHUB_TOKEN` 的 push 不触发 workflow → 需要重建站点时运行 `python tools/dispatch_deploy.py --workflow deploy-pages.yml`；
   5. 所有 `run:` 步骤必须是**一行式 `python tools/*.py`**，禁止内联 shell 逻辑（`validate_workflows.py` 规则 6 自动校验）。
   ```
2. **§1.1** 标题与正文替换为：
   ```markdown
   ### 1.1 `init-command-panel.yml` —— **接入 Python（设计 D2）**

   `workflow_dispatch` + `issues: write` + `contents: read`（D2：统一先 checkout 才能跑仓库内脚本）+ `python tools/init_panel.py`（幂等：open issue 中已有「命令面板」则跳过）。
   **验收**：dispatch 两次，第二次应识别为「已存在」而不重复建 Issue #1。
   ```
3. **§1.2** 代码块中的内联 `python -c` 步骤替换为：
   ```yaml
       - name: registry 可解析且结构合法
         run: python tools/validate_registry.py
   ```
4. **§2.1–§2.4** 的四个 yaml 代码块：整体替换为对应 workflow 文件的完整内容（以 `.github/workflows/issue-commands.yml`、`deploy-pages.yml`、`sync-scheduled.yml`、`cleanup-panel.yml` 为准，即任务 10–13 的产物——SPEC 是蓝本，文件是真源，两处必须逐字一致）。
5. **§2.4 实现说明**里"末尾加 `if: always()` 的汇总步骤"一条改为：
   ```markdown
   > - 无汇总步骤：各脚本（`cleanup_config.py`/`commit.py`/`dispatch_deploy.py`）自身打印关键日志，触发来源由 `cleanup_config.py` 的 `触发=...` 行给出。
   ```
6. **§3 表** `init-command-panel.yml` 行替换为：
   ```markdown
   | `init-command-panel.yml` | `issues: write`（建面板）`contents: read`（checkout 读 `tools/*.py`） | 缺 issues → 无法建面板；缺 contents → checkout 失败 |
   ```
7. **§4 表后**追加一句：
   ```markdown
   > 白名单现由 `tools/commit.py --allowlist` 执行：yml 里不再出现 `git add` 字样，脚本内部固定 `git config` 身份 + 有暂存变更才 commit/push。
   ```
8. **§6 checklist** 第 5 条替换为：
   ```markdown
   - [ ] 失败路径：`run:` 为一行式 `python tools/*.py`（`validate_workflows.py` 自动校验）；需要回帖的有 `!cancelled()`
   ```

- [ ] **步骤 4：验证文档与文件一致**

运行：`python tools/validate_workflows.py`
预期：退出码 0（文档改动不影响校验，此步防手滑破坏 yml）

目视核对：SPEC-WORKFLOWS §2.1 代码块与 `.github/workflows/issue-commands.yml` 内容一致（其余三条同理）。

- [ ] **步骤 5：Commit**

```powershell
git add docs-ownership.md PLAN.md SPEC-WORKFLOWS.md
git commit -m "docs: 同步 tools/ 归属、U4 瘦身口径与 workflow 一行式 python 规格"
```

---

## 任务 18：总验收

**文件：** 无新改动（只验证；发现问题则修复后重跑）

- [ ] **步骤 1：全量单测**

运行：`python -m unittest discover tools/tests -q`
预期：退出码 0，`OK`（9 个测试文件全绿）

- [ ] **步骤 2：workflow 纪律校验**

运行：`python tools/validate_workflows.py`
预期：退出码 0，`ALL CHECKS PASSED`，且汇总含 `run steps:    one-line python tools/*.py (6 workflows)`

- [ ] **步骤 3：确认 yml 中无残留多行 shell**

运行（PowerShell）：

```powershell
Select-String -Path .github\workflows\*.yml -Pattern 'run: \|'
```

预期：无任何匹配输出。

- [ ] **步骤 4：本地冒烟（可独立运行的脚本）**

```powershell
python tools/validate_registry.py
python tools/gate.py
$td = Join-Path $env:TEMP "usm-assemble"
Remove-Item -Recurse -Force $td -ErrorAction SilentlyContinue
New-Item -ItemType Directory "$td\dist" | Out-Null
Set-Content "$td\dist\a.user.js" "x"
Set-Content "$td\dist\index.html" "<html/>"
python tools/assemble_site.py --root $td
Get-ChildItem -Recurse "$td\_site" | Select-Object -ExpandProperty FullName
python -m unittest discover tools/tests -q
```

预期：第 1 条退出码 0（`registry 校验通过：0 个脚本`）；第 2 条退出码 2 且报 `缺少必需环境变量 COMMENT_USER`（证明本地可跑、缺参报错清晰）；组装命令退出码 0，输出列表含 `_site\dist\a.user.js` 与 `_site\index.html`；最后一条 `OK`。

- [ ] **步骤 5：真实事件回归（需推送到远端后手动执行，不自动 commit）**

1. push 全部提交到 `ACG-Q/userscripts`（**等用户明确指示再 push**）；
2. Issue #1 发 `/list` → 回帖正常、`git status` 只含预期路径、`deploy-pages` 被派发；
3. 用非拥有者账号评论 → 评论被删、无回帖；
4. Actions 手动 dispatch `cleanup-panel.yml`（默认 dry-run）→ 输出 `触发=workflow_dispatch apply=false keep=10`、`committed=false`；
5. Actions 手动 dispatch `init-command-panel.yml` 两次 → 第二次输出「面板已存在，跳过创建」。

- [ ] **步骤 6：收尾**

```powershell
git status --short
```

预期：除预先存在的 ` M README.md` 与 `docs/superpowers/`（本计划/规格文档，尚未提交）外，无未提交改动。把计划文档与规格文档一并提交：

```powershell
git add docs/superpowers/
git commit -m "docs: 落盘辅助功能 Python 化设计与实现计划"
```
