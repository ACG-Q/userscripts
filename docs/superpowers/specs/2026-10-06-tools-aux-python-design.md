# 设计 · userscripts 辅助功能 Python 化与 workflow 去 shell

> 日期：2026-10-06
> 范围：`userscripts` 内容仓（`ACG-Q/userscripts`）
> 前置：`acg-q/userscript-console@v1.1.0` Action 已承担核心功能（run-command / project / build / cleanup / doctor），本设计不改工具仓接口。

---

## 1. 背景与目标

6 条 workflow 里共有 13 处内联 `run: |` bash 逻辑（权限门禁、git 提交、派发部署、回帖、`_site` 组装、清理输入归一、面板初始化、registry 校验等）。问题：

- 逻辑埋在 yml 字符串里，本地无法运行、无法单元测试
- shell 纪律（`set -euo pipefail`、heredoc、引号转义）靠人肉维护，易漂移

**目标**：
1. 核心功能继续由 userscript-console Action 承担；**辅助功能全部下沉到本仓 `tools/*.py`**
2. yml 中**不残留任何内联 shell 逻辑**，`run:` 步骤只允许一行式 `python tools/xxx.py ...`

## 2. 决策记录

| # | 决策 | 选项 |
|---|---|---|
| D1 | 允许 `run: python tools/xxx.py` 一行调用（`run:` 步骤存在，但无内联 bash 逻辑） | 否决"全 `uses:`"（需把辅助功能包装成 Action，成本高） |
| D2 | **统一先 checkout 再跑 Python**，含权限门禁与面板初始化两处（接受"未授权评论也 checkout"的微小代价；`init-command-panel.yml` 补 `contents: read`） | 否决"保留 shell 例外" |
| D3 | 脚本**本地也能跑 + 配单元测试**：env 与 argparse 双通道，副作用收进可注入边界 | 否决"CI 专用/不写测试" |
| D4 | 方案 A 全量替换 13 处；否决 C（统一入口 + Makefile，YAGNI） | 见当时方案对比 |

## 3. 架构

```
.github/workflows/*.yml   薄壳：on:/permissions:/concurrency、if 门禁、一行式 run
tools/*.py                辅助功能：CI 与本地双环境可跑
acg-q/userscript-console  核心功能：不动
```

### 3.1 组件清单

| 脚本 | 职责 | 关键接口 |
|---|---|---|
| `tools/gate.py` | 评论者==拥有者判定；未授权则调 API 删评论 | env `COMMENT_USER`/`REPO_OWNER`；写 `GITHUB_OUTPUT.authorized`；HTTP DELETE 用 `urllib`（不依赖 `gh` CLI） |
| `tools/commit.py` | 白名单 git 提交（3 条 workflow 复用） | `--allowlist <paths...> --message <msg>`；输出 `committed=true/false`；无实际变更退出 0 且 `committed=false` |
| `tools/dispatch_deploy.py` | 显式派发 `deploy-pages.yml`（3 处复用） | `--workflow <file>`；派发失败打 `::warning::` 后退出 0（**不阻断**，保持现行为） |
| `tools/reply.py` | 组装执行结果回帖（含失败态前缀、投影追加） | env `RESULT`/`PROJ`/`CMD_OK`/`ISSUE_NUMBER`；行为对齐现 shell 逐字语义 |
| `tools/assemble_site.py` | `dist/*` 按 `*.user.js` 拆入 `_site/` | `--root <dir>`；`dist/` 缺失 → 报错退出非 0 |
| `tools/cleanup_config.py` | 归一 apply/keep（dispatch 用 input，schedule 固定 `apply=true keep=10`） | env `EVENT`/`DISPATCH_APPLY`/`KEEP`；写 `GITHUB_OUTPUT.apply/keep` |
| `tools/init_panel.py` | 面板 Issue 存在性检查 + 创建 | `--title/--body/--label`；存在则跳过（退出 0） |
| `tools/validate_registry.py` | registry 结构校验（替内联 `python -c`） | 非 0 退出 = CI 红 |
| `tools/validate_workflows.py` | （既有）workflow 纪律校验 | 规则随本次重构更新（§6） |

**通用约定**：
- 除 `validate_workflows.py` 需要既有依赖 `PyYAML` 外，其余脚本**纯标准库**——因此 workflow 里不需要任何 `pip install` 步骤，不新增依赖
- env 读默认值、argparse 可覆盖 → 本地 `python tools/xxx.py --help` 直接可用
- 退出码：`0` 成功/业务性短路，`1` 运行或校验失败，`2` 用法错误
- `git`/GitHub API 副作用收进独立函数，测试可注入 fake（不真调网络）

### 3.2 明确不做

- 不做 e2e / 真跑 Actions 的集成测试
- 不做 `tools/run.py` 统一入口、Makefile（YAGNI）
- 不改 userscript-console 的 `action.yml` 接口

## 4. 各 workflow 改造对照

### 4.1 `issue-commands.yml`（4 处 shell → Python）

