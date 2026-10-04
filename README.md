# userscript-manager · 内容/数据仓

> **工具已迁往 [`acg-q/userscript-console`](https://github.com/acg-q/userscript-console)**。
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
- **Pages 宿主**：`build` 产出 → `_site` → `actions/deploy-pages`
- **触发器**：所有 workflow 的 `on:` / `permissions:` / `concurrency` 归本仓管理

详见 [PLAN.md](./PLAN.md) 与 [SPEC-DATA.md](./SPEC-DATA.md)。
