# userscripts（现 `userscript-manager`）· 实施计划

> 单位：人日 = 1 人全职 1 天。每任务带 **ID / 产出 / 验收**，可直接派给 AI。
> 与 `../userscript-console/PLAN.md` 配对执行；阶段编号一一对应。

---

## 阶段 0 —— 原地准备（不建新仓、可独立回退，**建议立即执行**）

**目标**：把「改造内容仓」需要的前置一次性做完，且每一步都单独可 revert。

| ID | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| U0-1 | `issue-commands.yml` 的 `git add .` → `git add registry.json scripts dist archive`（审查项 M5/M9） | 白名单提交 | workflow 内 grep 无 `git add .`；真实跑一条 `/list` 后 `git status` 只含预期路径 | ✅ |
| U0-2 | `sync-scheduled.yml` 同样收窄（该仓当前是 `git add .`） | 同上 | 同上 | ✅ |
| U0-3 | 写 `docs-ownership.md`：按 `README §2` 表列出「迁出/保留」路径，**与工具仓 `README §6` 目录规划互为镜像** | 迁移清单 | 两份清单无重叠、无遗漏（脚本核对：`comm -3 <(…) <(…)`） | ✅ |
| U0-4 | `README.md` 顶部加「工具已迁往 `acg-q/userscript-console`」占位段（阶段 2 后填真实链接） | 用户导航占位 | 链接语法正确 | ✅ |
| U0-5 | 新增 `validate.yml`（骨架先只做 registry JSON 可解析检查） | 数据守门 workflow | 推送后绿；故意写坏 `registry.json` 分支会红（本地验证） | ✅ |
| U0-6 | 记录**迁移前基线**：`git rev-parse HEAD`、Pages URL、存量安装链接数（`grep -c 'downloadURL' dist/*.user.js`） | `BASELINE.md` | 三者入档，作为 CUTOVER 对比锚点 | ✅ |

**估计**：0.5–1 人日　**回退**：逐条 `git revert`。

---

## 阶段 1 —— 工具仓抽取（与工具仓 `C1-1` 同一个 PR 协调）

| ID | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| U1-1 | **确认迁出路径清单**（工具仓 `filter-repo` 参数的最终签字）：`console.py manager.py project_issues.py build_pages.py panel_cleanup.py pages_assets.py userscript_manager/ tests/ tools/ requirements.txt requirements-dev.txt ruff.toml mypy.ini .coveragerc docs/commands/ docs/design.md docs/code-review-2026-10-03.md` | 清单 v1（存 `docs-ownership.md`） | 与工具仓 `PLAN C1-1` 完全一致 | ✅ |
| U1-2 | **不改动本仓**：抽取是「新仓 clone + filter-repo」，本仓历史与文件原样保留 | — | 本仓 `git status` 干净、`git log` 未被改写 | ✅ |
| U1-3 | 同步评审：工具仓的 `tests/snapshot/` 快照基线与 `tests/fixtures/`、`tools/validate_graphql.py` 确实已在新仓可用 | 抽取完整 | 新仓 CI 首跑绿 | ✅ |
| U1-4 | 记录两仓基线 SHA 到 `BASELINE.md`（`tool@<sha>` / `content@<sha>`） | 可追溯起点 | 双仓 SHA 入档 | ✅ |

**估计**：0.5 人日　**风险**：`filter-repo` 必须在**克隆**上执行（`--source` 指向镜像），**绝不能在本仓原地跑**（会重写历史）。

---

## 阶段 2 —— workflow 切换为 `uses:`（**拆仓收益兑现点**）

**目标**：4 条业务 workflow 的逻辑步骤换成 Action 调用，Python 路径**保留在本仓**作为回退（阶段 4 才删）。

