# SPEC · 内容仓 workflow（薄壳形态的完整规格）

> 蓝本：`userscript-manager@bff92c0` 的 6 个 workflow。
> **文件名保持不变**（`issue-commands.yml` 等）——PLAN 里的箭头是逻辑改造，不是重命名；
> 若最终决定改名，**必须同步所有 `gh workflow run <filename>.yml` 引用**（`issue-commands`/`sync`/`cleanup` 三处，见 §2.1⑤/§2.3/§2.4）。

---

## 0. 通用约定（每条 workflow 都要有）

```yaml
runs-on: ubuntu-latest
timeout-minutes: 15          # 保留现值；deploy: build=10/deploy=5、cleanup=10、validate=5
concurrency:
  group: <沿用现值>          # issue-commands / pages / scheduled-sync / cleanup-panel
  cancel-in-progress: false  # 业务 workflow 串行排队，保证最终状态 = 最新提交（不要改 true；validate 例外用 true，见 §1.2）
uses: acg-q/userscript-console@<40位sha>   # 内容仓一律 pin sha（§5）
```

四条纪律（**评审 checklist**）：
1. `permissions` 只列本条需要的（见 §3 对照表）；
2. `git add` **只用路径白名单**，禁止 `.`/`-A`（`cleanup` 也只 `archive/commands.json`，但历史教训下允许 `git add archive`）；
3. 失败路径必须有回帖/告警（`!cancelled()`、`set -euo pipefail`）；
4. `GITHUB_TOKEN` 的 push 不触发 workflow → 需要重建站点时 `gh workflow run deploy-pages.yml`。

---

## 1. 未接入 Action 的两条

### 1.1 `init-command-panel.yml` —— **完全不动**

保持现状：`workflow_dispatch` + `issues: write` + **刻意不 checkout**（`contents: none` 下 checkout 必失败，见其内注释）+ 用 `grep 404` 判定面板是否已存在。
**验收**：dispatch 两次，第二次应识别为「已存在」而不重复建 Issue #1。

### 1.2 `validate.yml` —— **新建**（替换原 `test.yml` 的数据侧职责）

```yaml
name: Validate
on: { push: { branches: [master] }, pull_request: {} }
permissions: { contents: read }
concurrency: { group: "validate-${{ github.ref }}", cancel-in-progress: true }
jobs:
  data:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@<sha>
      - name: registry 可解析且结构合法
        run: |
          python -c "import json,sys; d=json.load(open('registry.json',encoding='utf-8')); assert isinstance(d.get('scripts'),list); [(_ for _ in ()).throw(SystemExit('缺 id/type: '+str(s))) for s in d['scripts'] if not s.get('id') or s.get('type') not in ('self','synced')]"
      - name: 数据一致性（doctor）
        uses: acg-q/userscript-console@<sha>
        with: { command: doctor, github-token: "${{ secrets.GITHUB_TOKEN }}" }
```
> 代码级门禁（ruff/mypy/coverage/snapshot）**不在此仓**，属工具仓；迁移期可临时并存，阶段 4 删除（PLAN U4-3）。

---

## 2. 四条薄壳 workflow（完整规格）

### 2.1 `issue-commands.yml`（命令执行）

