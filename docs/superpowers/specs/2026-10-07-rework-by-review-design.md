# 设计 · 按审查清单重修 project-06（重新开发）

> 日期：2026-10-07
> 范围：`project-06` 两仓——`userscript-console`（Go 工具仓 / composite Action）与 `userscripts`（内容仓）
> 基准：`C:\Users\LiuJi\Desktop\projec-02`（Python 成熟参考实现，24 测试文件、golden、7 UI specs）
> 验收：二次全面复审判定"可合并"
> 约束：**不开子代理**（批次 5 复审若属技能流程所需，先向用户确认）

---

## 1. 背景与目标

2026-10-07 的三并行分层审查判定 project-06 **不可合并**：53 个代码问题 + 12 项与 projec-02 的功能差异，共 65 项。已知严重度分布为 3 Critical、13 Important、17 Minor（合计 33，与 53 差 20 项，原报告构成不可考——批次 0 重建时须复核归类并以重建结果为准）。其中 C2（cleanup 先删后归档）为每日 cron 触发的静默数据丢失，C3（站点绝对根路径链接）使 Pages 子路径下导航全失效。

审查清单当时未落盘，65 项完整明细只存在于会话记忆（17 Minor 与部分 Important 细节不可考）。

**目标**：
1. 重建并落盘完整问题清单，作为全程可勾销的唯一基准
2. 按严重度分批修复全部 65 项，每批过 CI 门禁
3. 以二次全面复审"可合并"为完成定义

**明确不做**：不重构已稳定架构；不回退 GreasyFork v1.1.2 抓取修复；不追求与 projec-02 字节级一致；不引入新第三方依赖（若确需，按 AGENTS.md §3 先行说明许可证与维护状态）。

## 2. 决策记录

| # | 决策 | 选项 |
|---|---|---|
| D1 | 按严重度分批串行（批次 0-5） | 否决按模块分批（Critical 分散在多层，数据丢失风险不能最先消除）；否决多路并行（冲突与返工风险） |
| D2 | 全量修复：53 问题 + 12 功能差异 | 否决只修 Critical+Important；否决功能差异后置 |
| D3 | 验收 = 二次全面复审判"可合并" | 否决仅清单勾销+CI 绿；否决分批即时复审 |
| D4 | **不开子代理**，全部顺序执行 | 用户指令，覆盖技能默认的并行建议 |
| D5 | 规格落 `userscripts/docs/superpowers/specs/` | 沿用 2026-10-06 既有惯例（project-06 根目录非 git 仓） |

## 3. 批次划分与门禁

| 批次 | 内容 | 产出 |
|---|---|---|
| 0 基线重建 | 我顺序跑三轮分层审查（数据源层 / 命令·数据层 / CI·站点层），65 项落盘并复核 53=3+13+17+… 的构成差异 | `docs/reviews/2026-10-07-baseline.md`：编号（C/I/M/F + 序号）、文件位置、描述、状态列 |
| 1 Critical | C1 复核、C2 归档语义、C3 站点链接 | 两仓各一 commit，CI 绿 |
| 2 Important | 13 项，四波顺序推进 | 每波独立 commit，CI 绿 |
| 3 Minor | 17 项复核后修（已被覆盖的直接勾销） | 小步 commit，CI 绿 |
| 4 功能差异 | 12 项按 projec-02 对照表移植 | 对照表全勾销 + 测试/快照 |
| 5 复审 | requesting-code-review 二次全面复审 | 判定"可合并" |

**每批固定门禁**：对应测试全绿 → 工具仓 `go test` 覆盖 ≥90% + `snapshot check` + `go vet` + gofmt → 内容仓 `python -m unittest discover tools/tests -q` + `python tools/validate_workflows.py` → 提交推送 → 远端 CI 绿 → 勾销清单状态列 → 才进下一批。

**提交纪律**：每批/每波独立 commit，禁止跨批混合；中文 conventional commits；`userscripts/README.md` 是预存改动，**永不提交**；批间隙用 `git status` 核对工作树。

**未提交改动盘点**（批次 0 执行）：
- `userscript-console/action.yml`（C1 修复，未提交）→ 归批次 1
- `userscripts/SETUP.md`（C1 文档，未提交）→ 归批次 1
- `userscripts/README.md` → 不提交