```yaml
steps:
  - uses: actions/checkout@v5                      # ① 统一 checkout（D2）
  - name: Permission gate                          # ② gate.py
    id: gate
    env: { COMMENT_USER: ${{ github.event.comment.user.login }},
           REPO_OWNER: ${{ github.repository_owner }},
           COMMENT_ID: ${{ github.event.comment.id }},
           GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
    run: python tools/gate.py
  - name: Run command                              # ③④ Action，不动
    id: cmd
    if: steps.gate.outputs.authorized == 'true'
    uses: acg-q/userscript-console@v1.1.0
    with: { command: run-command, github-token: ${{ secrets.GITHUB_TOKEN }},
            comment-body: ${{ github.event.comment.body }},
            comment-user: ${{ github.event.comment.user.login }},
            issue-number: ${{ github.event.issue.number }}, use-binary: true }
  - name: Project issues
    id: proj
    if: steps.gate.outputs.authorized == 'true'
    uses: acg-q/userscript-console@v1.1.0
    with: { command: project, github-token: ${{ secrets.GITHUB_TOKEN }}, use-binary: true }
  - name: Commit changes                           # ⑤ commit.py
    id: commit
    if: steps.gate.outputs.authorized == 'true' && steps.cmd.outputs.changed == 'true'
    run: python tools/commit.py --allowlist registry.json scripts dist archive
         --message "Apply command: ${{ github.event.comment.user.login }}"
  - name: Trigger site deploy                      # ⑥ dispatch_deploy.py
    if: steps.gate.outputs.authorized == 'true' && steps.commit.outputs.committed == 'true'
    env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
    run: python tools/dispatch_deploy.py --workflow deploy-pages.yml
  - name: Reply to comment                         # ⑦ reply.py（!cancelled() 原样保留）
    if: ${{ !cancelled() && steps.gate.outputs.authorized == 'true' }}
    env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }},
           RESULT: ${{ steps.cmd.outputs.result }}, PROJ: ${{ steps.proj.outputs.result }},
           CMD_OK: ${{ steps.cmd.outcome }},
           ISSUE_NUMBER: ${{ github.event.issue.number }} }
    run: python tools/reply.py
```

### 4.2 其余 5 条

| 文件 | 改动 |
|---|---|
| `deploy-pages.yml` | `_site` 组装 → `python tools/assemble_site.py`；Action 构建、configure-pages、upload、deploy job 不动 |
| `sync-scheduled.yml` | 提交/派发 → `commit.py --allowlist registry.json scripts dist` / `dispatch_deploy.py`；输出名 `pushed` 统一为 `committed` |
| `cleanup-panel.yml` | 输入归一 → `cleanup_config.py`；提交 → `commit.py --allowlist archive`；派发 → `dispatch_deploy.py`；**删除"汇总"步骤**（脚本自身打印日志） |
| `validate.yml` | 内联 `python -c` → `python tools/validate_registry.py`（纯标准库，无安装步骤）；doctor Action 步骤不动 |
| `init-command-panel.yml` | 补 `permissions: contents: read` + `checkout`；`gh` 逻辑 → `python tools/init_panel.py` |

### 4.3 逐字保留的契约

`on:` / `permissions:` / `concurrency` / `timeout-minutes` / `if` 门禁表达式 / Action 调用参数 / 输出名（`authorized`/`changed`/`committed`）/ "失败也回帖（`!cancelled()`）" / "GITHUB_TOKEN push 不触发 workflow 需显式派发" / 白名单提交路径。

## 5. 错误处理

| 场景 | 行为 |
|---|---|
| 脚本运行失败（API/git/校验不过） | 非 0 退出 → job 红，打印明确错误；禁止 `except: pass` |
| 派发部署失败 | `::warning::` + 退出 0（**不阻断**，与现状一致） |
| `gate.py` 未授权 | 退出 0 + `authorized=false`（业务分支非错误）；删评论 API 失败 → 非 0 |
| `commit.py` 无变更 | 退出 0 + `committed=false`（短路） |
| 缺必需 env/参数 | 退出 2（用法错误，与运行时错误区分） |

## 6. 测试

- 位置：`tools/tests/`，框架用标准库 `unittest`（本仓无既有测试基建、零新增依赖）
- **纯逻辑覆盖**：`gate.py` 授权判定、`reply.py` 三态正文组装、`cleanup_config.py` 双触发源归一、`assemble_site.py` 文件分类、`validate_registry.py` 合法/缺 id/非法 type
- **副作用隔离**：`commit.py`、`init_panel.py`、`dispatch_deploy.py` 的 git/API 调用收进可注入函数，测试用 fake
- 验收命令：
  ```bash
  python -m unittest discover tools/tests -q
  python tools/validate_workflows.py
  ```

## 7. 文档同步（同 PR 必改）

| 文件 | 冲突点 | 改法 |
|---|---|---|
| `docs-ownership.md` | `tools/**` 列在"迁出"且核对脚本检查其不存在 | `tools/` 移入"保留"清单；核对脚本同步改 |
| `PLAN.md` | U4-1"删除全部 Python"、U4-2"删 requirements/ruff/mypy 且 CI 不再 pip install" | U4-1 收窄为"删除已迁出的业务 Python，`tools/` 保留"；U4-2 收窄为"业务依赖不装"（`tools/` 脚本纯标准库，无需安装步骤） |
| `SPEC-WORKFLOWS.md` | 明文要求 `set -euo pipefail`、heredoc 等 shell 纪律；§2 是含 shell 的完整形态 | §2 整体替换为一行式 Python 形态；shell 纪律改为 Python 脚本编写纪律（退出码、不吞异常、env/CLI 双通道） |

**连带**：`validate_workflows.py` 规则更新——保留"禁止 `git add .`"、SHA pin、权限/超时/并发校验；删除 shell 存在性校验，新增"`run:` 必须匹配 `python tools/*.py`"。

**不动**：根 `README.md`（DR-5 仍成立）、`BASELINE.md`、`CUTOVER.md`。

## 8. 验收（Definition of Done）

```bash
python -m unittest discover tools/tests -q        # 新增测试全绿
python tools/validate_workflows.py                  # 规则更新后全绿
grep -rn 'run: |' .github/workflows/                # 无多行 shell（仅允许一行式 python）
python tools/assemble_site.py --root <tmp>          # 本地可跑
python tools/validate_registry.py                   # 本地可跑
```

外加一次真实事件回归：Issue #1 发一条 `/list`，确认回帖、提交白名单、派发部署三条链路行为与重构前一致。