| ID | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| U2-1 | `issue-commands.yml` → `command.yml`（按 `SPEC-WORKFLOWS §2.1` 重写）：保留权限门禁、`concurrency`、`timeout`、路径白名单提交、`!cancelled()` 回帖 | 首条薄壳 | Issue #1 发 `/list`：回帖正常、`changed` 正确、只提交白名单路径 | ✅（Stage 0 已实现） |
| U2-2 | `deploy-pages.yml` → `deploy.yml`（`SPEC-WORKFLOWS §2.2`）：`command: build` → `_site` 组装 → `actions/deploy-pages`；触发器与 `if` 条件**逐字保留** | 首个站点构建 | Pages 上 `index.html`/`scripts.json`/`commands/page-1.html` 可访问；`build-warnings.txt` 语义不变 | ✅（Stage 0 已实现） |
| U2-3 | `sync-scheduled.yml` → `sync.yml`（`SPEC-WORKFLOWS §2.3`）：`command: run-command`（`comment-body: /sync-all`、`comment-user: ${{ github.repository_owner }}`）+ `project` + 提交 + `gh workflow run deploy-pages.yml` | 定时同步薄壳 | 手动 dispatch 一次：脚本同步、registry diff 正常、站点重建被派发 | ✅（Stage 0 已实现） |
| U2-4 | `cleanup-panel.yml` → `cleanup.yml`（`SPEC-WORKFLOWS §2.4`）：`command: cleanup`、`apply: true`、`keep: 10`，提交 `archive/commands.json`，再派发部署 | 清理薄壳 | 手动 dispatch：**当前 6 组 < 10 组 → 应输出「无需清理」且 `changed=false`**（不会误删） | ✅（Stage 0 已实现） |
| U2-5 | `init-command-panel.yml` **不接入**（保持原样，含「无 checkout」设计） | 不变 | dispatch 一次仍能正确识别 404/已存在 | ✅ |
| U2-6 | `validate.yml` 升级：`command: doctor`（`--check`）+ registry JSON 可解析 | 数据守门 | 故意制造孤儿源码目录 → CI 红 | ✅（Stage 0 已实现） |
| U2-7 | 全部切换后回填 `README.md` 的工具链接段（U0-4） | 完整导航 | 无占位词 | ✅（README 已更新） |

**切换单位**：一次一条 workflow，**每条独立 PR + 真实事件验证后再进下一条**（顺序 `command → deploy → sync → cleanup`）。表中 `→` 为**逻辑改造**，workflow 文件名保持现状（见 `SPEC-WORKFLOWS.md` 头注）；涉及 `gh workflow run` 一律用实际文件名（`deploy-pages.yml`）。

**估计**：1.5–2 人日　**回退**：单条 revert → 回到 Python 内联步骤（Python 代码此时尚在本仓）。

---

## 阶段 3 —— 运行观察（本仓侧的验收动作）

工具仓 Go 重构期间（10–16 人日），本仓只做**观察**，不加功能。

| ID | 任务 | 频率 | 验收 | 状态 |
|---|---|---|---|---|
| U3-1 | 每次 `command`/`sync` 运行后检查：`git diff --exit-code registry.json scripts dist`（构建幂等，无意外 diff） | 每次真实命令 | 连续 10 次无差异 | ⏳ 观察中 |
| U3-2 | 每次 `deploy` 后抽样冒烟：`index.html` 含 `commands/page-1.html` 链接、`scripts.json` 可取、目标详情页版本下拉存在 | 每次部署 | 冒烟清单（CUTOVER §3）全过 | ⏳ 观察中 |
| U3-3 | 每周跑一次 `cleanup` dry-run（`apply: false`），对比归档计数 | 每周 | 计数单调、无重复归档 | ⏳ 观察中 |
| U3-4 | 每次工具仓 release 后：确认 `action.yml` 的 version/sha 同步，再决定是否 bump pin | 每次 release | sha 校验通过 | ✅ 已验证 |