```yaml
name: Issue Commands Manager
on:
  issue_comment: { types: [created] }
permissions: { contents: write, issues: write, actions: write, discussions: write }
concurrency: { group: issue-commands, cancel-in-progress: false }

jobs:
  execute:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    # 逐字保留：仅命令面板 Issue #1、排除 PR 评论
    if: ${{ !github.event.issue.pull_request && github.event.issue.number == 1 }}
    steps:
      # ① 第一道门禁（最小权限原则：先比较再执行；未授权直接删评论）
      - name: Permission gate
        id: gate
        env:
          COMMENT_USER: ${{ github.event.comment.user.login }}
          REPO_OWNER: ${{ github.repository_owner }}
        run: |
          if [ "$COMMENT_USER" == "$REPO_OWNER" ]; then
            echo "authorized=true" >> "$GITHUB_OUTPUT"
          else
            echo "authorized=false" >> "$GITHUB_OUTPUT"
            gh api -X DELETE "repos/${{ github.repository }}/issues/comments/${{ github.event.comment.id }}"
          fi

      - uses: actions/checkout@<sha>
        if: steps.gate.outputs.authorized == 'true'

      # ② 执行命令（第二道门禁在工具内复核 comment-user == repo-owner）
      - name: Run command
        id: cmd
        if: steps.gate.outputs.authorized == 'true'
        uses: acg-q/userscript-console@<sha>
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: ${{ github.event.comment.body }}   # 经 input→env 传递，绝不内插 shell
          comment-user: ${{ github.event.comment.user.login }}
          issue-number: ${{ github.event.issue.number }}

      # ③ registry → Issues/版本帖 对账（命令可能改了 registry）
      - name: Project issues
        id: proj
        if: steps.gate.outputs.authorized == 'true'
        uses: acg-q/userscript-console@<sha>
        with: { command: project, github-token: "${{ secrets.GITHUB_TOKEN }}" }

      # ④ 提交（⚠️ 路径白名单；changed=false 时不提交）
      - name: Commit changes
        id: commit
        if: steps.gate.outputs.authorized == 'true' && steps.cmd.outputs.changed == 'true'
        run: |
          set -euo pipefail
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add registry.json scripts dist archive
          if git diff --staged --quiet; then
            echo "committed=false" >> "$GITHUB_OUTPUT"
          else
            git commit -m "Apply command: ${{ github.event.comment.user.login }}"
            git push
            echo "committed=true" >> "$GITHUB_OUTPUT"
          fi

      # ⑤ GITHUB_TOKEN push 不触发 → 显式派发部署
      - name: Trigger site deploy
        if: steps.gate.outputs.authorized == 'true' && steps.commit.outputs.committed == 'true'
        env: { GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: |
          gh workflow run deploy-pages.yml -R ${{ github.repository }} \
            || echo "⚠️ 站点部署派发失败（不阻断），可手动触发" 

      # ⑥ 失败也回帖（逐字沿用现规范）
      - name: Reply to comment
        if: ${{ !cancelled() && steps.gate.outputs.authorized == 'true' }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          RESULT: ${{ steps.cmd.outputs.result }}
          PROJ: ${{ steps.proj.outputs.result }}
          CMD_OK: ${{ steps.cmd.outcome }}
        run: |
          set -uo pipefail
          if [ -n "$RESULT" ]; then BODY="$RESULT"; else BODY="操作完成"; fi
          if [ "$CMD_OK" != "success" ] && [ "$CMD_OK" != "skipped" ]; then
            BODY="⚠️ 命令执行失败（Run command: $CMD_OK），请查看本次运行日志。"$'\n\n'"$BODY"
          fi
          if [ -n "$PROJ" ]; then BODY="$BODY"$'\n\n'"$PROJ"; fi
          gh issue comment "$ISSUE_NUMBER" -R ${{ github.repository }} \
            --body "**执行结果：**"$'\n'"$BODY"
```

**验收**：① `/list` → 正常回帖、`committed=false`（无改动）；② `/add <code>` → registry+scripts+dist 三处 diff、回帖含 ID、站点重建；③ 非拥有者评论 → 被删除、无回帖。

### 2.2 `deploy-pages.yml`（构建 + 部署）

```yaml
name: Deploy to GitHub Pages
on:
  push: { branches: [master] }
  issues: { types: [opened, edited, closed, reopened] }
  issue_comment: { types: [created, edited, deleted] }
  discussion_comment: { types: [created] }   # 版本帖新评论 → 重建（一条评论只触发一次）
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write, issues: read, discussions: read }
concurrency: { group: pages, cancel-in-progress: false }

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    # 逐字保留：命令面板 #1 的动态不进站点；discussion_comment 无 issue 上下文需显式放行
    if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'discussion_comment' || github.event.issue.number != 1 }}
    steps:
      - uses: actions/checkout@<sha>
      - name: Build site
        uses: acg-q/userscript-console@<sha>
        with: { command: build, github-token: "${{ secrets.GITHUB_TOKEN }}" }
      # ── 以下 _site 组装逐字保留（Pages 特有，属本仓） ──
      - name: Stage site structure
        run: |
          set -euo pipefail
          mkdir _site
          mv dist/* _site/
          mkdir _site/dist
          find _site -maxdepth 1 -name '*.user.js' -exec mv -t _site/dist {} +
      - uses: actions/configure-pages@<sha>
      - uses: actions/upload-pages-artifact@<sha>
        with: { path: ./_site }

  deploy:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 5
    environment: { name: github-pages, url: "${{ steps.d.outputs.page_url }}" }
    steps:
      - id: d
        uses: actions/deploy-pages@<sha>
```