## 4. 批次技术要点

### 4.1 批次 1（Critical）

- **C2**：`userscript-console/internal/cleanup/cleanup.go` 的 `MergeArchive`（对照 `SPEC-DATA.md:103`、`projec-02/panel_cleanup.py`）。改为**先写归档（原子写：临时文件 + rename）、确认成功后再删评论**；任一步失败则不删、报错返回，不吞异常。单测覆盖：归档失败时评论不被删除；正常路径顺序正确。测试名如 `test_merge_archive_failure_keeps_comments`。
- **C1**：`action.yml` 的 owner/repo 拆分推导已改，批次 1 内本地模拟 `GITHUB_REPOSITORY` 两形态验证输出 `https://<owner>.github.io/<repo>`。
- **C3**：以**生成产物**验收——重新生成站点，HTML 内 grep 所有 `href` 相对可达、`scripts.json` 结构正常、`CUTOVER.md:93-95` 冒烟项全过；不以"源码改过了"为准。

### 4.2 批次 2（Important，四波顺序，波内独立项可顺次做）

1. **CI 门禁波**：I1 工具仓测试+覆盖率入发布前置；I2 GraphQL schema 校验（放 `userscripts/tools/`，与 `validate_workflows.py` 同层）；I3 golangci-lint 接入 CI。
2. **失败可观测波**：I4 project 步骤失败不阻断 registry 提交的语义修正；I5 回帖如实上报提交/触发失败。改 Python 工具 + 测试，修完人为制造失败路径验证回帖确实报错。
3. **安全波**：I6 面板 Issue #1 初始化保障；全部 `uses:` 从 tag 改 commit SHA pin；release 加门禁。
4. **站点正确性波**：I7 站点功能缺口补齐或文档显式声明裁剪；I8 markdown 消毒对齐 D-04；I9 评论正文去双重处理；I10 首页 JS TypeError；I11 命令页快照补测。

（I12/I13 以批次 0 重建清单为准补入对应波。）

### 4.3 批次 3（Minor）

先与批次 1/2 已修项比对复核，被顺带修复的直接勾销；余项逐条小步修复，每项独立 commit。

### 4.4 批次 4（功能差异）

- 基线清单每项 F 必须附 **projec-02 源文件:行号** 作为移植依据；实现按对照表逐项进行。
- 站点 10 项缩水：对照 `projec-02/build_pages.py` + UI specs，Go 移植保持 `internal/pages` 模板体系，每项配 golden 快照；快照基线刷新需人工过目 diff。
- 结构性差异（GraphQL schema 校验等）：纯标准库实现优先；新依赖须先按 AGENTS.md §3 说明。

## 5. 测试与错误处理

- 每项修复/功能覆盖正常、边界、错误三路径；测试名描述行为；不使用 `skip/only`。
- 站点改动一律以生成产物为验收对象（HTML grep、`scripts.json` 结构）。
- 新增/改动代码不吞异常：捕获必记 warning 以上日志并返回明确错误；CI 步骤失败必须使 job 失败，不用 `continue-on-error` 掩盖。
- 工具仓注入 fake 隔离网络副作用（沿用既有模式）；真实网络验证走代理 `HTTPS_PROXY=http://127.0.0.1:7897`。

## 6. 回滚与风险

- 任一批 CI 红 → 只回滚该批 commit，不牵连已完成批次。
- C2 影响每日 cron → 批次 1 先本地 fixture 跑通全链路再推。
- 快照批量刷新可能掩盖回归 → diff 逐文件人工过目。
- 二次复审翻出新问题 → 批次 5 预留缓冲；新问题按严重度决定追加小批或记录后置。
- 本机无 GitHub 凭证、API 按 IP 限流常耗尽 → 轮询优先 `webfetch`；`rate_limit.remaining>0` 时才用 PowerShell 直调。

## 7. 执行环境备忘

- PowerShell 5.1 坑：`go test -coverprofile=x.out` 须空格形式；`rg`/`Find-String` 不可用（用 grep 工具）；bash 风格 `&&`/`||`/heredoc 在 pwsh 中报错，脚本用单行或写临时 `.py` 文件执行。
- 环境变量与命令跨平台写法遵循 AGENTS.md §10。
