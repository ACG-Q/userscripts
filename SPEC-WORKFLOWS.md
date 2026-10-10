# SPEC · 内容仓 workflow（薄壳形态的完整规格）

> 终态形态：门禁删评、执行回帖、站点搬移、数据自检等业务逻辑全部收进
> `acg-q/userscript-console` 的 usm action（设计 D7）；本仓 workflow 只保留
> `on:` / `permissions:` / `concurrency` / `timeout-minutes` 与两类胶水步骤
> （白名单 git 提交、`gh` 派发/兜底回帖）。
> **文件名保持不变**——`gh workflow run <filename>.yml` 引用（`deploy-pages.yml` 等）不得因改名失效。

---

## 0. 通用约定（每条 workflow 都要有）

```yaml
runs-on: ubuntu-latest
timeout-minutes: 15          # 沿用现值；deploy: build=10/deploy=5、cleanup=10、validate=5
concurrency:
  group: <沿用现值>          # issue-commands / pages / scheduled-sync / cleanup-panel
  cancel-in-progress: false  # 业务 workflow 串行排队，保证最终状态 = 最新提交（validate 例外 true）
uses: acg-q/userscript-console@<pin>   # 内容仓 pin 策略见 §5
```

五条纪律（**评审 checklist**）：

1. `permissions` 只列本条需要的（见 §2 对照表）；
2. `git add` **只用路径白名单**，禁止 `.`/`-A`/`--all`（§3）；
3. 失败路径必须让 job 变红（步骤以非 0 退出码失败）；带评论上下文的 `issue-commands.yml`
   必须保留 `!cancelled()` 兜底回帖步骤（§4）；
4. `GITHUB_TOKEN` 的 push 不触发 workflow → 需要重建站点时
   `gh workflow run deploy-pages.yml`（一步 shell，见各骨架）；
5. **业务逻辑零内联**：门禁删评（input `comment-id`）、执行回帖（`post-reply`）、
   站点搬移（`pages-out`）、数据自检（`command: doctor`）一律走 usm action 的
   input/output；workflow 的 `run:` 只允许白名单 git 提交与 `gh` 胶水两类。

---

## 1. 六条 workflow 终态（`on:` / `permissions:` / `concurrency` 逐字不动）

### 1.1 `issue-commands.yml`（命令执行——完整骨架，与工具仓 SPEC-ACTION §3.1 同 PR 同步）

```yaml
name: Issue Commands Manager

on:
  issue_comment: { types: [created] }
permissions:
  contents: write
  issues: write
  actions: write
  discussions: write
concurrency:
  group: issue-commands
  cancel-in-progress: false

jobs:
  execute:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    # 仅命令面板 Issue #1、排除 PR 评论
    if: ${{ !github.event.issue.pull_request && github.event.issue.number == 1 }}
    steps:
      - uses: actions/checkout@v5

      # 门禁删评 + 执行 + 结果回帖都在 action 内（comment-id / post-reply）
      - name: Run command
        id: cmd
        uses: acg-q/userscript-console@<pin>
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: ${{ github.event.comment.body }}
          comment-user: ${{ github.event.comment.user.login }}
          comment-id: ${{ github.event.comment.id }}
          issue-number: ${{ github.event.issue.number }}
          post-reply: 'true'
          use-binary: true

      # 投影对账（命令可能改了 registry）
      - name: Project issues
        id: proj
        if: steps.cmd.outputs.authorized == 'true'
        uses: acg-q/userscript-console@<pin>
        with:
          command: project
          github-token: ${{ secrets.GITHUB_TOKEN }}
          use-binary: true

      # 提交（路径白名单；changed=false 时整步跳过）
      - name: Commit changes
        id: commit
        if: ${{ !cancelled() && steps.cmd.outputs.authorized == 'true' && steps.cmd.outputs.changed == 'true' && steps.cmd.outcome == 'success' }}
        run: >-
          git config user.name "github-actions[bot]" &&
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com" &&
          git add registry.json scripts dist archive &&
          (git diff --staged --quiet ||
          (git commit -m "Apply command: ${{ github.event.comment.user.login }}" && git push))

      # 派发站点部署（GITHUB_TOKEN push 不触发 workflow，需显式派发）
      - name: Trigger site deploy
        id: deploy
        if: ${{ !cancelled() && steps.commit.outcome == 'success' }}
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: gh workflow run deploy-pages.yml

      # 失败也回帖（逐字沿用现规范）
      - name: Reply to comment
        if: ${{ !cancelled() && (steps.cmd.outcome == 'failure' || steps.proj.outcome == 'failure' || steps.commit.outcome == 'failure' || steps.deploy.outcome == 'failure') }}
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: |
          gh issue comment ${{ github.event.issue.number }} \
            -R ${{ github.repository }} \
            --body "⚠️ 执行/提交/派发环节失败，请查看 Actions 日志"
```

**验收**：① `/list` → 正常回帖、无提交（changed=false 跳过 Commit）；② `/add <code>` →
registry+scripts+dist 三处 diff、回帖含 ID、部署被派发；③ 非拥有者评论 → 被删除
（`comment-id` 删评）、无回帖、Commit/Deploy 跳过。

