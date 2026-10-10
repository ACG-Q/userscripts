# userscript-manager · 数据仓 + 工具仓

> 双仓协同模式：`userscript-manager` 为内容/数据仓，`acg-q/userscript-console` 为工具仓。
> - **内容仓** (`userscript-manager`)：存储真源数据（`registry.json`、`scripts/`、`dist/`、`archive/`)，编排 Pages 部署产物。
> - **工具仓** (`acg-q/userscript-console`)：提供 `usm` CLI 与 GitHub Action（门禁删评 / 结果回帖 / 构建 / 投影 / 清理 / 自检），及测试、快照基线等工程资产。
> - 数据变更通过本仓 Issue #1 触发本仓 workflow，由其调用工具仓 action 处理；工具仓命令速查请见 [README §6](https://github.com/acg-q/userscript-console#6-仓库设置)。

---

> **工具已迁往** [`acg-q/userscript-console`](https://github.com/acg-q/userscript-console)。
> 所有命令通过 Issue #1 发送，工具自动处理；本仓只存真源数据与 Pages 部署产物。

---

## 安装脚本

在 [GreasyFork](https://greasyfork.org/) 或 [userscript.zone](https://userscript.zone/) 搜索本仓同名项目，
或直接访问 `https://acg-q.github.io/userscript-manager/dist/<id>.user.js` 安装。

---

## 使用命令面板

1. 打开本仓 **Issue #1**（命令面板）
2. 在评论中输入命令：

| 命令 | 说明 |
|---|---|
| `/list` | 列出所有脚本 |
| `/info <id>` | 查看脚本详情 |
| `/add <URL>` | 从 GreasyFork / Gist / 直链添加脚本 |
| `/rm <id>` | 软删除脚本 |
| `/sync-all` | 同步所有 synced 类型脚本 |
| `/build` | 重建站点 |

完整命令列表见 **[工具仓命令文档](https://github.com/acg-q/userscript-console#命令速查)**。

---

## 站点

- **主页**：https://acg-q.github.io/userscript-manager/
- **脚本详情页**：`https://acg-q.github.io/userscript-manager/scripts/<id>.html`
- **脚本列表 JSON**：`https://acg-q.github.io/userscript-manager/scripts.json`

---

## 本仓定位

- **真源数据**：`registry.json`、`scripts/`、`dist/*.user.js`、`archive/commands.json`
- **Pages 宿主**：`build`（action input `pages-out: _site` 一步搬移）→ `actions/deploy-pages`
- **触发器**：所有 workflow 的 `on:` / `permissions:` / `concurrency` 归本仓管理

详见 [SPEC-WORKFLOWS.md](./SPEC-WORKFLOWS.md) 与 [SPEC-DATA.md](./SPEC-DATA.md)。

---

## 运维配置（并入原 SETUP.md）

> 执行顺序：先配置**硬性依赖**（否则 workflow 直接红），再配置**可选优化**。

### 硬性依赖（不配 workflow 必红）

| # | 项 | 设置 | 不配会怎样 |
|---|---|---|---|
| 1 | GitHub Pages 来源 | Settings → Pages → Build and deployment → **Source: GitHub Actions**（分支 `master`、路径 `/`） | `deploy-pages` 报 "No HTML files found" |
| 2 | Discussions | Settings → Features → **Discussions** ✅ | `CreateDiscussion` 403，版本帖静默丢失（真实事故） |
| 3 | Issues | Settings → General → Features → **Issues** ✅（默认已开） | 命令面板/回帖不可用 |

**验证**：手动跑一次 `deploy-pages.yml` 后 `Settings → Pages` 显示部署成功；
`gh api repos/<owner>/<repo> | jq '.has_discussions'` 输出 `true`。

### 可选优化

| 项 | 说明 |
|---|---|
| Actions permissions | 若设为 "Only selected Actions"，需添加 `acg-q/userscript-console` |
| Variables `AUTHOR_NAME` / `AUTHOR_NAMESPACE` / `PAGES_BASE` | 均有合理默认值；只影响自写脚本头部与站点绝对 URL，不配也能跑 |
| Branch Protection | 推荐 PR review + status checks（`test` 工具仓、`validate` 内容仓）+ 仅 owner 直推 |

> `GITHUB_TOKEN` 的 push **不会触发** workflow（GitHub 安全设计），所以提交后由
> workflow 显式 `gh workflow run deploy-pages.yml` 派发站点重建。

### 零配置项（自动处理）

`secrets.GITHUB_TOKEN`（权限由各 workflow `permissions:` 声明）、`actions/checkout`、
`actions/configure-pages`、`actions/upload-pages-artifact`、`actions/deploy-pages`、
预装的 `gh` 与 `jq`——均无需手动配置。**workflow 已零 Python 依赖**（唯一例外是
`init-command-panel.yml` 调用保留的 `tools/init_panel.py`，用 runner 预装 python 运行）。

### 首次上线操作序列

```bash
# 1. 推送代码到远端（假设远端名为 origin，分支 master）
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin master

# 2. init-command-panel 随 push 自动运行（幂等建 Issue #1）；如需手动补跑：
gh workflow run init-command-panel.yml

# 3. 检查 Pages 部署是否成功
gh run watch --workflow deploy-pages.yml  # 或网页查看 Actions tab

# 4. 验证 Discussions 已启用
gh api repos/<owner>/<repo> | jq '.has_discussions'   # 应输出 true
```

### 故障排查速查

| 症状 | 原因 | 修复 |
|---|---|---|
| `deploy-pages` 报 "No HTML files found" | Pages 来源设成了 "Upload artifact" | Settings → Pages → Source 改为 GitHub Actions |
| `CreateDiscussion` 403 | Discussions 未启用 | Settings → Features → Discussions ✅ |
| 回帖 403 | `permissions: issues: write` 遗漏 | 核对 SPEC-WORKFLOWS §2 权限表 |
| `gh workflow run` 403 | `permissions: actions: write` 遗漏 | 核对权限表 |
| 站点 URL 不对 | `PAGES_BASE` 未设且自动推导失败 | Settings → Variables 设置 `PAGES_BASE=https://...` |
| `usm` 作者名不对 | `AUTHOR_NAME` 未设，使用默认 `usm` | Settings → Variables → 设置 `AUTHOR_NAME` |
