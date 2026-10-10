# SPEC · 数据契约（内容仓的"真源"规范）

> 本仓所有文件的**格式、所有权与演进规则**。工具仓读写这些文件，必须遵守本文件；
> 反过来，本仓任何人改动数据格式，必须先改本文件并同步工具仓 `SPEC-ARCH-TEST.md`。

---

## 1. `registry.json` —— 唯一真源

### 1.1 结构（schema = 1）

```jsonc
{
  "schema": 1,
  "scripts": [
    {
      // ── 通用字段（字段清单，展示序；键序以定型的序列化格式为准，见读写规则 3/4） ──
      "id": "3f45ee3c-…",          // self=UUID；synced=来源URL MD5 前12位
      "type": "self" | "synced",
      "name": "...", "version": "1.0.1", "description": "...",
      "author": "...", "namespace": "...",
      "match": ["*://*/*"], "grant": ["none"],
      "enabled": true,
      "created_at": "2026-10-02T…Z", "updated_at": "2026-10-02T…Z",
      "documentation": "",          // Markdown 正文（README 冗余副本）
      "changelog": [ { "version": "1.0.1", "date": "2026-10-02", "note": "手动更新" } ], // 新→旧
      "discussions": [ { "version": "1.0.1", "number": 10, "node_id": "D_…",
                         "url": "https://github.com/…/discussions/10",
                         "created_at": "2026-10-02" } ],   // 旧→新（账本，末条=当前版本帖）
      "deleted": false,             // 软删除标记
      "issue": { "number": 5, "node_id": "I_…", "url": "https://github.com/…/issues/5" },

      // ── synced 专有 ──
      "source_url": "https://…", "source_type": "greasyfork|direct|github_gist|userscript_zone",
      "last_synced_at": "…Z" | null, "sync_enabled": true,
      "custom_match": null          // 历史字段，保留
    }
  ]
}
```

**读写规则**（工具必须实现，`userscript_manager/registry.py` 为参照）：
1. **加载即校验**：非对象 / `scripts` 非数组 / 缺 `id` / `type` 非法 → 报错并提示「用 Git 历史恢复，不要直接删除」；
2. **向后兼容默认值**：读入即 `discussions=[]`、`deleted=false`（老数据无需迁移脚本）；
3. **原子写**（临时文件+rename）：序列化格式一经定型必须稳定（`Load→Save` 空改动字节不变），实现可用 struct 或 map（排序键即稳定），见工具仓 SPEC §I-2（DR-6：格式允许一次性规范化）；
4. **JSON 形态**：2 空格缩进、不转义非 ASCII、**无结尾换行**（现有文件末字节为 `}`）——默认沿用此形态；允许一次性规范化（DR-6），一旦定型不得再变；
5. **幂等**：`Load → Save` 无改动时字节不变（避免无意义 diff）。

### 1.2 schema 演进规则

| 变更类型 | 动作 |
|---|---|
| 新增可选字段 | 工具 `setdefault` 写入；**不 bump** `schema` |
| 字段改名/删除/语义变化 | bump `"schema": 2`，并同步：工具 `--registry-schema-version` 默认值 → Action input 默认 → 本仓 `validate.yml` 断言值 |
| 迁移期兼容 | 工具必须能读 `schema ∈ {1,2}`（读旧写旧）；**未来引入 schema 升级时，必须以显式 `--migrate` 才允许升级写入**（届时在 SPEC-CLI 收录该 flag） |

**跨仓协调**：`registry-schema-version` 不匹配 → Action 失败（防「工具 v2 写 schema 2、内容仓还是 1」的静默损坏）。

---

## 2. 目录与文件契约

### 2.1 源码树（工具写、人可改文档）

```
scripts/
├── self/<id>/index.js              # 自写脚本源码（仅代码，无头部外的文档）
│        └── README.md              # 自写脚本文档（save_documentation 写入）
└── synced/<id>/script.user.js      # 同步脚本源码（上游原文，不美化）
```
- `/rm` 软删除：**删除对应源码目录 + `dist/<id>.user.js`**，registry 条目保留（`deleted: true`）；
- `/add <url>` 同源复活：**复用原 id**，重建源码与 dist（工具仓 I-4 不变量）；
- `doctor --check` 校验：每条未删条目的源码文件存在、每个目录都有对应条目（孤儿检测）。

### 2.2 `dist/`（跟踪 vs 忽略 —— **最容易搞错的一张表**）

| 路径 | git | 原因 |
|---|---|---|
| `dist/<id>.user.js` | ✅ **必须入库** | 安装/更新 URL 直接指向 Pages 上的该文件；丢失=全部用户 404 |
| `dist/index.html` | ❌ ignore | `build` 在部署期生成 |
| `dist/scripts/**` | ❌ ignore | 同上（详情页） |
| `dist/scripts.json` | ❌ ignore | 同上（首页懒加载数据） |
| `dist/commands/**` | ❌ ignore | 同上（命令归档分页） |
| `dist/build-warnings.txt` | ❌ ignore | 构建诊断，**只在有问题时生成** |

