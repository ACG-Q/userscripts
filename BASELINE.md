# BASELINE.md · 迁移前基线

> 记录迁移起点，供 CUTOVER 阶段对比验证。

---

## 仓库基线

| 项 | 值 |
|---|---|
| 仓名 | `userscript-manager`（**禁止改名**，DR-3） |
| Pages URL | `https://acg-q.github.io/userscript-manager` |
| 工具仓 SHA | `ffd137cd20c780e1b582e752c8631e9dbe1cc31c`（`userscript-console@v1`） |
| 本仓 HEAD | `ffd137cd20c780e1b582e752c8631e9dbe1cc31c` |

---

## 存量安装链接数

```bash
# 迁移前记录（阶段 4 U4-6 验收时核对无减少）
grep -c 'downloadURL' dist/*.user.js 2>/dev/null || echo "0"
```

**基线值**：`N`（填写实际数字，当前 registry 为空 → `0`）

---

## 验收 checklist（CUTOVER §4）

- [ ] `grep -rn 'git add \.\|git add -A\|git add --all' .github/` 无匹配
- [ ] 4 条 workflow 的 `uses:` 全为 40 位 sha；`permissions:` 与 SPEC-WORKFLOWS §3 表一致
- [ ] `validate.yml`（doctor）在 PR 与 push 上运行
- [ ] 工具代码/测试/requirements 已从本仓删除
- [ ] `docs/index.md` 为脚本文档索引
- [ ] 站点冒烟 6 项全绿；安装链接数未减少
- [ ] `registry.json` 的 `git log` 在切换期间只有工具产生的正常变更
