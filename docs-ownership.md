# docs-ownership.md — 文档归属清单

> 与工具仓 `userscript-console/README.md §6` 目录规划互为镜像；两清单无重叠、无遗漏。

---

## 迁出 → 工具仓（`userscript-console`）

| 路径 | 说明 |
|---|---|
| `console.py` | CLI 单入口 |
| `manager.py` | 主逻辑入口 |
| `project_issues.py` | 投影逻辑 |
| `build_pages.py` | 站点生成 |
| `panel_cleanup.py` | 面板清理 |
| `pages_assets.py` | 静态资源 |
| `userscript_manager/**` | Python 包 |
| `tests/**` | Python 测试 |
| `tools/**` | 工具脚本（含 `validate_graphql.py`） |
| `requirements.txt` | 生产依赖 |
| `requirements-dev.txt` | 开发依赖 |
| `ruff.toml` | linter 配置 |
| `mypy.ini` | type checker 配置 |
| `.coveragerc` | 覆盖率配置 |
| `docs/commands/*.md` | 命令用法文档 |
| `docs/design.md` | 系统设计文档 |
| `docs/code-review-*.md` | 审查记录 |

---

## 保留在本仓（内容/数据仓）

| 路径 | 说明 |
|---|---|
| `registry.json` | 脚本注册表（唯一真源） |
| `scripts/self/**` | 自写脚本源码 + README |
| `scripts/synced/**` | 同步脚本源码 |
| `dist/*.user.js` | 安装包（**必须入库**） |
| `archive/commands.json` | 命令历史归档 |
| `docs/index.md` | 脚本文档索引 |
| `README.md` | 面向用户的安装/使用指南 |
| `.github/workflows/*.yml` | 薄壳 workflow（5 条） |
| `.gitignore` | 路径忽略规则 |
| `PLAN.md` / `SPEC-DATA.md` / `SPEC-WORKFLOWS.md` / `CUTOVER.md` | 本仓实施规格 |

---

## 核对

```bash
# 工具仓（检查迁出路径不存在）
git ls-tree -r HEAD --name-only | grep -E '(console\.py|manager\.py|project_issues\.py|build_pages\.py|panel_cleanup\.py|pages_assets\.py|userscript_manager|tests/|tools/|requirements|’ruff|’mypy|.coveragerc|docs/commands|docs/design|docs/code-review)' || echo "✓ 迁出路径已清空"

# 本仓（检查保留路径存在）
ls registry.json scripts/ dist/ archive/ docs/index.md README.md .github/workflows/ 2>/dev/null && echo "✓ 保留路径存在"
```