### 2.3 `archive/commands.json`（`cleanup` 写入，**入库**）

```jsonc
{
  "schema": 1,
  "commands": [                    // 旧→新（按归档时间累积）
    {
      "command_id": "IC_…", "author": "ACG-Q",
      "command": "/add https://…", "created_at": "2026-10-02T…Z",
      "results": [ { "id": "IR_…", "author": "github-actions[bot]",
                     "body": "**执行结果：**\n✅ …", "created_at": "…" } ],
      "archived_at": "2026-10-03T…Z"
    }
  ]
}
```
- **幂等键** = `command_id`（孤儿组用首条 result id）；重复触发不得重复归档；
- 归档**先落盘再删评论**（工具仓 I 序列），删除失败下轮只补删除；
- 站点 `commands/page-N.html` 每页 5 条、新→旧渲染自本文件（**顺序反转**）。

---

## 3. 文档归属（已收敛，2026-10-09；发布迁移 2026-10-09 方案 B）

| 文档 | 归属 | 说明 |
|---|---|---|
| `docs/index.md` + `docs/commands/*.md` | **源在工具仓** `userscript-console/docs/` | 与工具代码同 PR 演进；`deploy-pages.yml` 部署前 sparse-checkout 拉取到 `./docs/`，`usm build` 转换为本站 `/docs/`（`HasDocs=true` → 导航「文档」指向 `docs/index.html`） |
| `docs/dev/*.md` | 工具仓 | 纯仓库文档，不转换为站点页 |
| ~~`docs/design.md`~~ | 已移除（2026-10-09） | 系统设计在工具仓历史规格 |
| ~~`docs/code-review-2026-10-03.md`~~ | 已移除（2026-10-09） | 审查档案在工具仓历史规格 |
| `README.md` | **本仓** | 面向脚本用户：安装、如何在 Issue #1 发命令、脚本列表；命令速查**链接**到工具仓 README |

> 本仓不持任何文档源文件（`docs/` 不入库，仅 CI 工作区临时落位）；工具仓自有 Pages 站已下线（2026-10-09），文档唯一发布地址为本站 `/docs/`。
> 历史清单（`BASELINE.md` / `CUTOVER.md` / `PLAN.md` / `docs-ownership.md`）已于 2026-10-10 文档精简移除，见 git 历史。

---

## 4. `.gitignore`（目标形态；迁移期条目见行内注释）

```gitignore
# 站点部署产物（build 生成，不入库）
dist/index.html
dist/scripts/
dist/scripts.json
dist/commands/
dist/build-warnings.txt
_site/

# 运行期临时（阶段 4 后 command_result.txt 随 Python 移除）
command_result.txt
*.tmp
*.log

# 阶段 4 移除工具代码后不再需要的条目（U4-2）
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
coverage.xml
htmlcov/
tools/schema.docs.graphql
```
⚠️ **不得**出现 `dist/`、`dist/*.user.js`、`scripts/`、`archive/` 这类整目录忽略。

---

## 5. 仓库设置（不随迁移改变）

| 项 | 值 | 消费者 |
|---|---|---|
| 仓名 | `userscript-manager`（**禁止改名**，DR-3） | 存量 `@downloadURL/@updateURL` |
| Pages | 启用，`https://acg-q.github.io/userscripts` | 安装链接 |
| vars `GITHUB_PAGES_URL` | 若已设则留空亦可（`build` 由 repo 推导） | `usm build` |
| vars `AUTHOR_NAME` / `AUTHOR_NAMESPACE` | 现值 | 自写脚本头部默认值 |
| 命令面板 | Issue #1（`control_issue_number` 硬编码在工具侧） | 所有 workflow 的 `if` |

---

## 6. 数据完整性自检（`usm doctor --check`，本仓 `validate.yml` 调用）

1. `registry.json` 可解析、`schema` 与预期一致、每条 `id/type` 合法；
2. 未软删条目的源码文件存在；已软删条目**没有**源码与 dist 文件；
3. `dist/<id>.user.js` 与 `enabled`：禁用条目仍可保留文件（当前行为），但**不得存在「条目已删而 dist 还在」**；
4. 孤儿目录（盘上有、registry 无）→ 报错；
5. `archive/commands.json` 可解析、`schema` 合法、无重复 `command_id`；
6. `scripts.json` / 站点 HTML 属部署产物，**不参与**本检查（本地不存在属正常）。

任何一条失败 → `doctor` exit 1 → `validate.yml` 红。
