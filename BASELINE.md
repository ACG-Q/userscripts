# BASELINE.md · 迁移前基线

> 记录迁移起点，供 CUTOVER 阶段对比验证。

---

## 仓库基线

| 项 | 值 |
|---|---|
| 仓名 | `userscript-manager`（**禁止改名**，DR-3） |
| Pages URL | `https://acg-q.github.io/userscript-manager` |
| 工具仓 SHA | `c459f821839bb0b2e434751a8be45bf4415f73e4`（`userscript-console` master：Actions 版本升级至 Node 24 基线） |
| 本仓 HEAD | （推送后见 `git rev-parse HEAD`） |
| workflow pin | 7 处 `uses:` 全部对齐工具仓 master ✅ |
| 校验 | `python tools/validate_workflows.py` 自动比对工具仓 `origin/master`，pin 过期即红（U3-4） |

---

## 存量安装链接数

```bash
# 迁移前记录（阶段 4 U4-6 验收时核对无减少）
grep -c 'downloadURL' dist/*.user.js 2>/dev/null || echo "0"
```

**基线值**：`0`（当前 registry 为空，无存量脚本）

---

## 验收 checklist（CUTOVER §4）

- [ ] `grep -rn 'git add \.\|git add -A\|git add --all' .github/` 无匹配
- [ ] 4 条 workflow 的 `uses:` 全为 40 位 sha；`permissions:` 与 SPEC-WORKFLOWS §3 表一致
- [ ] `validate.yml`（doctor）在 PR 与 push 上运行
- [ ] 工具代码/测试/requirements 已从本仓删除
- [ ] `docs/index.md` 为脚本文档索引
- [ ] 站点冒烟 6 项全绿；安装链接数未减少
- [ ] `registry.json` 的 `git log` 在切换期间只有工具产生的正常变更
