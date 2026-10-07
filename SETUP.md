# SETUP.md — 远端仓库配置清单

> 执行顺序：先配置 **硬性依赖**（否则 workflow 直接红），再配置 **可选优化**。
> 每项都有「是否必须」标签和「不配会怎样」说明。

---

## 一、硬性依赖（不配 workflow 必红）

### 1. GitHub Pages — 启用 + 部署来源 = GitHub Actions

| 项 | 值 |
|---|---|
| 设置路径 | Settings → Pages → Build and deployment → **Source: GitHub Actions** |
| 分支 | `master`（工作流已硬编码） |
| 路径 | `/ (root)`（默认） |

> **为什么**：`deploy-pages.yml` 用 `actions/deploy-pages@v4` 部署，不是从 `gh-pages` 分支构建；若选错了来源会报 "No HTML files found"。

**验证**：触发一次 `deploy-pages.yml` 手动运行后，`Settings → Pages` 显示 `https://<owner>.github.io/<repo>/` 且「部署成功」。

---

### 2. Discussions — 启用

| 项 | 值 |
|---|---|
| 设置路径 | Settings → Features → **Discussions** ✅ 勾选 |
| 默认状态 | GitHub 新建仓库默认关闭，需手动开启 |

> **为什么**：`issue-commands.yml` 和 `deploy-pages.yml` 声明了 `discussions: write` / `discussions: read`。未启用 Discussions 时，`CreateDiscussion` API 会返回 **403**，版本帖静默丢失（真实事故，见 CUTOVER §5）。

**验证**：仓库主页导航栏出现「Discussions」标签；或运行 `curl -s -H "Authorization: token $GH_TOKEN" https://api.github.com/repos/<owner>/<repo>/discussions | grep -c "message"`。

---

### 3. Issues — 启用（默认已开）

| 项 | 值 |
|---|---|
| 设置路径 | Settings → General → Features → **Issues** ✅ |
| 默认状态 | 新建仓库默认开启 |

> **为什么**：命令面板在 Issue #1，`issue-commands.yml` 需要 `issues: write`。若关闭则无法发帖/回帖。

---

## 二、可选优化（不配不影响运行，但用户体验更好）

### 4. Actions — 启用（默认已开）

| 项 | 值 |
|---|---|
| 设置路径 | Settings → Actions → General → **Actions permissions** → 允许所有 Actions |
| 风险 | 若选 "Only selected Actions"，需额外添加 `acg-q/userscript-console` |

---

### 5. Repository Variables（可选，已有合理默认值）

| 变量名 | 设置路径 | 默认值 | 用途 |
|---|---|---|---|
| `AUTHOR_NAME` | Settings → Secrets and variables → **Variables** | `usm` | 自写脚本头部默认作者名 |
| `AUTHOR_NAMESPACE` | 同上 | ``（空） | 自写脚本头部默认命名空间 |
| `PAGES_BASE` | 同上 | 自动推导 | 站点绝对 URL（如 `https://acg-q.github.io/userscript-console`），一般不需设 |

> 这三个变量只在 `/add` 或自写脚本时影响头部默认值，**不设也能正常运行**。

---

### 6. Branch Protection（推荐）

| 设置 | 建议值 |
|---|---|
| Require pull request reviews | ✅ 开启（PR 流程） |
| Require status checks | ✅ `test`（工具仓）、`validate`（内容仓） |
| Restrict who can push | 仅 owner（防止直接 push master） |
| Include administrators | ✅ 开启 |

> 注意：`GITHUB_TOKEN` 的 push **不会触发** workflow（这是 GitHub 的安全设计），所以 `issue-commands.yml` 的第⑤步必须显式 `gh workflow run deploy-pages.yml`。

---

## 三、零配置项（不用操心）

以下项目 GitHub Actions **自动处理**，无需手动配置：

| 项 | 说明 |
|---|---|
| `secrets.GITHUB_TOKEN` | 自动注入，权限由 workflow 的 `permissions:` 块声明 |
| `actions/checkout@v4` | GitHub 官方 action，预装在 runner 上 |
| `actions/setup-go@v5` | 同上 |
| `actions/configure-pages@v5` | 同上 |
| `actions/upload-pages-artifact@v3` | 同上 |
| `actions/deploy-pages@v4` | 同上 |
| `gh` CLI | 预装在 GitHub-hosted runner（`ubuntu-latest`）上 |
| `jq` | 预装在 GitHub-hosted runner 上 |
| `python` | 预装在 GitHub-hosted runner 上 |

---

## 四、首次上线操作序列

```bash
# 1. 推送代码到远端（假设远端名为 origin，分支 master）
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin master

# 2. init-command-panel 随 push 自动运行（幂等建 Issue #1）；如需手动补跑：
gh workflow run init-command-panel.yml

# 3. 检查 Pages 部署是否成功
gh run watch --workflow deploy-pages.yml  # 或网页查看 Actions tab

# 4. 验证 Discussions 已启用
gh api repos/<owner>/<repo> | jq '.has_discussions'
# 应输出 true
```

---

## 五、故障排查速查

| 症状 | 原因 | 修复 |
|---|---|---|
| `deploy-pages` job 报 "No HTML files found" | Pages 来源设成了 "Upload artifact" 而非 "GitHub Actions" | Settings → Pages → Source 改为 GitHub Actions |
| `CreateDiscussion` 403 | Discussions 未启用 | Settings → Features → Discussions ✅ |
| 回帖 403 | `permissions: discussions: write` 遗漏 | 核对 SPEC-WORKFLOWS §3 权限表 |
| `gh workflow run` 403 | `permissions: actions: write` 遗漏 | 核对权限表 |
| 站点 URL 不对 | `PAGES_BASE` 未设且自动推导失败 | 在 Settings → Variables 设置 `PAGES_BASE=https://...` |
| `usm` 作者名不对 | `AUTHOR_NAME` 未设，使用默认 `usm` | Settings → Variables → 设置 `AUTHOR_NAME` |