**退出条件**（全部满足才进阶段 4）：
- [ ] 工具仓测试与快照基线全绿（见工具仓 `MIGRATION` §4）
- [ ] U3-1 连续 10 次无 diff
- [ ] 无回滚请求

**估计**：0.5 人日（分散在 2–3 周观察期）

---

## 阶段 4 —— 瘦身与固化

| ID | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| U4-1 | 删除迁出路径（`U0-3` 清单中的全部项） | 本仓只剩数据 + workflow + 用户文档 | `git grep -l 'def main' -- '*.py'` 无结果；`tests/` 不存在 | ⏳ 待观察期结束后 |
| U4-2 | 删除 `requirements.txt`、`ruff.toml`、`mypy.ini`、`.coveragerc`；`.gitignore` 去掉测试相关条目 | 配置瘦身 | CI 不再 `pip install` | ⏳ 待观察期结束后 |
| U4-3 | `test.yml` → `validate.yml`（纯 `doctor` + registry 解析），**移除四道代码门禁**（它们已属工具仓） | 数据侧 CI | CI 时长 < 30s；故意破坏数据会红 | ✅（已在 Stage 0 实现） |
| U4-4 | `docs/` 落位：本仓 `docs/index.md` 改为**脚本文档索引**（链各脚本 README + 链工具仓命令文档）；确认站点导航 `文档` 链接指向本仓 `docs/index.md` | 文档导航正确 | 打开站点导航 `文档` → 落在本仓 docs | ✅（已在 Stage 0 实现） |
| U4-5 | 版本 pin 策略落档：所有 `uses:` 改为 commit-sha（外部用户文档给 `@v1` 用法） | 安全基线 | `grep -rn 'uses: acg-q/userscript-console@' .github` 全为 40 位 sha | ✅（已在 Stage 0 实现） |
| U4-6 | 更新 `README.md`：架构段改为「数据仓 + 工具仓」两段式；命令速查链到工具仓 | 面向用户 | 无失效链接 | ✅（已在 Stage 0 实现） |

**估计**：1–1.5 人日

---

## 里程碑与总账

| 里程碑 | 完成标志 | 累计人日 |
|---|---|---|
| **N0** | `git add` 白名单 + docs 清单 + BASELINE（可立即做） | 0.5–1 |
| N1 | 工具仓建立，本仓不受影响 | +0.5 |
| **N2** | 4 条 workflow 全部 `uses:` 化且回归通过 ← **主要收益兑现** | **+1.5–2** |
| N3 | 运行观察达标 | +0.5（跨 2–3 周） |
| N4 | 瘦身完成、CI <30s、pin 固化 | +1–1.5 |
| | **本仓合计** | **4–6 人日**（与工具仓并行，关键路径仍是工具仓的 15–21） |

---

## 风险登记

| ID | 风险 | 缓解 | 状态 |
|---|---|---|---|
| U-R1 | 仓名/URL 改变导致存量 `@downloadURL` 失效 | **DR-3 禁止改名**；U0-6 记录基线，CUTOVER 核对 | 已约束 |
| U-R2 | `filter-repo` 误在原仓执行重写历史 | 必须 `--source` 镜像/克隆执行（U1-2） | 开放（一次性操作） |
| U-R3 | 白名单漏路径 → 命令改动没提交（回帖说成功但真源没变） | `changed` 输出 + 白名单显式列出 `archive`（清理期）+ U2-1 验收包含 `git status` 检查 | 设计已覆盖 |
| U-R4 | Action 403（权限声明遗漏） | SPEC-WORKFLOWS §3 权限对照表；每次改权限必须过表 | 开放 |
| U-R5 | 站点构建失败但 workflow 绿 | `build` 失败必须让 job 失败（`set -euo pipefail`），部署 job `needs: build` | 设计已覆盖 |
| U-R6 | 观察期新旧实现行为漂移 | 工具仓行为测试与快照是唯一裁决；Python 仅作语义参照（DR-6）；本仓只做 U3 观察 | 开放 |
