# CUTOVER · 切换、验证与回滚 Runbook

> 执行者：人 或 AI。每一步都有**前置条件 / 动作 / 验证 / 回滚**四段，任一验证失败即停在当前步。
> 配套：`PLAN.md`（阶段编号）、`SPEC-WORKFLOWS.md`（YAML 全文）、`../userscript-console/PLAN.md`（工具侧）。

---

## 0. 基线（开始前必须记录，见 PLAN U0-6）

```bash
# 在内容仓 master
git rev-parse HEAD                          # → BASELINE.content
grep -c 'downloadURL' dist/*.user.js        # → 存量安装链接数 N
# 在工具仓（阶段1后）
git rev-parse HEAD                          # → BASELINE.tool
```

**硬约束**：仓名与 Pages URL 不变（DR-3）；`dist/*.user.js` 始终入库。

---

## 1. 切换序列（严格按序，每步绿了才进下一步）

### Step 1 —— 同仓准备（PLAN 阶段 0）
- 前置：无
- 动作：U0-1/2（`git add` 白名单）、U0-3（docs 归属）、U0-5（`validate.yml` 骨架）、U0-6（基线）
- 验证：`grep -rn 'git add \.' .github/workflows/` 无匹配；`validate.yml` 绿；`BASELINE.md` 已提交
- 回滚：`git revert` 对应提交

### Step 2 —— 建工具仓（工具仓 PLAN 阶段1 / 内容仓 U1）
- 前置：U1-1 迁出路径清单终签（基于 U0-3 的 `docs-ownership.md`）
- 动作：克隆镜像 → `git filter-repo --path <清单>` → 推到新仓 `userscript-console` → 工具仓 CI 首跑
- 验证：工具仓 `pytest tests/` 全绿；`tests/snapshot/`、`tests/fixtures/` 目录就位（快照基线随后续 M-0/M-1 逐步提交）；**内容仓 `git status` 干净、历史未变**
- 回滚：删除新仓即可（内容仓零改动）

### Step 3 —— 接入第一条 workflow（`issue-commands.yml`，U2-1）
- 前置：工具仓已打 tag（`v0.1.0`），`action.yml` v0（Python 实现）自测绿
- 动作：按 `SPEC-WORKFLOWS §2.1` 改写，pin sha，提 PR
- 验证（**端到端三条**）：
  1. Issue #1 发 `/list` → 正常回帖、`git diff` 无（`changed=false` 不提交）
  2. Issue #1 发 `/add <代码块>` → 回帖含 ID；`git status` **只有** `registry.json`/`scripts/`/`dist/` 变化
  3. 用另一账号发命令 → 评论被删、无回帖
- 回滚：revert 该 PR → 回到内联 Python 步骤（Python 代码仍在本仓）

### Step 4 —— `deploy-pages.yml`（U2-2）
- 动作：按 `SPEC-WORKFLOWS §2.2` 改写（触发器与 `if` 逐字保留）
- 验证：站点三件套可取；`https://acg-q.github.io/userscript-manager/scripts/3f45ee3c-….html` 有版本下拉；在版本帖发评论 → ~30s 后重建
- 回滚：revert

### Step 5 —— `sync-scheduled.yml`（U2-3）
- 动作：按 `SPEC-WORKFLOWS §2.3` 改写
- 验证：手动 dispatch → `registry.json` 的 `last_synced_at` 更新、回帖/日志正常、部署被 `gh workflow run` 派发
- 回滚：revert

### Step 6 —— `cleanup-panel.yml`（U2-4）
- 动作：按 `SPEC-WORKFLOWS §2.4` 改写
- 验证：dispatch → 当前 6 组 < 10 → **「无需清理」且无提交**；再用 dry-run（`apply: false`）跑一次 U3-3 观察项
- 回滚：revert

### Step 7 —— 运行观察（PLAN 阶段3）
- 时长：≥2 周 或 连续 10 次命令运行
- 指标（U3-1..U3-4）：`git diff --exit-code registry.json scripts dist` 无差异；站点冒烟清单（§3）全过
- 出口：工具仓测试与快照全绿（`MIGRATION §4`）

### Step 8 —— 瘦身（PLAN 阶段4，U4-1..U4-6）
- 动作：删除迁出路径 → `test.yml` 换 `validate.yml`（doctor）→ 文档/README 收尾 → pin 固化
- 验证：§4 最终验收全绿
- 回滚：`git revert`（文件都能从历史找回；**数据从未被删**）

### Step 9 —— 工具仓切 Go 二进制（工具仓 C4-2，**内容仓无动作**）
- 验证：内容仓 4 条 workflow 不改一行全部重跑绿（接口未变的证明）

---

## 2. 回滚速查表

