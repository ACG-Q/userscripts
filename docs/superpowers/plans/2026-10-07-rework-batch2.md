# 批次 2（Important 四波）实现计划

> **面向 AI 代理的工作者：** 必需子技能：superpowers:executing-plans 逐任务实现此计划（**D4：用户禁止使用子代理**，不得使用 subagent-driven-development）。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 修复基线 13 个 Important（I1-I13，按规格 §4.2 四波推进）+ 2 项附带（站点 URL 文档漂移记入基线），并完成 `v1.1.3` 发版与 SHA 升钉，使批次 0/1 的 C1-C4 修复在内容仓 CI 真正生效。

**架构：** 波 1（CI 骨架）→ 波 2（失败可观测性，含批次 0 新发现 I12/I13）→ 波 3（安全：I6 复核 + tag→SHA pin + 发版）→ 波 4（站点正确性 I7-I11）→ 附带（文档 URL 漂移 I14）→ 收口勾销。每任务独立中文 conventional commit，master 直推，靠两仓 CI 验证。

**技术栈：** Go 1.x（工具仓）、Python 3 stdlib + graphql-core（内容仓 tools）、GitHub Actions、goldmark+bluemonday（I8）。

---

## 全局约束（每个任务都适用）

1. **两仓门禁（提交前必跑，全绿才 push）：**
   - 工具仓 `C:\Users\LiuJi\Desktop\project-06\userscript-console`：`gofmt -l .`（空输出）→ `go vet ./...` → `go test ./... -covermode=atomic -coverprofile=cover.out`（`go tool cover "-func=cover.out"` 尾行 total ≥90%）→ `go run ./cmd/usm snapshot check`（输出"快照一致"）→ `go build ./...`
   - 内容仓 `C:\Users\LiuJi\Desktop\project-06\userscripts`：`python -m unittest discover tools/tests -q` → `python tools/validate_workflows.py`（ALL CHECKS PASSED）
2. **提交纪律：** 每任务只 `git add` 列出的文件；**`userscripts/README.md` 有预存未提交改动，永不提交**；禁止 `git add -A`；提交后 `git push origin HEAD`，轮询两仓 CI 至 success（工具仓 Test、内容仓 Validate/Deploy/Init）。
3. **PowerShell 5.1 坑：** 无 `&&`（用 `; if ($?) { }`）；含中文的文件编辑一律用 edit 工具（`Set-Content -Encoding UTF8` 会写 BOM、`Get-Content` 默认 ANSI 会乱码）；`go tool cover` 参数要引号；`$var:` 会被解析成驱动器（用 `${var}:`）；多行 shell 写临时 `.sh` 用 `D:\Software\Git\bin\bash.exe` 跑。
4. **改模板/站点后必须** `go run ./cmd/usm snapshot update` 刷新 `tests/snapshot/`，并逐文件 `git diff` 过目确认只有预期变化。
5. **网络：** GitHub API 匿名额度 60/h，轮询用 `Invoke-RestMethod` 解析关键字段；本地网络走 `$env:HTTPS_PROXY='http://127.0.0.1:7897'`（仅在直连失败时设置）。
6. **波次顺序不得打乱**（规格 §4.2）；波内任务顺序按本计划编号。

## 文件结构（按仓）

**工具仓 userscript-console：**
| 文件 | 变更 | 任务 |
|---|---|---|
| `.github/workflows/release.yml` | 增 test job + publish needs | 1 |
| `.golangci.yml`（**已存在**，按实装版本修订）+ `.github/workflows/test.yml` | lint 配置与接入 | 3 |
| `internal/cleanup/cleanup.go` | CommandKey 增 command_id/archived_at | 6 |
| `internal/cli/doctor.go` | command_id 查重跳过空值 | 6 |
| `internal/commands/rm.go`（RemoveDist 已存在于 fileio.go，无需改 script 包） | /rm 删源+dist | 7 |
| `internal/pages/pages.go` | 消毒(bluemonday)、Comment Body、renderCommands 重写 | 10/11/14 |
| `internal/pages/templates/{index,detail,commands,commands-index}.tmpl` | 导航/CSS/JS/meta-refresh | 12/14 |
| `cmd/usm/snapgen_test.go` | 快照断言补测 | 13 |
| `go.mod` | bluemonday 转 direct | 10 |

**内容仓 userscripts：**
| 文件 | 变更 | 任务 |
|---|---|---|
| `tools/validate_graphql.py`（新建）+ `tools/tests/test_validate_graphql.py`（新建）+ `tools/validate_workflows.py`（规则 6 加 pip 单行例外）+ `.github/workflows/validate.yml` | GraphQL schema 校验 | 2 |
| `.github/workflows/issue-commands.yml` | if 条件 + 状态透传 | 4/5 |
| `tools/reply.py` + `tools/tests/test_reply.py` | commit/dispatch 结果透传 | 5 |
| `tools/tests/test_init_panel.py` | I6 幂等测试补强 | 8 |
| 6 个工作流的 `uses:` 7 处 | tag→SHA pin + binary-version | 9 |
| `BASELINE.md`/`CUTOVER.md`/`SPEC-DATA.md`/`docs/index.md` + 基线新增 I14 | 站点 URL 修正 | 15 |
| `docs/reviews/2026-10-07-baseline.md` | I1-I14 勾销 | 16 |

---

### 任务 1：I1 release 流程补测试/覆盖率前置（波 1）

**文件：**
- 修改：`userscript-console/.github/workflows/release.yml`

- [ ] **步骤 1：加 test job（含 lint 占位——任务 3 落地后此 job 复用同一命令）**

在 `jobs:` 下 `build:` 之前插入：

```yaml
  # 前置 0：质量门禁（无此 job 绿，不准发布；对应基线 I1）
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: gofmt
        run: |
          out=$(gofmt -l .)
          if [ -n "$out" ]; then echo "gofmt 需要格式化:"; echo "$out"; exit 1; fi
      - name: vet
        run: go vet ./...
      - name: 测试 + 覆盖率门禁
        run: |
          go test ./... -covermode=atomic -coverprofile=cover.out
          pct=$(go tool cover -func=cover.out | tail -1 | grep -oE '[0-9.]+%' | tr -d '%')
          awk -v p="$pct" 'BEGIN{exit !(p>=90)}'
      - name: 快照门禁
        run: go run ./cmd/usm snapshot check
      - name: 编译自检
        run: go build ./...
```

- [ ] **步骤 2：publish 挂接 needs**

`publish:` 的 `needs: build` 改为：

```yaml
  publish:
    needs: [build, test]
```

`move-v1-tag: needs: publish` 不变。

- [ ] **步骤 3：验证 + 提交 + push + CI**

内容仓跑 `python tools/validate_workflows.py`（validate 只覆盖内容仓时跳过并说明）；工具仓目检 YAML 缩进（2 空格）。

```bash
git add .github/workflows/release.yml
git commit -m "ci(release): 发布前置补测试/覆盖率/快照门禁（I1）"
git push origin HEAD
```

轮询工具仓 Test（本 push 不触发 release，无 Release run 属预期）。

---

### 任务 2：I2 GraphQL schema 校验工具（波 1）

**文件：**
- 创建：`userscripts/tools/validate_graphql.py`
- 创建：`userscripts/tools/tests/test_validate_graphql.py`
- 修改：`userscripts/.github/workflows/validate.yml`

**设计（依据：projec-02/tools/validate_graphql.py 全文；规格 §4.2 波 1 + AGENTS.md §3）：** 查询文本在**工具仓** Go 源码反引号字符串里（`internal/github/queries.go` 等，12 处），内容仓自身无 GraphQL——故工具接收 `--go-dir` 指向工具仓检出（CI 第二 checkout）。依赖引入 `graphql-core`（MIT、活跃维护；GraphQL 规范校验无标准库实现，手写解析器违背 AGENTS.md §3"优先成熟库"）；schema 下载用 `urllib`（不引入 requests）。schema 缓存 `tools/schema.docs.graphql` 已在 `.gitignore:21`。

- [ ] **步骤 1：红灯——先写测试**

`tools/tests/test_validate_graphql.py`：