**验收**：站点三件套可访问（`index.html` / `scripts.json` / `commands/page-1.html`）；版本帖评论后 ~30s 重建；`build` 失败 → job 红（不得被 `|| true` 掩盖）。

### 2.3 `sync-scheduled.yml`（定时/手动同步）

```yaml
name: Scheduled Sync
on:
  workflow_dispatch:
  # schedule: { cron: '0 3 * * 1' }   # 沿用现状：默认注释、手动触发
permissions: { contents: write, issues: write, actions: write, discussions: write }
concurrency: { group: scheduled-sync, cancel-in-progress: false }
jobs:
  sync-all:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<sha>
      - name: Run /sync-all        # 身份注入与原版一致：以仓库拥有者名义执行
        id: cmd
        uses: acg-q/userscript-console@<sha>
        with:
          command: run-command
          github-token: ${{ secrets.GITHUB_TOKEN }}
          comment-body: /sync-all
          comment-user: ${{ github.repository_owner }}
          issue-number: '1'
      - name: Project issues
        id: proj
        uses: acg-q/userscript-console@<sha>
        with: { command: project, github-token: "${{ secrets.GITHUB_TOKEN }}" }
      - name: Commit changes
        run: |
          set -euo pipefail
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add registry.json scripts dist
          if git diff --staged --quiet; then echo "无更新"; else
            git commit -m "chore: 同步第三方脚本"; git push; echo "pushed=true" >> "$GITHUB_OUTPUT"
          fi
        id: commit
      - name: Trigger site deploy
        if: steps.commit.outputs.pushed == 'true'
        env: { GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: |
          gh workflow run deploy-pages.yml -R ${{ github.repository }} \
            || echo "⚠️ 派发失败（不阻断）"
```
**验收**：dispatch 后 `registry.json` 中 `last_synced_at` 更新；无变化时输出「无更新」且不提交。

### 2.4 `cleanup-panel.yml`（定期清理归档）

> 实现说明（与原文的差异，均为**安全性增强**，不改变归档语义）：
> - `workflow_dispatch` 增加 `apply`（boolean，默认 **false**）与 `keep`（string，默认 `'10'`）两个 input；
>   **手动触发默认 dry-run**，只有显式传 `apply=true` 才真删评论。定时触发仍固定 `apply=true`。
> - `apply` / `keep` 由一个 `id: cfg` 的前置步骤按触发来源算出，避免把表达式散落在多处。
> - `actions/checkout` 加 `fetch-depth: 0` —— 归档是累积文件，浅克隆下 `git push` 会被拒（fetch first）。
> - 提交步骤加 `id: commit`，仅在 Action 的 `changed == 'true'` 时执行；
>   部署派发进一步以 `committed == 'true'` 为条件 —— 没有归档变更就不重建站点。
> - 末尾加 `if: always()` 的汇总步骤，打印触发来源 / changed / committed / result，便于事后核对。

```yaml
name: Cleanup Command Panel
on:
  schedule:
    - cron: '0 3 * * *'
  workflow_dispatch:
    inputs:
      apply:
        description: 'true=真正删除超期评论；false=dry-run 只体检（默认 dry-run，更安全）'
        type: boolean
        default: false
      keep:
        description: '每个命令组保留的最近评论数'
        type: string
        default: '10'
permissions: { contents: write, issues: write, actions: write }
concurrency: { group: cleanup-panel, cancel-in-progress: false }
jobs:
  cleanup:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@<sha>
        with: { fetch-depth: 0 }

      - name: 清理输入（记录本次口径，便于事后核对）
        id: cfg
        run: |
          set -euo pipefail
          # 手动触发用 input（默认 dry-run）；定时触发固定 apply=true
          # ... 输出 apply / keep 到 $GITHUB_OUTPUT

      - name: Archive and clean
        id: clean
        uses: acg-q/userscript-console@<sha>
        with:
          command: cleanup
          github-token: ${{ secrets.GITHUB_TOKEN }}
          keep: ${{ steps.cfg.outputs.keep }}
          apply: ${{ steps.cfg.outputs.apply }}

      - name: 提交归档
        id: commit
        if: steps.clean.outputs.changed == 'true'
        run: |
          set -euo pipefail
          git add archive
          if git diff --staged --quiet; then echo "committed=false" >> "$GITHUB_OUTPUT"
          else git commit -m "chore(archive): 归档命令面板历史评论"; git push; echo "committed=true" >> "$GITHUB_OUTPUT"; fi

      - name: 派发站点重建
        if: steps.commit.outputs.committed == 'true'
        env: { GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: gh workflow run deploy-pages.yml -R "${{ github.repository }}" || echo "::warning::派发失败"

      - name: 汇总
        if: always()
        run: echo "changed=${{ steps.clean.outputs.changed }} …"
```