### 1.2 `deploy-pages.yml`（构建 + 搬移 + 部署）

- `assemble` 步骤已由 action input `pages-out: _site` 收编（`usm build --pages-out`，
  语义同旧站点组装：`*.user.js` → `_site/<dist 段>/`，其余 → `_site/`，搬后 dist 清空）。
- `build` 步骤后仍接 `actions/configure-pages@v6` → `upload-pages-artifact`（`path: ./_site`）
  → `deploy-pages`，两 job 结构与 `if` 条件逐字不变。

```yaml
      - name: 构建站点 / Build site
        id: build
        uses: acg-q/userscript-console@<pin>
        with:
          command: build
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pages-out: _site
          use-binary: true

      - uses: actions/configure-pages@v6
      - uses: actions/upload-pages-artifact@v4
        with: { path: ./_site }
```

**验收**：站点三件套可访问（`index.html` / `scripts.json` / `commands/page-1.html`）；
`build` 失败 → job 红（不得被 `|| true` 掩盖）。

### 1.3 `sync-scheduled.yml`（定时/手动同步）

- `/sync-all` 以仓库拥有者名义注入（`comment-user: ${{ github.repository_owner }}`）；
- **`post-reply: 'false'`**：schedule 无评论上下文，不回帖（原版也无回帖步骤）；
- 提交与派发为内联胶水（原独立提交/派发脚本已删，设计 §3.5）：

```yaml
      - name: Run /sync-all
        id: cmd
        uses: acg-q/userscript-console@<pin>
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: /sync-all
          comment-user: ${{ github.repository_owner }}
          issue-number: '1'
          post-reply: 'false'
          use-binary: true

      - name: Project issues
        id: proj
        uses: acg-q/userscript-console@<pin>
        with: { command: project, github-token: '${{ secrets.GITHUB_TOKEN }}', use-binary: true }

      - name: Commit changes
        id: commit
        if: ${{ steps.cmd.outputs.changed == 'true' }}
        run: >-
          git config user.name "github-actions[bot]" &&
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com" &&
          git add registry.json scripts dist &&
          (git diff --staged --quiet ||
          (git commit -m "chore: 同步第三方脚本" && git push))

      - name: Trigger site deploy
        if: ${{ steps.commit.outcome == 'success' }}
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: gh workflow run deploy-pages.yml
```

**验收**：dispatch 后 `registry.json` 中 `last_synced_at` 更新；无变化时
`changed=false` → 提交与派发整步跳过。

### 1.4 `cleanup-panel.yml`（定期清理归档）

- `apply`/`keep` 归一改为**表达式直传**（原输入归一脚本已删，设计 §3.5）：
  `apply: ${{ github.event_name == 'schedule' || inputs.apply }}`、
  `keep: ${{ inputs.keep || '10' }}`——定时触发固定 `apply=true`，手动触发默认 dry-run；
  ⚠️ `inputs.apply` 是**布尔值**，禁止写 `== 'true'`：类型不匹配时 GH 转数字比较
  （`1 == NaN` 恒 false），手动触发 apply=true 会被误判成 dry-run；
- `workflow_dispatch` 的 `apply`/`keep` 两个 input、`fetch-depth: 0`（归档累积文件，
  浅克隆 push 被拒）**逐字保留**；
- 提交（白名单 `archive`）与派发为内联胶水（同 1.3 模式，message 为
  `chore(archive): 归档命令面板历史评论`）。

```yaml
      - name: Archive and clean / 归档与清理
        id: clean
        uses: acg-q/userscript-console@<pin>
        with:
          command: cleanup
          github-token: ${{ secrets.GITHUB_TOKEN }}
          keep: ${{ inputs.keep || '10' }}
          apply: ${{ github.event_name == 'schedule' || inputs.apply }}
          use-binary: true
```

**验收**：
- dispatch（不传 apply）→ dry-run，`changed=false` → 提交/派发跳过；
- dispatch 且 `apply=true` → 真删超期评论 + 提交 `archive/commands.json` + 派发部署；
- 定时触发 → 固定 `apply=true`、`keep=10`。

### 1.5 `validate.yml`（数据自检）

- registry 结构自检收编进 `usm doctor --check`（原独立校验脚本已删，覆盖 registry 结构与
  schema 版本、源码/dist/归档一致性，见 SPEC-DATA §6）；
- GraphQL schema 校验归属工具仓（其 CI 同类校验），本仓副本删除（设计 §3.5）；
- `permissions: contents: read`、`cancel-in-progress: true` 逐字不变。

```yaml
      - uses: actions/checkout@v5
      - name: 数据一致性自检 / Data doctor
        uses: acg-q/userscript-console@<pin>
        with:
          command: doctor
          github-token: ${{ secrets.GITHUB_TOKEN }}
          use-binary: true
```

### 1.6 `init-command-panel.yml`（一次性建面板）

- **唯一保留脚本** `tools/init_panel.py`（幂等：Issue #1 已存在则跳过），
  逐字不变：`checkout` → `python tools/init_panel.py`（设计 §3.5 留）。