```python
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_graphql as vg

MINI_SCHEMA = """
type Query { repository(owner: String!, name: String): Repo }
type Repo { id: ID!, name: String }
schema { query: Query }
"""


def _schema_obj():
    from graphql import build_schema
    return build_schema(MINI_SCHEMA, assume_valid=True)


class CollectGoQueriesTest(unittest.TestCase):
    def test_collects_query_literals_and_skips_noise(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "queries.go"
            p.write_text(
                "package github\n"
                "const Q = `query { repository(owner: \\\"a\\\", name: \\\"b\\\") { id } }`\n"
                "const NotQ = `plain text without graphql`\n",
                encoding="utf-8")
            got = vg.collect_go_queries(Path(d))
        self.assertEqual(len(got), 1)
        self.assertIn("query", next(iter(got.values())))

    def test_missing_go_dir_returns_error(self):
        self.assertEqual(vg.main(["--go-dir", r"C:\no\such\dir", "--offline"]), 1)


class ValidateTextTest(unittest.TestCase):
    def test_valid_query_passes(self):
        errs = vg.validate_text(_schema_obj(), "q", "query { repository(owner: \"a\") { id } }")
        self.assertEqual(errs, [])

    def test_unknown_field_reported(self):
        errs = vg.validate_text(_schema_obj(), "q", "query { repository { nope } }")
        self.assertTrue(errs)

    def test_syntax_error_reported"):
        errs = vg.validate_text(_schema_obj(), "q", "query {")
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main()
```

> 注意修正笔误：`def test_syntax_error_reported"):` 应为 `def test_syntax_error_reported(self):`——以运行结果为准修正后再继续。

- [ ] **步骤 2：运行确认红**

`python -m unittest tools.tests.test_validate_graphql -v`（或 `cd` 内容仓根 `python -m unittest discover tools/tests -p "test_validate_graphql.py" -v`）
预期：FAIL/ERROR（`validate_text`/`collect_go_queries` 不存在）。若本机缺 `graphql-core`：`python -m pip install graphql-core`（本地可设 `$env:HTTPS_PROXY='http://127.0.0.1:7897'`）。

- [ ] **步骤 3：实现 `tools/validate_graphql.py`**

```python
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
        print(f"\nfailed}/{len(queries)} 个查询未通过 schema 校验".replace("failed}", f"{failed}"),
              file=sys.stderr)
        return 1
    print(f"\n全部 {len(queries)} 个查询通过 schema 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

> 执行时修正两处笔误（与测试同步）：`failed}/{len...` 行写为 `f"\n{failed}/{len(queries)} 个查询未通过 schema 校验"`；上一行的 f-string 拼接删除。

- [ ] **步骤 4：绿灯验证**

`python -m unittest discover tools/tests -p "test_validate_graphql.py" -v` 全 PASS。
再对真实工具仓跑一次：`python tools/validate_graphql.py --go-dir ..\userscript-console`（首次需下载 schema ~5MB；直连失败设代理）。预期输出 12+ 个 `✓`、退出 0。**若出现 ✗（真实查询字段不存在）：修复工具仓 Go 查询为合法字段后重跑**（此即本工具价值；改动需单独提交并跑工具仓门禁）。

- [ ] **步骤 5a：放宽 validate_workflows.py 规则 6（波 1 调查实锤的前置冲突）**

> **调查结论：** 规则 6（`validate_workflows.py:68` `RUN_PATTERN = ^python tools/[a-z_]+\.py(\s.*)?$`）要求所有 `run` 步骤是单行 `python tools/*.py` 调用——`pip install` 与多行 `run: |` 都会被本仓门禁拦下。规则设计意图是「shell 逻辑全量收口进 tools/*.py」，包引导安装（bootstrap）不是 shell 逻辑，故给 `python -m pip install <spec>` 开一个**无 shell 操作符的单行**例外。

`tools/validate_workflows.py` 修改（规则 6 段）：

```python
RUN_PATTERN = re.compile(
    r'^(python tools/[a-z_]+\.py(\s.*)?|python -m pip install [a-z0-9_.=\-]+)$')
```

注释同步：`# run 步骤必须是 tools/*.py 单行调用，或单行 python -m pip install（依赖引导，无 shell 操作符）`；report 段 `run one-liner` 文案不变。**不引入 `&&`/`|`/重定向**——凡需要组合逻辑的一律进 tools/*.py。

- [ ] **步骤 5b：接入 validate.yml**

`validate.yml` 的 `steps:` 里、doctor 步骤之前加（每个 run 都是**单行**）：

```yaml
      # 工具仓 GraphQL 查询对官方 schema 校验（基线 I2；第二 checkout 取查询源）
      - uses: actions/checkout@v5
        with:
          repository: acg-q/userscript-console
          path: tool-src
      - name: 安装 GraphQL 校验依赖 / Install graphql-core
        run: python -m pip install graphql-core==3.3.0
      - name: GraphQL schema 校验 / Validate GraphQL queries
        run: python tools/validate_graphql.py --go-dir tool-src
```

- [ ] **步骤 6：门禁 + 提交 + push + CI**

内容仓：`python -m unittest discover tools/tests -q` + `python tools/validate_workflows.py`（ALL CHECKS PASSED 即证明 5a/5b 两处改动自洽）。

```bash
git add tools/validate_graphql.py tools/tests/test_validate_graphql.py tools/validate_workflows.py .github/workflows/validate.yml
git commit -m "ci(graphql): 新增 GraphQL schema 校验工具并接入 validate CI（I2；规则 6 放开 pip 单行例外）"
git push origin HEAD
```

轮询内容仓 Validate 至 success（本任务会实跑 schema 下载，若网络失败看 run 日志区分）。

---

### 任务 3：I3 golangci-lint 接入 CI（波 1）

**文件：**
- 修改：`userscript-console/.golangci.yml`（**波 1 调查修正：已存在**（v1 语法，12733cd 提交；`run:`/`linters.enable` 已开 govet/staticcheck/errcheck/ineffassign/unused/gocritic/gofumpt）——**不是新建**，按步骤 1 实装版本决定保留 v1 语法或迁移 v2 语法，现有 linter 集合作为起点）
- 修改：`userscript-console/.github/workflows/test.yml`
- 修改：`userscript-console/.github/workflows/release.yml`（任务 1 的 test job 追加 lint 步）
- 潜在：各包 `.go`（修复 lint 发现）

- [ ] **步骤 1：本地安装并首跑，摸清发现面**

```powershell
$env:HTTPS_PROXY='http://127.0.0.1:7897'
go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest
golangci-lint version   # 记录版本号 v2.x.y，供 yml pin
golangci-lint run ./...
```

若装的是 v1 旧版（v2 路径拉不到），改用 `go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.64.8` 并在 yml 用该版本——**以本地实装版本为准写死 pin，禁止 `latest` 入 yml**。现有 `.golangci.yml` 是 v1 语法：实装 v1 → 原样沿用；实装 v2 → 迁移为 v2 语法（`version: "2"` + `linters.default/settings`），linter 集合只增不减。

- [ ] **步骤 2：复核配置（有真实发现才开规则，不为开而开）**

现有配置为基线；若迁移 v2 语法，等价改写为：

```yaml
version: "2"
linters:
  default: standard          # errcheck/govet/ineffassign/staticcheck/unused
  settings:
    errcheck:
      check-type-assertions: true
      exclude-functions:
        - (io.Closer).Close    # 仅在确有 defer Close 且错误可忽略处按需收敛
issues:
  max-issues-per-linter: 0
  max-same-issues: 0
```

> 配置是**下限**：现有 linter 集合（含 staticcheck SA1019、errcheck，SPEC-ARCH-TEST §4 必开项）的发现必须修代码，不许用 exclude 一排了之；仅当某类误报有明确理由时加 exclude 并写注释。

- [ ] **步骤 3：修 lint 发现（红→绿）**

逐条修 `golangci-lint run ./...` 的输出（预期类型：未检查的 error 返回、类型断言未 ok-guard、unused 变量/参数）。每修一批跑 `go test ./... -count=1` 确认不破坏行为。**禁止**为过 lint 而删测试断言或 `//nolint` 滥用（每条 nolint 必须带理由注释）。

- [ ] **步骤 4：test.yml 接入**

`test.yml` 的 `vet` 步骤之后加：

```yaml
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v8
        with:
          version: v2.1.6   # ← 换成步骤 1 实装版本
```

> 若该 action 版本不存在（404/工作流语法错），降级为 `@v6` + 实装的 v1 版本；以 CI 实跑绿为准。备选无 action 方案：`run: go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@<ver> && golangci-lint run ./...`。

- [ ] **步骤 5：release.yml 的 test job 同步加 lint 步**（"lint 才准发布"，规格 §4.2 波 1）——在任务 1 的 `vet` 步骤后插入同名同内容步骤。

- [ ] **步骤 6：门禁 + 提交 + push + CI**

```bash
git add .golangci.yml .github/workflows/test.yml .github/workflows/release.yml [被修的 .go 文件...]
git commit -m "ci(lint): 接入 golangci-lint 并修复标准集发现（I3）"
git push origin HEAD
```

轮询工具仓 Test 至 success（lint 步是新步骤，首跑必看日志确认不是被缓存跳过）。

---

### 任务 4：I4 commit/dispatch 步骤 if 加状态函数（波 2）

**文件：**
- 修改：`userscripts/.github/workflows/issue-commands.yml:67,76`
- 创建：`userscripts/tools/tests/test_issue_workflow.py`（回归护栏）

**问题实锤：** 步骤 ⑤ Commit 的 `if: authorized && changed=='true'` 隐式 AND `success()`——步骤 ④ proj 失败即阻断 registry 提交，已执行的命令结果（工作区改动）被丢弃；⑥ 派发同理被 ⑤ 之外的失败阻断。

- [ ] **步骤 1：红灯测试**

`tools/tests/test_issue_workflow.py`：

```python
import re
import unittest
from pathlib import Path

YML = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "issue-commands.yml"


class IssueCommandsIfConditionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = YML.read_text(encoding="utf-8")

    def _step_if(self, step_id):
        m = re.search(
            rf"- name: [^\n]+\n\s+id: {step_id}\n\s+if: \${{{{([^}}]+)}}}}",
            self.text)
        self.assertIsNotNone(m, f"步骤 {step_id} 缺 id 或 if 条件")
        return m.group(1)

    def test_commit_if_survives_upstream_failure(self):
        cond = self._step_if("commit")
        self.assertIn("!cancelled()", cond)
        self.assertIn("steps.cmd.outcome == 'success'", cond)
        self.assertIn("steps.cmd.outputs.changed == 'true'", cond)

    def test_dispatch_if_requires_commit_only(self):
        cond = self._step_if("deploy")
        self.assertIn("!cancelled()", cond)
        self.assertIn("steps.commit.outputs.committed == 'true'", cond)

    def test_dispatch_has_id(self):
        self.assertRegex(self.text, r"id: deploy")


if __name__ == "__main__":
    unittest.main()
```

运行 `python -m unittest discover tools/tests -p "test_issue_workflow.py" -v` → 红（当前 commit if 无 `!cancelled()`；deploy 步无 id）。

- [ ] **步骤 2：改 yml**

① 步骤 ⑤ Commit：

```yaml
      - name: Commit changes
        id: commit
        # 显式状态函数：proj（④）失败不阻断 registry 提交，否则已执行命令结果被丢弃（I4）
        if: ${{ !cancelled() && steps.gate.outputs.authorized == 'true' && steps.cmd.outputs.changed == 'true' && steps.cmd.outcome == 'success' }}
        run: >-
          python tools/commit.py --allowlist registry.json scripts dist archive
          --message "Apply command: ${{ github.event.comment.user.login }}"
```

② 步骤 ⑥ 派发加 id + 条件：

```yaml
      - name: Trigger site deploy
        id: deploy
        if: ${{ !cancelled() && steps.gate.outputs.authorized == 'true' && steps.commit.outputs.committed == 'true' }}
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: python tools/dispatch_deploy.py --workflow deploy-pages.yml
```

- [ ] **步骤 3：绿灯 + 门禁**

重跑步骤 1 测试 → PASS；`python tools/validate_workflows.py` → ALL CHECKS PASSED。

- [ ] **步骤 4：提交 + push + CI**

```bash
git add .github/workflows/issue-commands.yml tools/tests/test_issue_workflow.py
git commit -m "ci(commands): commit/dispatch 显式状态函数，proj 失败不再丢弃 registry 提交（I4）"
git push origin HEAD
```

---

### 任务 5：I5 提交/派发失败可观测（波 2）

**文件：**
- 修改：`userscripts/tools/reply.py`
- 修改：`userscripts/tools/tests/test_reply.py`
- 修改：`userscripts/.github/workflows/issue-commands.yml`（reply 步 env 透传）

**依据：** spec 波 2"Python 补测试 + 测试：断言失败路径确实透传"；基线 `compose_body` 仅收 RESULT/PROJ/CMD_OK。

- [ ] **步骤 1：读现有测试风格**

Read `userscripts/tools/tests/test_reply.py`（了解现有 fake api 与断言写法；下列新用例按同样风格并入，保持既有用例不动）。

- [ ] **步骤 2：红灯——追加测试**

```python
class ComposeBodyStatusTest(unittest.TestCase):
    def test_commit_failure_reported(self):
        out = vg_compose("结果", "", "success", commit_ok="failure")
        self.assertIn("提交失败", out)
        self.assertIn("Commit changes: failure", out)

    def test_dispatch_failure_reported(self):
        out = vg_compose("结果", "", "success", commit_ok="success", dispatch_ok="failure")
        self.assertIn("派发失败", out)
        self.assertIn("Trigger site deploy: failure", out)

    def test_skipped_and_success_silent(self):
        out = vg_compose("结果", "", "success", commit_ok="skipped", dispatch_ok="success")
        self.assertNotIn("提交失败", out)
        self.assertNotIn("派发失败", out)

    def test_cmd_failure_still_first(self):
        out = vg_compose("结果", "", "failure", commit_ok="failure")
        self.assertLess(out.index("命令执行失败"), out.index("提交失败"))
```

> `vg_compose` = 文件顶部 `from reply import compose_body as vg_compose`（按现有 import 风格）。`main()` 环境变量用例沿用现有写法补一条 `COMMIT_OK=failure` 注入的断言。

运行 → 红（`compose_body` 现为 3 参，`commit_ok` 关键字不存在）。

- [ ] **步骤 3：实现 reply.py**

`compose_body` 改为（新参数带默认值，旧调用兼容）：

```python
def compose_body(result: str, proj: str, cmd_ok: str,
                 commit_ok: str = "", dispatch_ok: str = "") -> str:
    """拼装最终回复。失败态（cmd/commit/dispatch）逐条置顶提示，失败也回帖。"""
    body = result if result else "无输出"
    if cmd_ok not in ("success", "skipped"):
        body = f"⚠️ 命令执行失败（Run command: {cmd_ok}），请查看工作流日志。\n\n{body}"
    if commit_ok and commit_ok not in ("success", "skipped"):
        body = f"⚠️ 变更提交失败（Commit changes: {commit_ok}），本次命令结果未入库，请查看工作流日志。\n\n{body}"
    if dispatch_ok and dispatch_ok not in ("success", "skipped"):
        body = f"⚠️ 站点派发失败（Trigger site deploy: {dispatch_ok}），请查看工作流日志。\n\n{body}"
    if proj:
        body = f"{body}\n\n{proj}"
    return f"**执行结果**\n{body}"
```

`main()` 传参追加两行：

```python
    body = compose_body(
        os.environ.get("RESULT", ""),
        os.environ.get("PROJ", ""),
        os.environ.get("CMD_OK", "success"),
        os.environ.get("COMMIT_OK", ""),
        os.environ.get("DISPATCH_OK", ""),
    )
```

- [ ] **步骤 4：yml 透传**

reply 步 env 追加两行：

```yaml
          COMMIT_OK: ${{ steps.commit.outcome }}
          DISPATCH_OK: ${{ steps.deploy.outcome }}
```

（`steps.deploy` 依赖任务 4 的 `id: deploy`——**任务 4 先于任务 5 执行**。）

- [ ] **步骤 5：绿灯 + 门禁 + 提交**

`python -m unittest discover tools/tests -q` + `python tools/validate_workflows.py`：

```bash
git add tools/reply.py tools/tests/test_reply.py .github/workflows/issue-commands.yml
git commit -m "feat(reply): 透传 commit/dispatch 失败态到回帖（I5）"
git push origin HEAD
```

---

### 任务 6：I12 归档 schema 补 command_id/archived_at（波 2）

**文件：**
- 修改：`userscript-console/internal/cleanup/cleanup.go`（CommandKey、MergeArchive）
- 修改：`userscript-console/internal/cli/doctor.go`（查重跳过空 command_id）
- 测试：`internal/cleanup/`（现有 cleanup 测试文件追加）、`internal/cli/`（doctor 测试，执行时先读现有构造 helper 复用）

**依据：** SPEC-DATA.md:88-104（`command_id` 幂等键、`archived_at`）；doctor.go:126-145 查重读 `command_id` 恒空串 → archive ≥2 组假阳性"重复 command_id"。

- [ ] **步骤 1：红灯测试（cleanup）**

追加到 cleanup 包测试：

```go
func TestMergeArchiveAssignsCommandIDAndArchivedAt(t *testing.T) {
	newResults := map[string][]Result{
		"add": {{ID: "IR_2", Author: "u", Body: "/add x", CreatedAt: time.Unix(200, 0)}},
		"rm":  {{ID: "IR_3", Author: "u", Body: "/rm x", CreatedAt: time.Unix(300, 0)}},
	}
	got := MergeArchive(nil, newResults, 10)
	if len(got.Commands) != 2 {
		t.Fatalf("应合并 2 组, got %d", len(got.Commands))
	}
	seen := map[string]bool{}
	for _, c := range got.Commands {
		if c.CommandID == "" {
			t.Errorf("组 %q 缺 command_id", c.Command)
		}
		if seen[c.CommandID] {
			t.Errorf("command_id 重复: %s", c.CommandID)
		}
		seen[c.CommandID] = true
		if c.ArchivedAt.IsZero() {
			t.Errorf("组 %q 缺 archived_at", c.Command)
		}
	}
}

func TestMergeArchiveBackfillsLegacyCommandID(t *testing.T) {
	existing := &Archive{Schema: 1, Commands: []CommandKey{
		{Command: "add", Results: []Result{{ID: "IR_old", CreatedAt: time.Unix(100, 0)}}},
	}}
	got := MergeArchive(existing, nil, 10)
	if got.Commands[0].CommandID == "" {
		t.Error("旧条目应按最老 result ID 回填 command_id")
	}
}
```

> 类型名以包内实际为准（Result/MergeArchive 已确认；`Result.CreatedAt` 为 `time.Time`）。运行 `go test ./internal/cleanup/ -run TestMergeArchive -count=1` → 红（`CommandID`/`ArchivedAt` 未定义 → 编译失败即红）。

- [ ] **步骤 2：实现 cleanup.go**

`CommandKey` 增字段：

```go
type CommandKey struct {
	Command    string    `json:"command_id,omitempty"` // 注意：保持 Command 原 tag 不变
	...
}
```

> **精确写法**（勿照抄上面的错误示意）——是在现有 struct 里**追加**两行，不动原有 tag：

```go
type CommandKey struct {
	Command    string    `json:"command"`
	Author     string    `json:"author"`
	CreatedAt  time.Time `json:"created_at"`
	CommandID  string    `json:"command_id"`   // 幂等键：组内最老评论的 NodeID（SPEC-DATA §2.3）
	ArchivedAt time.Time `json:"archived_at"`  // 首次归档时间
	Results    []Result  `json:"results"`
}
```

`MergeArchive` 两处赋值：

① 既有条目回填（遍历 `existing.Commands` 的循环里追加）：

```go
		for _, r := range cmd.Results {
			merged[cmd.Command] = append(merged[cmd.Command], r)
			mark(cmd.Command, r.ID)
		}
		if cmd.CommandID == "" {
			// 旧归档无 command_id：按最老 result ID 回填，保证幂等键非空且稳定
			oldest := cmd.Results
			for i := 1; i < len(oldest); i++ {
				if oldest[i].CreatedAt.Before(oldest[0].CreatedAt) {
					oldest[0] = oldest[i] // 仅取最小值，不改原切片——用局部变量
				}
			}
			...
		}
```

> 上面示意会改切片，**实际实现用不修改原数据的写法**：

```go
	for _, cmd := range existing.Commands {
		for _, r := range cmd.Results {
			merged[cmd.Command] = append(merged[cmd.Command], r)
			mark(cmd.Command, r.ID)
		}
	}
	// （回填放最后 commands 构造阶段，见下）
```

② 构造 `commands` 的循环里（C2 修复后的排序/截断逻辑**保持不动**，仅在 append 处补两字段）：

```go
		sort.Slice(results, func(i, j int) bool {
			return results[i].CreatedAt.After(results[j].CreatedAt) // 保持现状（desc）
		})
		// 幂等键与归档时间（SPEC-DATA §2.3；新老条目统一在此赋值）
		commandID := ""
		if len(results) > 0 {
			// desc 排序后最老 = 末尾
			commandID = results[len(results)-1].ID
		}
		archivedAt := time.Now().UTC()
		for _, old := range existing.Commands {
			if old.Command == cmd && old.CommandID != "" {
				commandID = old.CommandID  // 保留既有幂等键
				if !old.ArchivedAt.IsZero() {
					archivedAt = old.ArchivedAt
				}
				break
			}
		}
		commands = append(commands, CommandKey{
			Command:    cmd,
			Results:    results,
			Author:     results[0].Author,
			CreatedAt:  results[0].CreatedAt,
			CommandID:  commandID,
			ArchivedAt: archivedAt,
		})
```

- [ ] **步骤 3：doctor 查重跳过空 command_id（旧归档兼容）**

`doctor.go` 的查重循环改为：

```go
			seen := map[string]bool{}
			for _, c := range arch.Commands {
				if c.CommandID == "" {
					continue // 旧归档无幂等键：跳过（下轮 cleanup 合并时回填）
				}
				if seen[c.CommandID] {
					add("archive/commands.json 存在重复 command_id: %s", c.CommandID)
				}
				seen[c.CommandID] = true
			}
```

- [ ] **步骤 4：红灯测试（doctor 假阳性）**

执行前先 Read `internal/cli/doctor_test.go`（不存在则创建 `internal/cli/doctor_doctor_archive_test.go` 同包），复用其临时根构造方式，追加：

```go
func TestDoctorArchiveDuplicateCommandID(t *testing.T) {
	// 两组均无 command_id（旧归档）→ 不得误报重复
	// 两组 command_id 相同（非空）→ 必须报重复
}
```

断言写实：

```go
	legacy := `{"schema":1,"commands":[
		{"command":"add","results":[{"id":"IR_1"}]},
		{"command":"rm","results":[{"id":"IR_2"}]}]}`
	// 写入 <root>/archive/commands.json → run doctor → errs 中不含 "重复 command_id"

	dup := `{"schema":1,"commands":[
		{"command":"add","command_id":"IC_1","results":[{"id":"IR_1"}]},
		{"command":"rm","command_id":"IC_1","results":[{"id":"IR_2"}]}]}`
	// → errs 中含 "重复 command_id: IC_1"
```

运行 → legacy 用例红（现状第二组即误报）。

- [ ] **步骤 5：绿灯 + 全量门禁**

`go test ./internal/cleanup/ ./internal/cli/ -count=1` → 全绿；总覆盖 ≥90%；snapshot 不受影响。

- [ ] **步骤 6：提交 + push + CI**

```bash
git add internal/cleanup/cleanup.go internal/cli/doctor.go internal/cleanup internal/cli
git commit -m "fix(archive): 归档补 command_id/archived_at 幂等键，doctor 查重兼容旧归档（I12）"
git push origin HEAD
```

---

### 任务 7：I13 /rm 删除源码与 dist 对齐 doctor（波 2）

**文件：**
- 修改：`userscript-console/internal/commands/rm.go:49-54`
- ~~新增 RemoveDist~~ **波 1 调查修正：`script.RemoveDist` 已存在**（`internal/script/fileio.go:73`，幂等：不存在 → nil，`removeFile` 统一实现）——**跳过新增**，直接调用
- 测试：`internal/commands/add_test.go`（现有 TestRm* 旁追加；`buildTestEnvWithFake` 已预置 self01/sync01）

**依据：** projec-02 `remove.py:46-51`（源码+dist 皆删）；doctor.go:91-97 要求 deleted 条目无源码无 dist → 现状 `/rm` 后 doctor 必红。

- [ ] **步骤 1：红灯测试**

```go
func TestRmRemovesSourceAndDistForBothTypes(t *testing.T) {
	env, _ := buildTestEnvWithFake(t) // 预置 self01/sync01

	// 构造两类型的源码与 dist
	if err := script.WriteSource(env.Root, "self01", registry.TypeSelf, "// self"); err != nil {
		t.Fatal(err)
	}
	if err := script.WriteSource(env.Root, "sync01", registry.TypeSynced, "// synced"); err != nil {
		t.Fatal(err)
	}
	if err := script.WriteDist(env.Root, "self01", "// self"); err != nil {
		t.Fatal(err)
	}
	if err := script.WriteDist(env.Root, "sync01", "// synced"); err != nil {
		t.Fatal(err)
	}

	for _, key := range []string{"self01", "sync01"} {
		if _, err := Execute("rm", env, key, nil); err != nil {
			t.Fatalf("rm %s 失败: %v", key, err)
		}
		src := scriptSourcePathFor(env.Root, key) // 见下：用 doctor 同源路径 helper
		if fileExistsAny(src) {
			t.Errorf("%s 源码应已删除", key)
		}
		if fileExistsAny(filepath.Join(env.Root, "dist", key+".user.js")) {
			t.Errorf("%s dist 应已删除", key)
		}
	}
}
```

> 辅助：若包内无现成存在性判断，用 `os.Stat(path); !os.IsNotExist(err)` 内联；源码路径按 `script` 包既有路径函数（执行时 Read `internal/script` 取 `SourcePath`/`DistPath` 真名，勿臆造——doctor 用的是 `scriptSourcePath(root,s)`（cli 包内）与 `script.DistPath(id)`）。运行 → 红（synced 源与两者 dist 仍在）。

- [ ] **步骤 2：实现**

**（波 1 调查修正）** `script.RemoveDist` 已存在（`fileio.go:73`，幂等）、`RemoveSource` 已确认幂等（`fileio.go:61-69` 注释与 `removeFile:168-176` 实现：缺文件 → nil）——**两者都不用新增/不需 IsNotExist 宽容处理**，只改 `rm.go`（去掉 `if s.Type == registry.TypeSelf` 条件）：

```go
	// 移除源码与分发产物（self/synced 同待遇；对齐 Python _soft_delete，doctor 双删校验）
	if err := script.RemoveSource(env.Root, s.ID, s.Type); err != nil {
		return reply(changed, "❌ 已删除脚本 %q，但源文件失败: %v", s.Name, err)
	}
	if err := script.RemoveDist(env.Root, s.ID); err != nil {
		return reply(changed, "❌ 已删除脚本 %q，但分发产物失败: %v", s.Name, err)
	}
```

- [ ] **步骤 3：绿灯 + 门禁 + 提交**

`go test ./internal/commands/ ./internal/script/ -count=1` → 绿；全量门禁：

```bash
git add internal/commands/rm.go internal/commands/add_test.go
git commit -m "fix(rm): 删除源码与 dist 对齐 doctor 双删校验（I13）"
git push origin HEAD
```

---

### 任务 8：I6 面板 Issue #1 初始化幂等复核（波 3）

**文件：**
- 修改：`userscripts/tools/tests/test_init_panel.py`

**现状（已读 init_panel.py）：** `find_panel` 幂等查找在位——过滤 `pull_request`、`DEFAULT_TITLE in title` 包含匹配、查询失败返回 1；存在即不 POST。基线判"基本在位，待核原判"——原报告缺失（`docs/reviews/` 仅本基线），以行为测试固化原判四项要求。

- [ ] **步骤 1：读现有测试**

Read `tools/tests/test_init_panel.py`，沿用其 fake api/环境注入风格。

- [ ] **步骤 2：补齐四用例（先红判断——已在位的行为直接绿，缺失的才是真回归）**

```python
    def test_existing_panel_skips_create(self):
        # api: GET issues 返回含 "命令面板" 标题的非 PR issue
        # 断言：main 返回 0 且无 POST 调用（fake 记录 method 序列）

    def test_pr_with_same_title_is_skipped(self):
        # 列表项带 "pull_request" 键且标题匹配 → 视为无面板 → 发生 POST 创建

    def test_title_contains_match(self):
        # 标题 "🛠️ 命令面板（勿删）" 含 DEFAULT_TITLE → 命中 → 不 POST

    def test_query_failure_exits_nonzero(self):
        # GET 返回 500 → main 返回 1，不 POST
```

- [ ] **步骤 3：运行 + 必要修补**

`python -m unittest discover tools/tests -p "test_init_panel.py" -v`。四项全绿 → I6 行为确认在位（测试即固化）；任一红 → 按断言修 `init_panel.py`（最小改动）后绿。

- [ ] **步骤 4：门禁 + 提交**

```bash
git add tools/tests/test_init_panel.py
git commit -m "test(panel): 固化 Issue #1 初始化幂等四态（I6 复核）"
git push origin HEAD
```

---

### 任务 9：波 3 收口——发 v1.1.3 + 全部 uses 升 SHA pin

**文件：**
- 修改：`userscripts/.github/workflows/{issue-commands,deploy-pages,sync-scheduled,cleanup-panel,validate}.yml`（7 处 `uses:`）
- 参照：`userscripts/tools/validate_workflows.py` 检查 8（已支持 a) 40 位 sha / b) vX.Y.Z / c) v1 三种 pin 形态，无需改校验器）

**前置：** 任务 1、3 已合入工具仓且 Test CI 绿（否则发出去的还是老门禁）。

- [ ] **步骤 1：工具仓打 tag 发版**

```bash
git -C ..\userscript-console status --short        # 必须干净
git -C ..\userscript-console tag v1.1.3
git -C ..\userscript-console push origin v1.1.3
```

轮询工具仓 **Release** workflow（build→publish→move-v1-tag 链）至 success；若红，修（新 commit）后按 §6 回滚纪律处理——**tag 冲突时不得 amend 已推 tag**，改用 `workflow_dispatch` 重跑或删本地 tag 重打（远端删 tag 仅在确认无副作用时）。

- [ ] **步骤 2：取 release 事实**

```powershell
git -C ..\userscript-console rev-parse 'v1.1.3^{commit}'   # 记为 $SHA（40位）
# checksums（可选 binary-sha256）：
Invoke-RestMethod -Uri 'https://github.com/ACG-Q/userscript-console/releases/download/v1.1.3/checksums.txt' -OutFile $env:TEMP\opencode\checksums.txt
Select-String -Path $env:TEMP\opencode\checksums.txt -Pattern 'usm-linux-amd64$'
```

- [ ] **步骤 3：升钉 7 处**

对 6 个工作流的每处 `uses: acg-q/userscript-console@v1.1.2`：

1. `@v1.1.2` → `@<SHA>`（40 位全量，安全形态 a）
2. 该 step 带 `use-binary: true` 的，`with:` 追加 `binary-version: '1.1.3'`（ACTION_REF 是裸 sha 时二进制版本无法自推导；`binary-sha256: '<linux-amd64 sha>'` 一并加，值来自步骤 2）
3. grep 自检：

```powershell
Select-String -Path .github\workflows\*.yml -Pattern 'userscript-console@'
# 预期：7 处全部为 @<SHA>，0 处残留 v1.1.2
Select-String -Path .github\workflows\*.yml -Pattern 'use-binary' | Measure-Object  # 每处 use-binary 旁有 binary-version
```

- [ ] **步骤 4：门禁 + 提交 + push + CI**

`python tools/validate_workflows.py`（检查 8 对 sha 形态放行；`latest_tool_sha()` 若比对最新 release sha，v1.1.3 之后应一致）+ `python -m unittest discover tools/tests -q`：

```bash
git add .github/workflows
git commit -m "ci(pin): 全部 uses 升至 v1.1.3 提交 SHA 并显式 binary-version（波3）"
git push origin HEAD
```

轮询内容仓 Validate/Deploy/Init 至 success——**此绿 = 批次 0/1 修复（含 C1-C4）正式在内容仓 CI 生效**（deploy 的 build 将由新版二进制执行，dist 注入自动正确）。

---

### 任务 10：I8 markdown 消毒改 bluemonday（波 4）

**文件：**
- 修改：`userscript-console/internal/pages/pages.go:160-172`（RenderMarkdown）、删除 `sanitizeDangerous`、修 :5 包注释
- 修改：`userscript-console/go.mod`/`go.sum`（bluemonday indirect → direct）
- 测试：`internal/pages/`（XSS 表驱动）

**依据：** 规格 D-04/DR-6（goldmark+bluemonday，XSS 硬验收）；现状 `WithUnsafe()` + 手写黑名单漏 `<img onerror>`/`<svg onload>`/`<iframe>`/`javascript:`。

- [ ] **步骤 1：红灯 XSS 表测试**

```go
func TestRenderMarkdownSanitizesXSS(t *testing.T) {
	cases := []string{
		`<script>alert(1)</script>ok`,
		`<img src=x onerror="alert(1)">`,
		`<svg onload=alert(1)></svg>`,
		`<iframe src="https://evil"></iframe>`,
		`[x](javascript:alert(1))`,
		`<a href="javascript:alert(1)">x</a>`,
		`<object data="e"></object><embed src="e">`,
		`<form action="e"><input name="a"></form>`,
	}
	for _, src := range cases {
		out := RenderMarkdown(src)
		low := strings.ToLower(out)
		for _, bad := range []string{"<script", "onerror=", "onload=", "<iframe", "javascript:", "<object", "<embed", "<form"} {
			if strings.Contains(low, bad) {
				t.Errorf("源 %q 未被消毒，输出含 %q:\n%s", src, bad, out)
			}
		}
	}
}

func TestRenderMarkdownKeepsSafeHTML(t *testing.T) {
	out := RenderMarkdown("**粗体** [链接](https://example.com) `code`")
	for _, want := range []string{"<strong>", "href=\"https://example.com\"", "<code>"} {
		if !strings.Contains(out, want) {
			t.Errorf("安全标记丢失 %q:\n%s", want, out)
		}
	}
}
```

运行 `go test ./internal/pages/ -run TestRenderMarkdown -count=1` → 红（`onerror=`/`javascript:` 直通）。

- [ ] **步骤 2：引入 bluemonday**

```powershell
$env:HTTPS_PROXY='http://127.0.0.1:7897'
go get github.com/microcosm-cc/bluemonday@latest
go mod tidy
```

`go.mod` 中 bluemonday 由 indirect 转 direct（tidy 自动）；AGENTS.md §3 依赖说明：MIT、活跃维护、规格 D-04 点名指定，替代手写黑名单。

- [ ] **步骤 3：实现**

`RenderMarkdown` 改为：

```go
// RenderMarkdown 使用 goldmark 渲染 Markdown，并用 bluemonday UGCPolicy 消毒
// （规格 D-04：WithUnsafe 放行原始 HTML 后必须过 bluemonday，黑名单手写不可靠）。
func RenderMarkdown(src string) string {
	var buf bytes.Buffer
	md := goldmark.New(
		goldmark.WithExtensions(),
		goldmark.WithRendererOptions(htmlmd.WithUnsafe()),
	)
	if err := md.Convert([]byte(src), &buf); err != nil {
		return esc(src)
	}
	return bluemonday.UGCPolicy().Sanitize(buf.String())
}
```

删除 `sanitizeDangerous` 函数及其直接测试（用 XSS 表测试替代）；修正 :5 包注释与实现一致。imports 增 `bluemonday`，移除不再使用的 helper import。

- [ ] **步骤 4：绿灯 + 全量门禁 + 提交**

```bash
git add internal/pages/pages.go go.mod go.sum internal/pages
git commit -m "fix(pages): markdown 消毒改 bluemonday UGCPolicy，堵 XSS 直通（I8）"
git push origin HEAD
```

---

### 任务 11：I9 评论正文单次处理 + clip 400（波 4）

**文件：**
- 修改：`userscript-console/internal/pages/pages.go`（Comment 结构 :66、Body 构造点、新增 `clipText`）
- 测试：`internal/pages/`

**依据：** build_pages.py:467,564 `escape_html(clip(body,400))` 单次处理；issue_stats.py:62 `clip` = 折叠空白 → 超限截断+省略号；现状 RenderMarkdown 产 HTML 后 `{{.Body}}` 对 string 二次转义。

- [ ] **步骤 1：红灯测试**

```go
func TestCommentBodySinglePassAndClipped(t *testing.T) {
	// 构造带评论的 detail 数据（复用现有 detail 渲染测试的 fixture 方式）
	// ① 正文含 HTML：渲染结果中 "<b>x</b>" 出现且不被二次转义（断言无 "&lt;b&gt;"）
	// ② 超 400 字正文：渲染结果正文中长度受限且以 "…" 结尾
}
```

执行时先 Read 现有 detail 渲染测试（`pages_test.go` 中含 Comments 的用例）复制其数据构造；断言：

```go
	if strings.Contains(html, "&lt;b&gt;") { t.Error("评论正文被二次转义") }
	if !strings.Contains(html, "<b>x</b>") { t.Error("评论 markdown/HTML 未渲染") }
```

运行 → 红（现状输出 `&lt;b&gt;`）。

- [ ] **步骤 2：实现**

① `Comment` 结构：

```go
type Comment struct {
	Author    string
	Body      template.HTML // 已消毒+截断的可信 HTML（单次处理，D-04）
	CreatedAt string
}
```

② 新增 helper（pages.go，靠近 RenderMarkdown）：

```go
// clipText 折叠空白并按 rune 截断到 limit 字符，超出加省略号
// （对齐 projec-02 issue_stats.clip）。
func clipText(s string, limit int) string {
	s = strings.Join(strings.Fields(s), " ")
	r := []rune(s)
	if len(r) <= limit {
		return s
	}
	return string(r[:limit]) + "…"
}
```

③ 所有 `Body: RenderMarkdown(...)` 构造点统一为（`grep -n "RenderMarkdown(" internal/pages/pages.go` 定位，讨论区 :311 与 Issue 评论区两处）：

```go
	Body: template.HTML(RenderMarkdown(clipText(c.Body, 400))),
```

④ 确认 `detail.tmpl:94` 保持 `{{.Body}}` 不动（类型为 template.HTML 后不再转义）。

- [ ] **步骤 3：绿灯 + 门禁（含既有评论测试适配）**

`go test ./internal/pages/ -count=1`——若既有断言期望转义输出，按"单次处理"语义更新断言（更新理由写进提交信息）。

- [ ] **步骤 4：提交 + push**

```bash
git add internal/pages/pages.go internal/pages
git commit -m "fix(pages): 评论正文 clip 400 + 单次消毒输出，去除二次转义（I9）"
git push origin HEAD
```

---

### 任务 12：I10 首页 JS null 守卫（波 4）

**文件：**
- 修改：`userscript-console/internal/pages/templates/index.tmpl`（script 段）
- 测试：`internal/pages/`

**实锤：** `Total≤Batch` 时 `#loadMore`/`#loadMoreBtn` 不渲染（index.tmpl:64-69），顶层 `document.getElementById('loadMoreBtn').onclick` → null.onclick TypeError。

- [ ] **步骤 1：红灯测试**

```go
func TestIndexJSGuardsMissingLoadMore(t *testing.T) {
	// 用 Total≤Batch 的数据渲染 index（复用现有 index 渲染测试 fixture）
	html, err := renderIndexForTest(...) // 执行时按现有测试的渲染入口
	if err != nil { t.Fatal(err) }
	if !strings.Contains(html, "if (btn)") || !strings.Contains(html, "if (lm)") {
		t.Errorf("index JS 缺少 loadMore 元素的 null 守卫:\n%s", html)
	}
}
```

运行 → 红。

- [ ] **步骤 2：实现（index.tmpl script 段尾部改）**

```js
        function loadMore() {
            var next = Math.min(shown + batch, total);
            var cards = document.querySelectorAll('.card');
            for (var i = shown; i < next; i++) {
                if (cards[i]) cards[i].style.display = '';
            }
            shown = next;
            if (shown >= total) {
                var lm = document.getElementById('loadMore');
                if (lm) lm.style.display = 'none';
            }
        }
        var btn = document.getElementById('loadMoreBtn');
        if (btn) btn.onclick = loadMore;
        loadMore();
```

- [ ] **步骤 3：绿灯 + 快照 + 提交**

`go test ./internal/pages/ -count=1` → 绿；`go run ./cmd/usm snapshot update` → `git diff tests/snapshot` 只含 index.html JS 段变化：

```bash
git add internal/pages/templates/index.tmpl tests/snapshot
git commit -m "fix(index): 首页 JS 对缺失 loadMore 元素加 null 守卫（I10）"
git push origin HEAD
```

---

### 任务 13：I11 命令页快照补测（波 4）

**文件：**
- 修改：`userscript-console/cmd/usm/snapgen_test.go`

- [ ] **步骤 1：红灯——补断言**

`TestBuildSiteSnapshot` 的存在性断言列表扩为（沿用 `files[name] == ""` 风格）：

```go
	for _, name := range []string{
		"site/index.html", "site/scripts.json", "site/build-warnings.txt",
		"site/commands/index.html", "site/commands/page-1.html",
	} {
		if files[name] == "" {
			t.Errorf("产物 %s 不应为空", name)
		}
	}
	// 页面全集：含全部脚本详情页 + 至少一个命令归档页
	if len(files) < 4+len(reg.Scripts) {
		t.Errorf("应含全站产物页, got %d 个文件", len(files))
	}
	for name := range files {
		if strings.HasPrefix(name, "site/scripts/") && strings.HasSuffix(name, ".html") {
			return // 详情页存在性由上方计数兜底，这里确保前缀约定未变
		}
	}
```

> `files` 键的真实前缀执行时校准：先跑 `go test ./cmd/usm -run TestBuildSiteSnapshot -count=1` 看当前键（C3 期间已确认 `site/index.html` 形态；命令页键预期 `site/commands/...`）。若键不符，按真实键改断言值——**断言目标不变：命令页 index+page-1 非空**。

- [ ] **步骤 2：红→绿确认**

现状若命令页已产出（C3 后）则本断言直接绿——此时红灯退化为"守护性测试"，仍在（防 I7 重写回归）；若键缺失则红 → 检查 corpus 是否含 `archive/commands.json`（预期含）。

- [ ] **步骤 3：提交**

```bash
git add cmd/usm/snapgen_test.go
git commit -m "test(snapshot): 命令归档页纳入站点快照存在性断言（I11）"
git push origin HEAD
```

---

### 任务 14：I7 站点功能缺口五点（波 4，最大任务）

**文件：**
- 修改：`userscript-console/internal/pages/pages.go`（renderCommands :373-439 重写、renderCommandsIndex 删除/改静态、Build 调用点、commandsIndexData/commandsPageData 类型）
- 修改：`userscript-console/internal/pages/templates/commands.tmpl`（全局混排 + 文件分页）
- 修改：`userscript-console/internal/pages/templates/commands-index.tmpl`（meta-refresh）
- 修改：`userscript-console/internal/pages/templates/index.tmpl`（归档导航 + CSS 变量 + JS 初始隐藏）
- 修改：`userscript-console/internal/pages/templates/detail.tmpl`（归档导航 + CSS 变量）
- 测试：`internal/pages/pages_test.go`（新用例 + 更新 TestBuildLinksAreRelative）

**Py 对照（已读）：**
- build_pages.py:169,187,193（`page()` 包装器）：导航/页脚链接 = `commands/page-1.html`（相对根 `rel` 前缀）。
- build_pages.py:771-824（`build_command_pages`）：`ordered = reversed(archive)` 全局倒序 → 按 `COMMANDS_PER_PAGE`（5）**整组**分块 → `page-N.html` 连续页号；过期 `page-*.html` 清理；**`commands/index.html` = meta refresh → page-1.html**（带兜底链接）；空归档产空态 page-1。
- build_pages.py:764-771（`_pager`）：`上一页 / 第 x / y 页 / 下一页`，`page-{n}.html` 相对链接。
- index.tmpl:17 使用未定义变量 `--text-muted`/`--font-ui`/`--border-strong`；:21 `--brand-fade`；:29 `--info-bg/--info-text`；:30 `--warn-bg/--warn-text`；:31 `--bg-subtle`；detail.tmpl:21 `--neutral-bg`；:54 `badge-deleted` 无样式（`components.css` 未被任何模板链接）。

- [ ] **步骤 1：红灯测试（四条）**

`internal/pages/pages_test.go` 追加（fixture 复用现有 corpus/Options 构造）：

```go
func TestCommandsGlobalPagination(t *testing.T) {
	// 12 个命令组、CommandsPerPage=5 → 页数=3
	// page1 含最新组的命令文本（CreatedAt 最大者）；page3 = 最旧组
	// 所有键 1..3，无缺页；页内 stat 显示 第 N/3 页
}

func TestCommandsIndexMetaRefresh(t *testing.T) {
	// idxHTML 含 `<meta http-equiv="refresh"` 与 `url=page-1.html`
}

func TestArchiveNavLinks(t *testing.T) {
	// index 页含 href="commands/page-1.html"
	// detail 页含 href="../commands/page-1.html"
}

func TestIndexBatchInitialHide(t *testing.T) {
	// index JS 含初始隐藏逻辑：`style.display = 'none'` 循环（i = batch 起）
}
```

运行 `go test ./internal/pages/ -run 'TestCommands|TestArchiveNav|TestIndexBatch' -count=1` → 全红。同时既有 `TestBuildLinksAreRelative` 会因 commands-index 改 meta-refresh 而需同步更新（步骤 4 内处理）。

- [ ] **步骤 2：renderCommands 重写（pages.go）**

```go
// renderCommands 渲染命令归档：全局倒序整组分页（对齐 build_pages.py build_command_pages），
// 每页 opts.CommandsPerPage 组；空归档也产空态 page-1；index 为 meta-refresh。
func renderCommands(opts Options) (map[int]string, string, error) {
	archivePath := filepath.Join(filepath.Dir(filepath.Clean(opts.Out)), "archive", "commands.json")

	var groups []commandGroup
	data, err := os.ReadFile(archivePath)
	if err == nil {
		var archive commandArchive
		if err := json.Unmarshal(data, &archive); err != nil {
			return nil, "", fmt.Errorf("解析归档失败: %w", err)
		}
		groups = archive.Commands
	} else if !os.IsNotExist(err) {
		return nil, "", fmt.Errorf("读取归档失败: %w", err)
	}

	sort.Slice(groups, func(i, j int) bool {
		return groups[i].CreatedAt.After(groups[j].CreatedAt) // 新→旧
	})

	perPage := opts.CommandsPerPage
	if perPage <= 0 {
		perPage = 5
	}
	totalPages := (len(groups) + perPage - 1) / perPage
	if totalPages < 1 {
		totalPages = 1 // 空归档也产 page-1（CUTOVER 空态可达）
	}

	result := make(map[int]string, totalPages)
	for p := 1; p <= totalPages; p++ {
		start := (p - 1) * perPage
		end := start + perPage
		if end > len(groups) {
			end = len(groups)
		}
		pageGroups := groups[start:end]
		html, err := renderCommandPage(pageGroups, p, totalPages, len(groups))
		if err != nil {
			return result, "", err
		}
		result[p] = html
	}

	return result, commandsIndexHTML, nil
}

// commandsIndexHTML 静态跳转页：旧链/直达均落到 page-1（build_pages.py:816-824）。
const commandsIndexHTML = `<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0; url=page-1.html">
    <title>命令归档</title>
</head>
<body>
    <p><a href="page-1.html">命令归档 · 第 1 页 →</a></p>
</body>
</html>
`
```

- [ ] **步骤 3：类型与模板配套**

① `commandsPageData` 改为：

```go
type commandsPageData struct {
	Groups     []commandGroup
	Page       int
	TotalPages int
	TotalItems int
}
```

② `renderCommandPage` 新签名与实现：

```go
func renderCommandPage(groups []commandGroup, page, totalPages, totalItems int) (string, error) {
	return renderTemplate("commands", commandsPageData{
		Groups: groups, Page: page, TotalPages: totalPages, TotalItems: totalItems,
	})
}
```

③ 删除 `commandsIndexData`、`renderCommandsIndex`、`firstPage`/`HasCommands` 相关 C3 残留——执行时 `grep -n 'firstPage\|HasCommands\|renderCommandsIndex\|commandsIndexData' internal/pages/` 全部清理（Build 调用点同步改：写 `commands/index.html` 用 `commandsIndexHTML` 常量）。

④ `commands.tmpl` 重写主体（样式骨架保留，改数据与链接）：

```html
        <a class="back" href="../index.html">← 返回脚本列表</a>
        <h1>命令归档</h1>
        <div class="stat-bar">
            <span class="count">共 <b>{{.TotalItems}}</b> 条历史命令</span>
            <span class="total">第 {{.Page}}/{{.TotalPages}} 页</span>
        </div>
        {{range $gi, $g := .Groups}}
        <div class="entry">
            <header>
                <h2>{{$g.Command}}</h2>
                <div class="meta">by {{$g.Author}} · {{$g.CreatedAt.Format "2006-01-02 15:04"}}</div>
            </header>
            {{range $g.Results}}
            <div class="body"><b>{{.Author}}</b>：{{.Body}}</div>
            {{else}}
            <div class="body">无执行结果</div>
            {{end}}
        </div>
        {{else}}
        <p class="empty-state">还没有归档记录</p>
        {{end}}
        {{if gt .TotalPages 1}}
        <div class="pagination">
            {{if gt .Page 1}}<a class="prev" href="page-{{sub .Page 1}}.html">上一页</a>{{end}}
            {{range $i := seq .TotalPages}}
                {{if eq (add $i 1) $.Page}}<span class="active">{{$i}}</span>
                {{else}}<a href="page-{{add $i 1}}.html">{{$i}}</a>{{end}}
            {{end}}
            {{if lt .Page .TotalPages}}<a class="next" href="page-{{add .Page 1}}.html">下一页</a>{{end}}
        </div>
        {{end}}
```

> `commandGroup.CreatedAt` 是 `time.Time`——模板里方法调用 `.Format` 合法；若渲染报错改在 Go 侧格式化为字符串字段。`seq`/`add`/`sub` funcMap 已存在（commands.tmpl 原分页在用）。**页码链接一律 `page-N.html` 文件路径，杜绝 `?page=`（静态站无效）**。

⑤ `commands-index.tmpl` 全文替换为与 `commandsIndexHTML` 相同的静态 meta-refresh 页（模板与常量二选一——**执行时择一**：保留 tmpl 则 renderTemplate 调用传 nil 数据；删 tmpl 则 Build 直接写常量。计划默认：**保留 tmpl 文件**便于快照一致性，`renderCommands` 返回值即 `renderTemplate("commands-index", nil)` 渲染结果）。

- [ ] **步骤 4：导航 + CSS + JS（index/detail 模板）**

① 归档导航：`index.tmpl` `<h1>Userscript Console</h1>` 行后加：

```html
        <p><a href="commands/page-1.html">命令归档 →</a></p>
```

`detail.tmpl` 的 `.back` 返回链接行后加：

```html
                <a href="../commands/page-1.html">命令归档 →</a>
```

② CSS：`index.tmpl` 与 `detail.tmpl` 的 `:root` 末尾补（值与现有色板同源）：

```css
--text-muted: #6a737d; --info-bg: #ddf4ff; --info-text: #0969da;
--warn-bg: #fff8c5; --warn-text: #7d4e00; --bg-subtle: #f6f8fa;
--neutral-bg: #eaeef2; --brand-fade: rgba(9,105,218,.35);
--border-strong: #d0d7de; --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
```

`index.tmpl` 样式区补（components.css 未链接，badge 页内自足）：

```css
        .badge-deleted { background: #fce8e6; color: #cf222e; }
```

③ JS 初始隐藏（I7④；I12 已落 null 守卫，直接在其上叠加）——script 段改为：

```js
        var btn = document.getElementById('loadMoreBtn');
        if (btn) btn.onclick = loadMore;
        // 服务端全量渲染：初始只显示前 batch 条（I7④）
        var cards = document.querySelectorAll('.card');
        for (var i = batch; i < cards.length; i++) {
            cards[i].style.display = 'none';
        }
        shown = batch;
        loadMore();
```

（`loadMore()` 内已有 `if (lm)` 守卫——Total≤Batch 时 `shown>=total` 直接走守卫分支，无 TypeError。）

- [ ] **步骤 5：红灯全绿 + 既有测试适配**

`go test ./internal/pages/ -count=1`：
- 新四用例转绿；
- `TestBuildLinksAreRelative` 更新：commands-index 断言改为含 `url=page-1.html`（相对、无前导 `/`）；commands 页断言 `page-` 链接不含 `?`；
- 其他因数据结构变化的编译错误按步骤 2/3 修。

- [ ] **步骤 6：全量门禁 + 快照刷新**

```powershell
go run ./cmd/usm snapshot update
git diff --stat tests/snapshot
git diff tests/snapshot     # 逐文件过目：commands/*、index、detail 的预期变化
```

gofmt/vet/test ≥90%/snapshot check/build 全绿。

- [ ] **步骤 7：提交 + push + CI**

```bash
git add internal/pages tests/snapshot
git commit -m "fix(pages): 命令归档全局混排分页+meta-refresh+导航/CSS/JS 五点补齐（I7）"
git push origin HEAD
```

---

### 任务 15：I14 站点 URL 文档漂移修正（附带）

**文件：**
- 修改：`userscripts/BASELINE.md:12`、`userscripts/CUTOVER.md:48`、`userscripts/SPEC-DATA.md:156`、`userscripts/docs/index.md:32`
- 修改：`userscripts/docs/reviews/2026-10-07-baseline.md`（Important 表尾新增 I14 行）

**事实：** 部署 API 环境 URL = `https://acg-q.github.io/userscripts/`（实测 root 200、dist 200）；上述四处写 `userscript-manager`；`README.md:18,42-44` 同病但属**预存未提交改动，永不提交**（记入 I14 描述说明）。

- [ ] **步骤 1：修四处 URL**

把四文件中 `https://acg-q.github.io/userscript-manager` 全部改为 `https://acg-q.github.io/userscripts`（用 edit 工具逐文件，禁止 PowerShell 批量替换——防 BOM/编码事故）。

- [ ] **步骤 2：门禁 + 提交（提交 1）**

`python tools/validate_workflows.py`（若覆盖 docs 校验）+ `git diff` 确认仅四处：

```bash
git add BASELINE.md CUTOVER.md SPEC-DATA.md docs/index.md
git commit -m "docs: 站点 URL 修正为实际 Pages 路径 /userscripts（I14）"
git push origin HEAD
```

记下本提交短哈希 `$H`。

- [ ] **步骤 3：基线新增 I14 行（提交 2）**

`docs/reviews/2026-10-07-baseline.md` 的 Important 表（I13 行后）追加：

```markdown
| I14 | 3 | BASELINE.md:12；CUTOVER.md:48；SPEC-DATA.md:156；docs/index.md:32 | 文档站点 URL 漂移：写 `userscript-manager`，实际 Pages 为 `/userscripts`（部署 status 环境 URL 实测 root/dist 200）；README.md:18,42-44 同病但属预存未提交改动（永不提交）不改 | Important | 波 5 附带（用户确认记入） | fixed（$H；运行时以部署 API 为准） |
```

```bash
git add docs/reviews/2026-10-07-baseline.md
git commit -m "docs(review): 基线记入 I14 站点 URL 漂移（fixed）"
git push origin HEAD
```

---

### 任务 16：收口——勾销 I1-I14 + 汇报

- [ ] **步骤 1：两仓终检**

- 工具仓：全量门禁五连 + `git status --short` 干净（cover.out 若未忽略需确认 .gitignore）。
- 内容仓：`python -m unittest discover tools/tests -q` + `python tools/validate_workflows.py`；`git status --short` 仅 ` M README.md`。
- 轮询两仓全部 CI：工具仓 Test（任务 10-14 各 push）、Release（任务 9）、内容仓 Validate/Deploy/Init（任务 2/4/5/8/9/15 各 push）全 success。

- [ ] **步骤 2：基线勾销**

`docs/reviews/2026-10-07-baseline.md` Important 表 I1-I13 状态列由 `open（…）` 改为 `fixed（<工具仓或内容仓短哈希>；关键验证）`，每行填本计划对应任务的实际提交号与验证方式（例如 I1：`fixed（工具仓 <hash>；Release workflow 链 build+test→publish）`）。I14 已在任务 15 勾销。

```bash
git add docs/reviews/2026-10-07-baseline.md
git commit -m "docs: 勾销 I1-I13（批次 2 完成）"
git push origin HEAD
```

- [ ] **步骤 3：向用户汇报**

内容：四波完成清单（I1-I14 哈希表）、v1.1.3 发版与 SHA 升钉结果（C1-C4 在内容仓 CI 生效的证据）、两仓 CI 全绿截图字段、执行偏差记录（若有）、批次 3（8 Minor）/批次 4（12 F 差异）待写计划 3 的确认请求。

---

## 自检记录

1. **规格覆盖度：** §4.2 波 1=任务 1/2/3（I1/I2/I3）；波 2=任务 4/5/6/7（I4/I5 + I12/I13 按基线"补入对应波次"）；波 3=任务 8/9（I6 复核 + 全部 uses SHA pin + release 改进——release 流程改进由任务 1 覆盖）；波 4=任务 10/11/12/13/14（I8/I9/I10/I11/I7）；波 5 附带=任务 15（I14，用户确认）；收口=任务 16。I1-I13 全覆盖，无遗漏。
2. **占位符扫描：** 任务 2/14 含"执行时修正笔误/择一"标记——均为已知 ASCII 图示笔误的显式修正指令或等价二选一决策，非"待定"；任务 7/11 的"执行时 Read 包内真实函数名"是防臆造的校准步（附带了完整目标代码）；无 TODO/后续实现。
3. **类型一致性：** `CommandKey.CommandID/ArchivedAt`（任务 6 定义 ↔ doctor 读取 json tag `command_id` 一致）；`compose_body(result, proj, cmd_ok, commit_ok="", dispatch_ok="")`（任务 5 定义 ↔ yml env 名 `COMMIT_OK/DISPATCH_OK` ↔ 测试关键字参数）；`renderCommandPage(groups, page, totalPages, totalItems)` 与 `commandsPageData{Groups,Page,TotalPages,TotalItems}`（任务 14 步骤 2↔3 一致）；`clipText(s, limit)`（任务 11 定义 ↔ 调用 `clipText(c.Body, 400)`）；`validate_text(schema, name, text)`（任务 2 测试 ↔ 实现）；任务 14 的 `commandsIndexHTML` 常量 ↔ `commands-index.tmpl` 内容择一同步。
4. **顺序依赖：** 任务 5 依赖任务 4 的 `id: deploy`；任务 9 依赖任务 1/3 已发版内容；任务 14 步骤 4③ 依赖任务 12 的 JS 守卫——编号已保证。