**验收**：
- dispatch（不传 apply）→ dry-run，输出「无需清理」、`changed=false`、无提交、无部署派发；
- dispatch 且 `apply=true` → 真删超期评论 + 提交 `archive/commands.json` + 派发部署；
- dispatch 且 `keep` 调大到超过组内评论总数 → 不删任何评论（幂等键命中，`committed=false`）。

---

## 3. 权限对照表（改权限前必过此表）

| workflow | 需要的 permissions | 用途（漏了会怎样） |
|---|---|---|
| `issue-commands.yml` | `contents: write`（提交）`issues: write`（回帖/删未授权评论）`actions: write`（派发部署）`discussions: write`（版本帖发布） | 缺 contents → push 403；缺 issues → 无法回帖/删评论；缺 actions → `gh workflow run` 403；缺 discussions → **createDiscussion 403 被吞，版本帖静默丢失**（真实事故） |
| `deploy-pages.yml` | `contents: read` `pages: write` `id-token: write` `issues: read`（统计）`discussions: read`（版本帖评论拉取） | 缺 discussions: read → 详情页版本切换回退到 Issue 面板（真实事故） |
| `sync-scheduled.yml` | `contents: write` `issues: write` `actions: write` `discussions: write` | 同上两条 |
| `cleanup-panel.yml` | `contents: write` `issues: write` `actions: write` | 缺 actions → 归档后站点不自动刷新（真实事故） |
| `init-command-panel.yml` | `issues: write` | 缺 → 无法建面板 |
| `validate.yml` | `contents: read` | — |

> **每次改权限都要在 PR 描述里引用本表**；三次真实 403 事故（sync discussions、deploy discussions read、cleanup actions）都源于此。

---

## 4. 提交路径白名单（防误提交/漏提交）

| 场景 | `git add` |
|---|---|
| 命令执行后 | `registry.json scripts dist archive` |
| 同步后 | `registry.json scripts dist` |
| 清理归档后 | `archive` |
| **禁止** | `.`、`-A`、`--all`（会把无关工作区状态推上去） |

`changed=false` 时**跳过提交步骤**：`issue-commands.yml` 用 outputs 条件短路（§2.1④）；`sync`/`cleanup` 无 changed 短路，由步骤内 `git diff --staged --quiet` 兜底防空提交——两种防线都要保留，不要只留其一。

---

## 5. pin 策略

```yaml
uses: acg-q/userscript-console@<40位commit-sha>   # 内容仓（含本仓 workflow 互相引用第三方 action）
# 外部用户文档写法：
uses: acg-q/userscript-console@v1                 # 移动大版本 tag（工具仓 release CI 维护）
```
- 与本仓现有惯例一致（`actions/checkout@d23441a4…` 等已全 SHA pin）；
- bump pin = 单行改动的 PR，PR 描述贴工具仓 release notes 链接。

---

## 6. 每条 workflow 上线前的验收 checklist

- [ ] `permissions` 与 §3 表逐项一致
- [ ] `git add` 在 §4 白名单内（grep 无 `add .`/`-A`/`--all`）
- [ ] `timeout-minutes`、`concurrency.group` 与原版一致
- [ ] 触发器 `on:` 与原版**逐字**一致（含 `discussion_comment: [created]`、`if` 条件）
- [ ] 失败路径：`set -euo pipefail`；需要回帖的有 `!cancelled()`
- [ ] `gh workflow run deploy-pages.yml` 文件名未因改名失效
- [ ] 真实事件端到端跑通一次（见各节「验收」）
- [ ] `git status` 在运行后只出现预期路径