---

## 2. 权限对照表（改权限前必过此表）

| workflow | 需要的 permissions | 用途（漏了会怎样） |
|---|---|---|
| `issue-commands.yml` | `contents: write`（提交）`issues: write`（回帖/`comment-id` 删评）`actions: write`（派发部署）`discussions: write`（版本帖发布） | 缺 contents → push 403；缺 issues → 无法回帖/删评论；缺 actions → `gh workflow run` 403；缺 discussions → **createDiscussion 403 被吞，版本帖静默丢失**（真实事故） |
| `deploy-pages.yml` | `contents: read` `pages: write` `id-token: write` `issues: read`（统计）`discussions: read`（版本帖评论拉取） | 缺 discussions: read → 详情页版本切换回退到 Issue 面板（真实事故） |
| `sync-scheduled.yml` | `contents: write` `issues: write` `actions: write` `discussions: write` | 同上两条 |
| `cleanup-panel.yml` | `contents: write` `issues: write` `actions: write` | 缺 actions → 归档后站点不自动刷新（真实事故） |
| `init-command-panel.yml` | `issues: write`（建面板）`contents: read`（checkout 读 `tools/init_panel.py`） | 缺 issues → 无法建面板；缺 contents → checkout 失败 |
| `validate.yml` | `contents: read` | — |

> **每次改权限都要在 PR 描述里引用本表**；三次真实 403 事故（sync discussions、deploy
> discussions read、cleanup actions）都源于此。

---

## 3. 提交路径白名单（防误提交/漏提交）

| 场景 | `git add` |
|---|---|
| 命令执行后 | `registry.json scripts dist archive` |
| 同步后 | `registry.json scripts dist` |
| 清理归档后 | `archive` |
| **禁止** | `.`、`-A`、`--all`（会把无关工作区状态推上去） |

> 白名单由各 workflow 的**内联 git 步骤**执行（原独立提交脚本已删，设计 §3.5）：固定
> `github-actions[bot]` 身份 + `git diff --staged --quiet` 兜底防空提交。
> `changed == 'true'` 作为提交步骤的前置条件（outputs 短路），两道防线都要保留。

---

## 4. 回帖契约

| 场景 | 归属 | 行为 |
|---|---|---|
| 执行结果回帖 | action `post-reply`（run-command，缺省 `'true'`） | `**执行结果：**\n<result>` 回到触发 Issue；回帖失败仅 warning，不改退出码 |
| 未授权删评 | action `comment-id`（run-command） | 门禁未授权 → 自动删除该评论；**不回帖**；删除失败仅 warning |
| proj 摘要回帖 | **已删除（设计 D8）** | `project` 的 result 只进 Actions 日志，不再拼进回帖 |
| 定时同步 | `post-reply: 'false'`（sync 显式关闭） | schedule 无评论上下文，不回帖 |
| 失败兜底回帖 | workflow `!cancelled()` 步骤（仅 `issue-commands.yml`） | cmd/proj/commit/deploy 任一失败 → `gh issue comment` 告警 |

---

## 5. pin 策略与二进制零手填（v1.1.0+）

```yaml
# 内容仓（安全惯例）：显式 pin sha + 显式二进制版本
uses: acg-q/userscript-console@<40位commit-sha>
with:
  use-binary: true
  binary-version: '1.1.0'
  binary-sha256: '<64位十六进制，来自 release checksums.txt>'

# 零手填二进制（推荐，工具仓 v1.1.0+）：只需写 tag，版本+校验和自动推导
uses: acg-q/userscript-console@v1.1.2   # 精确版本 tag → 推导到对应 release
with:
  use-binary: true

# 零手填 + 大版本 tag（自动取最新 v1.x）
uses: acg-q/userscript-console@v1
with:
  use-binary: true
```

- 内容仓**安全惯例不变**：pin sha + 显式 `binary-version`/`binary-sha256`（收紧信任链）；
- **零手填模式**（`@v1.1.2` 或 `@v1` + `use-binary: true`）：工具仓从
  `github.action_ref` / GitHub API 自动推导版本与校验和，`checksums.txt` 为单一真源；
- bump pin = 单行改动的 PR，PR 描述贴工具仓 release notes 链接。

---

## 6. 每条 workflow 上线前的验收 checklist

- [ ] `permissions` 与 §2 表逐项一致
- [ ] `git add` 在 §3 白名单内（grep 无 `add .`/`-A`/`--all`）
- [ ] `timeout-minutes`、`concurrency.group` 与原版一致
- [ ] 触发器 `on:` 与原版**逐字**一致（含 `discussion_comment: [created]`、`if` 条件）
- [ ] 业务逻辑零内联：`run:` 只有白名单 git 提交与 `gh` 胶水（纪律 5）；带评论上下文
      的 workflow 保留 `!cancelled()` 兜底回帖
- [ ] `gh workflow run deploy-pages.yml` 文件名未因改名失效
- [ ] 真实事件端到端跑通一次（见各节「验收」）
- [ ] `git status` 在运行后只出现预期路径