| 症状 | 回滚动作 | 耗时 |
|---|---|---|
| 某条 workflow 行为错 | revert 该条 PR（回到内联 Python 或上一 sha pin） | 分钟 |
| Action 整体异常 | 所有 `uses:` pin 改回上一个 sha（或回 `v0.x`） | 分钟 |
| Go 版实现异常 | 工具仓 `action.yml` 的 v1 步骤 revert 回 v0（Python），内容仓**零改动** | 分钟 |
| 数据被写坏 | 内容仓 `git revert <坏提交>`（registry/scripts 都在 git） | 分钟 |
| 站点异常 | `workflow_dispatch` 重跑 deploy；或回滚触发它的提交 | 分钟 |
| 存量安装链接失效 | **不可回滚**（靠 DR-3 预防：永不改仓名/Pages） | — |

---

## 3. 站点冒烟清单（每次部署后，U3-2）

```
GET /index.html                     → 含「命令归档」链接、卡片「讨论」指向 discussions/N
GET /scripts.json                   → HTTP 200，数组长度 == registry 脚本数
GET /scripts/<id>.html              → 版本帖面板（discVerBtn/discData）或合法回退
GET /commands/page-1.html           → 空态或最近 5 条
GET /dist/<id>.user.js              → HTTP 200（安装链接）
GET /build-warnings.txt             → 有问题才是 200；无问题应 404
```

---

## 4. 最终验收（Definition of Done）

- [ ] `grep -rn 'git add \.\|git add -A\|git add --all' .github/` 无匹配
- [ ] 4 条 workflow 的 `uses:` 全为 40 位 sha；`permissions:` 与 SPEC-WORKFLOWS §3 表一致、`on:` 与原版逐字一致（§6 checklist）
- [ ] `validate.yml`（doctor）在 PR 与 push 上运行，人为破坏数据会红
- [ ] 工具代码/测试/requirements/ruff/mypy/coveragerc **已从本仓删除**，`git grep 'python build_pages.py'` 无结果
- [ ] `docs/index.md` 为脚本文档索引，迁出文档的链接为绝对 URL 指向工具仓
- [ ] 站点冒烟 6 项全绿；`BASELINE` 中的 N 个安装链接数未减少
- [ ] `registry.json` 的 `git log` 在切换期间只有工具产生的正常变更（无手工编辑）

---

## 5. 故障排查表

| 症状 | 可能原因 | 定位动作 |
|---|---|---|
| 回帖 403 / `gh workflow run` 403 | `permissions` 缺项（见 SPEC §3 表） | 对照表逐项核；三次历史事故：sync 缺 `discussions: write`、deploy 缺 `discussions: read`、cleanup 缺 `actions: write` |
| push 被拒 `fetch first` | 远端有新提交（并发） | workflow 已串行组；重跑即可，**不要 force push** |
| 命令回帖成功但仓库没变 | `changed` 判定漏了某个写入路径 | 看 Action output `changed`；核对白名单是否含该路径 |
| 版本帖没生成 | `discussions: write` 缺失 或 `node(id)` 查询失败 | 看 `project` 的 `result`；工具仓跑 `usm doctor` |
| 详情页版本切换消失（回退 Issue 面板） | `discussions: read` 缺失 → 拉取失败 | 部署产物根目录看 `build-warnings.txt`（有问题才存在） |
| 站点没更新 | push 由 `GITHUB_TOKEN` 发出**不触发** workflow | 必须 `gh workflow run deploy-pages.yml`；检查第⑤步 |
| `git status` 出现预期外文件 | `git add .` 回归 | 立即 revert；按 SPEC §4 白名单改 |
| registry 出现预期外大幅 diff（格式/转义全变且不稳定） | Go JSON 序列化未按 I-2 实现（序列化格式不稳定） | **停机**：回滚工具版本，修 `SetEscapeHTML(false)` 与序列化格式稳定性（`Load→Save` 空改动字节不变） |
| Action 下载失败/sha 不匹配 | release 与 `action.yml` 内置版本不同步 | 回 pin 上一 sha；工具仓 release CI 的同步步骤是根因 |
| 空跑一次想验证清理逻辑 | 误用 `apply: true` | 清理默认必须 dry-run；只有 `cleanup-panel.yml` 传 `apply: true` |

---

## 6. 观察指标（切换观察期记录到 `BASELINE.md` 或 issue）

1. 每次命令运行的 `changed` 与实际 `git status` 一致率（目标 100%）
2. 站点冒烟 6 项通过率（目标 100%）
3. Action 运行时长 P50/P95（v0 Python 版 vs v1 Go 版对比，验证拆仓是否值得）
4. 工具仓测试与快照全绿次数（连续 3 次为切换 v1 的硬门槛）
