# project-06 按审查清单重修 · 计划 1（批次 0-1）实现计划

> **面向 AI 代理的工作者：** 必需子技能：superpowers:executing-plans 逐任务实现此计划（**用户指令：禁止使用子代理**，不得改用 subagent-driven-development）。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 重建并落盘完整审查基线（65 项），然后修复全部 Critical（C1 PAGES_BASE、C2 cleanup 归档语义、C3 站点链接）。

**架构：** 批次 0 三轮顺序分层审查产出 `docs/reviews/2026-10-07-baseline.md` 勾销清单；批次 1 按 C2（TDD，先归档后删除 + 按 ID 幂等 + 保留最新 N 条）→ C1（验证已改的 owner/repo 推导）→ C3（模板链接全部改相对路径 + 首页命令归档导航）顺序修复，每步过工具仓 90% 覆盖率门禁。

**技术栈：** Go 1.x（tools 仓：`go test`/`go vet`/`gofmt`/`snapshot`）、Python 标准库 unittest（内容仓 tools）、Git Bash（验证 `action.yml` 的 bash 片段）。

**规格：** `docs/superpowers/specs/2026-10-07-rework-by-review-design.md`（D4：禁用子代理贯穿全程）

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `userscripts/docs/reviews/2026-10-07-baseline.md` | 创建 | 65 项勾销清单（编号/位置/描述/严重度/状态） |
| `userscript-console/internal/cleanup/cleanup.go` | 修改 | `MergeArchive`：按 ID 幂等 + 保留最新 Keep 条（旧→新落盘） |
| `userscript-console/internal/cleanup/cleanup_test.go` | 修改 | 幂等与保留语义的失败测试 |
| `userscript-console/internal/commands/cleanup.go` | 修改 | `saveArchive` 注入缝 + Apply 分支改为先存后删 |
| `userscript-console/internal/commands/cleanup_test.go` | 修改 | 先存后删两用例 + 强化既有弱断言 |
| `userscript-console/action.yml` | 修改（已改待验证） | PAGES_BASE 按 owner/repo 拆分推导 |
| `userscripts/SETUP.md` | 修改（已改待提交） | PAGES_BASE 示例改实际仓名 |
| `userscript-console/internal/pages/templates/{index,detail,commands,commands-index}.tmpl` | 修改 | 链接全部改相对路径；首页增命令归档导航 |
| `userscript-console/internal/pages/pages.go` | 修改 | `firstPage` 映射、`HasCommands`、渲染顺序调整、移除失效 `Base` |
| `userscript-console/internal/pages/pages_test.go` | 修改 | 相对链接断言（失败测试先行） |

**执行环境备忘（AGENTS.md §10）：** PowerShell 5.1 不支持 `&&`/heredoc，多行 shell 一律写临时 `.sh` 后用 `D:\Software\Git\bin\bash.exe` 执行；`go test -coverprofile` 必须空格形式；`rg`/`Find-String` 不可用。

---

### 任务 1：批次 0 — 基线重建

**文件：**
- 创建：`userscripts/docs/reviews/2026-10-07-baseline.md`

- [ ] **步骤 1：层 1（数据源层）审查**

逐文件通读并记录发现：
- `userscript-console/internal/sources/` 全部 `.go` 与其测试（重点：`greasyfork.go` 的 update 子域一级 + 三级回退、空 Code 报错；`sources.go` 的 Accept-Language——v1.1.2 修复，只登记问题不回退行为）
- 对照：`projec-02` 中同步抓取实现（`userscript_manager/` 下 grep `greasyfork`）

- [ ] **步骤 2：层 2（命令·数据层）审查**

- `userscript-console/internal/commands/*.go`、`internal/cleanup/*.go`、`internal/registry/*.go`
- `userscripts/tools/*.py` 与 `tools/tests/*.py`、`registry.json`
- 对照：`userscripts/SPEC-DATA.md`、`projec-02/panel_cleanup.py`
- 已知必须复核项：I4（project 步骤失败阻断 registry 提交语义）、I5（回帖不报提交/触发失败）、I9（评论正文双重处理）、C2 相关是否还有遗漏子项

- [ ] **步骤 3：层 3（CI·站点层）审查**

- `userscripts/.github/workflows/*.yml`、`tools/validate_workflows.py`、`userscript-console/action.yml`
- `userscript-console/internal/pages/**`、`cmd/usm/site.go`、`cmd/usm/snapgen.go`
- 对照：`projec-02/build_pages.py`、`projec-02/tests/test_pages.py`、`userscripts/CUTOVER.md` §3、`SPEC-WORKFLOWS.md`
- **已知嫌疑清单（逐条给出归属 C/I/M/F 与严重度，登记进基线）：**
  1. `?page=N` 分页链接落在静态 `page-N.html` 上无效（应为 `page-N.html` 文件互链，参照 `projec-02/build_pages.py:764-767`）
  2. 空归档时不产 `commands/page-1.html`（CUTOVER §3 要求"空态"可达；参照 `projec-02/build_pages.py:822-824` 跳转页）
  3. `detail.tmpl` 无命令归档导航（`projec-02` 有 `../commands/page-1.html`，test_pages.py:879）
  4. I1-I11 已知项逐条复核现状（CI 门禁、GraphQL schema、golangci-lint、SHA-pin、markdown 消毒、首页 JS TypeError、命令页快照等）
  5. 53=3+13+17+… 的构成差异——重建时重新归类，以重建结果为准

- [ ] **步骤 4：汇总写入基线文件**

按以下骨架写 `userscripts/docs/reviews/2026-10-07-baseline.md`（行数=实际发现数）：

```markdown
# 审查基线 · 2026-10-07（重修勾销清单）

> 规格：docs/superpowers/specs/2026-10-07-rework-by-review-design.md
> 验收：批次 5 二次全面复审判"可合并"
> 状态：open / fixed / waived（waived 须写理由）

| 编号 | 层 | 文件:行 | 问题描述 | 严重度 | projec-02/SPEC 依据 | 状态 |
|---|---|---|---|---|---|---|
| C1 | 3 | action.yml:197 | PAGES_BASE 把 owner/repo 整体替换为 - | Critical | CUTOVER §3 冒烟 | open |
| C2 | 2 | commands/cleanup.go:117 | 先删评论后写归档，数据丢失 | Critical | SPEC-DATA.md:103 | open |
| C3 | 3 | 多模板 | 绝对根路径链接在 Pages 子路径 404 | Critical | CUTOVER.md:92-97 | open |
```

规则：**批次 1 关闭前，基线中所有 Critical 必须 fixed**；新发现的 Critical 自动并入批次 1。

- [ ] **步骤 5：提交基线**

```bash
git add docs/reviews/2026-10-07-baseline.md
git commit -m "docs: 落盘审查基线（重修勾销清单）"
```
验证：`git status --short` 仅剩 ` M README.md` 与 ` M SETUP.md`（两者本批不提交）。

---

### 任务 2：C2 失败测试 — MergeArchive 幂等与保留语义

**文件：**
- 修改：`userscript-console/internal/cleanup/cleanup_test.go`（文件末尾追加）

- [ ] **步骤 1：编写失败测试**

```go
// TestMergeArchiveDedupByID 同一评论 ID 已在归档中时不得重复归档（SPEC-DATA.md:102 幂等）。
func TestMergeArchiveDedupByID(t *testing.T) {
	existing := &Archive{Schema: 1, Commands: []CommandKey{
		{Command: "add", Results: []Result{
			{ID: "n1", Author: "u", Body: "/add a", CreatedAt: time.Date(2026, 10, 1, 0, 0, 0, 0, time.UTC)},
		}},
	}}
	newResults := map[string][]Result{
		"add": {
			{ID: "n1", Author: "u", Body: "/add a", CreatedAt: time.Date(2026, 10, 1, 0, 0, 0, 0, time.UTC)},
			{ID: "n2", Author: "u", Body: "/add b", CreatedAt: time.Date(2026, 10, 2, 0, 0, 0, 0, time.UTC)},
		},
	}
	merged := MergeArchive(existing, newResults, 10)
	if len(merged.Commands) != 1 {
		t.Fatalf("应只有 add 组，实际 %d", len(merged.Commands))
	}
	if got := len(merged.Commands[0].Results); got != 2 {
		t.Errorf("n1 已归档不应重复：期望 2 条，实际 %d", got)
	}
}

// TestMergeArchiveKeepNewest 截断必须保留最新 Keep 条而非最旧，落盘顺序旧→新（SPEC-DATA.md §2.3）。
func TestMergeArchiveKeepNewest(t *testing.T) {
	d := func(day int) time.Time { return time.Date(2026, 10, day, 0, 0, 0, 0, time.UTC) }
	existing := &Archive{Schema: 1, Commands: []CommandKey{
		{Command: "add", Results: []Result{
			{ID: "o1", Author: "u", CreatedAt: d(1)},
			{ID: "o2", Author: "u", CreatedAt: d(2)},
		}},
	}}
	newResults := map[string][]Result{
		"add": {{ID: "n1", Author: "u", CreatedAt: d(3)}, {ID: "n2", Author: "u", CreatedAt: d(4)}},
	}
	merged := MergeArchive(existing, newResults, 2)
	results := merged.Commands[0].Results
	if len(results) != 2 {
		t.Fatalf("keep=2 应保留 2 条，实际 %d", len(results))
	}
	if results[0].ID != "n1" || results[1].ID != "n2" {
		t.Errorf("应保留最新 2 条且旧→新排列，实际 [%s, %s]", results[0].ID, results[1].ID)
	}
}
```

- [ ] **步骤 2：运行验证失败**

```
go test ./internal/cleanup/ -run 'TestMergeArchiveDedupByID|TestMergeArchiveKeepNewest' -v
```
预期：FAIL（dedup 用例实际 3 条；keep 用例实际 [o1, o2]）。

- [ ] **步骤 3：强化既有 TestMergeArchiveKeep 断言（固定正确语义）**

将 `cleanup_test.go:198-202` 的断言替换为：

```go
	merged := MergeArchive(existing, newResults, 2)
	addCmd := merged.Commands[0]
	if len(addCmd.Results) != 2 {
		t.Errorf("Keep=2 时应保留 2 条，实际: %d", len(addCmd.Results))
	}
	if addCmd.Results[0].ID != "r2" || addCmd.Results[1].ID != "r3" {
		t.Errorf("应保留最新 r2、r3 且旧→新排列，实际 [%s, %s]",
			addCmd.Results[0].ID, addCmd.Results[1].ID)
	}
```

---

### 任务 3：C2 实现 — MergeArchive 重写

**文件：**
- 修改：`userscript-console/internal/cleanup/cleanup.go:118-152`

- [ ] **步骤 1：编写最少实现**

用以下实现整体替换 `MergeArchive`（函数 doc 同步更新）：

```go
// MergeArchive 将新结果合并到归档：按评论 ID 幂等（SPEC-DATA.md:102），
// 每个命令保留最新 Keep 条，落盘顺序为旧→新（SPEC-DATA.md §2.3）。
func MergeArchive(existing *Archive, newResults map[string][]Result, keep int) *Archive {
	if existing == nil {
		existing = &Archive{Schema: 1}
	}
	merged := make(map[string][]Result)
	seen := make(map[string]map[string]bool)
	mark := func(cmd, id string) {
		if id == "" {
			return
		}
		if seen[cmd] == nil {
			seen[cmd] = make(map[string]bool)
		}
		seen[cmd][id] = true
	}
	isSeen := func(cmd, id string) bool { return id != "" && seen[cmd][id] }

	for _, cmd := range existing.Commands {
		for _, r := range cmd.Results {
			merged[cmd.Command] = append(merged[cmd.Command], r)
			mark(cmd.Command, r.ID)
		}
	}
	for cmd, results := range newResults {
		for _, r := range results {
			if isSeen(cmd, r.ID) {
				continue
			}
			merged[cmd] = append(merged[cmd], r)
			mark(cmd, r.ID)
		}
	}

	var commands []CommandKey
	for cmd, results := range merged {
		sort.Slice(results, func(i, j int) bool {
			return results[i].CreatedAt.After(results[j].CreatedAt)
		})
		if len(results) > keep {
			results = results[:keep]
		}
		sort.Slice(results, func(i, j int) bool {
			return results[i].CreatedAt.Before(results[j].CreatedAt)
		})
		commands = append(commands, CommandKey{
			Command:   cmd,
			Results:   results,
			Author:    results[0].Author,
			CreatedAt: results[0].CreatedAt,
		})
	}
	sort.Slice(commands, func(i, j int) bool {
		return commands[i].Command < commands[j].Command
	})
	return &Archive{Schema: 1, Commands: commands}
}
```

- [ ] **步骤 4：运行 cleanup 包测试验证通过**

```
go test ./internal/cleanup/ -v
```
预期：全部 PASS（含 Task 2 新增与既有 `TestMergeArchive*`）。

---

### 任务 4：C2 失败测试 — 先归档后删除（编排层）

**文件：**
- 修改：`userscript-console/internal/commands/cleanup_test.go`
- 修改：`userscript-console/internal/commands/cleanup.go`（仅加注入缝声明，见步骤 1）

- [ ] **步骤 1：添加注入缝（非测试逻辑，先行落位）**

在 `commands/cleanup.go` 的 import 块之后追加：

```go
// saveArchive 是 cleanup.Save 的注入缝，测试用于构造保存失败（见 cleanup_edge 思路）。
var saveArchive = cleanup.Save
```

- [ ] **步骤 2：编写两个失败测试（文件末尾追加）**

```go
// TestCleanupSaveFailureSkipsDelete 归档保存失败时一条评论都不得删除（SPEC-DATA.md:103 先落盘再删）。
func TestCleanupSaveFailureSkipsDelete(t *testing.T) {
	root := t.TempDir()
	reg := &registry.Registry{Schema: registry.SchemaVersion, Scripts: []registry.Script{
		{ID: "s1", Type: registry.TypeSelf, Name: "测试", Version: "1.0.0", Enabled: true},
	}}
	data, _ := json.Marshal(reg)
	os.WriteFile(filepath.Join(root, "registry.json"), data, 0o644)

	d := &cleanupDoer{t: t}
	comment := map[string]any{
		"id": "c1", "author": map[string]any{"login": "u1"},
		"body": "/add https://x.com", "createdAt": "2026-10-01T00:00:00Z",
	}
	list, _ := json.Marshal(map[string]any{
		"data": map[string]any{"repository": map[string]any{"issue": map[string]any{
			"comments": map[string]any{
				"pageInfo": map[string]any{"hasNextPage": false, "endCursor": ""},
				"nodes":    []any{comment},
			},
		}}},
	})
	// 只预置 1 条响应：若发生删除调用，doer 会因"第 2 次调用无预置响应"直接 Fatal
	d.resps = []string{string(list)}

	orig := saveArchive
	saveArchive = func(string, *cleanup.Archive) error { return errors.New("磁盘已满") }
	t.Cleanup(func() { saveArchive = orig })

	env := &Env{
		Root: root, RepoOwner: "o", RepoName: "o/r",
		IssueNumber: 1, GHClient: newCleanupGHClient(t, d),
		Now: time.Date(2026, 10, 5, 0, 0, 0, 0, time.UTC),
	}
	_, err := Execute("cleanup", env, "--apply", nil)
	if err == nil || !strings.Contains(err.Error(), "保存归档失败") {
		t.Fatalf("应返回保存归档失败，实际: %v", err)
	}
	if d.calls != 1 {
		t.Errorf("保存失败时不得调用删除接口，实际 HTTP 调用 %d 次", d.calls)
	}
}

// TestCleanupDeleteFailureArchiveAlreadySaved 删除失败前归档必须已落盘，下轮只补删除。
func TestCleanupDeleteFailureArchiveAlreadySaved(t *testing.T) {
	root := t.TempDir()
	reg := &registry.Registry{Schema: registry.SchemaVersion, Scripts: []registry.Script{
		{ID: "s1", Type: registry.TypeSelf, Name: "测试", Version: "1.0.0", Enabled: true},
	}}
	data, _ := json.Marshal(reg)
	os.WriteFile(filepath.Join(root, "registry.json"), data, 0o644)

	d := &cleanupDoer{t: t}
	c1 := map[string]any{"id": "c1", "author": map[string]any{"login": "u"},
		"body": "/add old", "createdAt": "2026-10-01T00:00:00Z"}
	c2 := map[string]any{"id": "c2", "author": map[string]any{"login": "u"},
		"body": "/add new", "createdAt": "2026-10-02T00:00:00Z"}
	list, _ := json.Marshal(map[string]any{
		"data": map[string]any{"repository": map[string]any{"issue": map[string]any{
			"comments": map[string]any{
				"pageInfo": map[string]any{"hasNextPage": false, "endCursor": ""},
				"nodes":    []any{c1, c2},
			},
		}}},
	})
	// keep=1 → 仅 c2 保留，删除 c1 时返回 GraphQL 错误
	d.resps = []string{string(list), `{"data":null,"errors":[{"message":"boom"}]}`}

	env := &Env{
		Root: root, RepoOwner: "o", RepoName: "o/r",
		IssueNumber: 1, GHClient: newCleanupGHClient(t, d),
		Now: time.Date(2026, 10, 5, 0, 0, 0, 0, time.UTC),
	}
	_, err := Execute("cleanup", env, "--apply --keep 1", nil)
	if err == nil || !strings.Contains(err.Error(), "删除评论失败") {
		t.Fatalf("应返回删除评论失败，实际: %v", err)
	}
	archPath := filepath.Join(root, "archive", "commands.json")
	archData, rerr := os.ReadFile(archPath)
	if rerr != nil {
		t.Fatalf("删除失败前归档必须已保存: %v", rerr)
	}
	if !strings.Contains(string(archData), `"id": "c2"`) {
		t.Errorf("归档应含保留条目 c2，实际: %s", archData)
	}
}
```

注意：`errors` 需加入 import 块（`"errors"`）。

- [ ] **步骤 3：运行验证失败**

```
go test ./internal/commands/ -run 'TestCleanupSaveFailureSkipsDelete|TestCleanupDeleteFailureArchiveAlreadySaved' -v
```
预期：FAIL —— 现行代码先删后存：用例 1 会触发 doer "第 2 次调用无预置响应" Fatal；用例 2 在删除处即返回、归档文件不存在。

- [ ] **步骤 4：强化既有 TestCleanupWithApplyAndDelete（原断言不失败）**

1. 将 `cleanup_test.go:75` 的 comment2 body 改为 `"/add https://new2.com"`（两评论同命令，keep=1 时确定性删除 1 条）。
2. 将 `cleanup_test.go:115-117` 替换为硬断言：

```go
	if !strings.Contains(res.Text, "已删除评论: 1") {
		t.Errorf("keep=1 时应删除 1 条（new1），输出: %s", res.Text)
	}
```
3. 对应地，`d.resps` 中删除响应保留 2 条无妨（未用完不会报错），但第 2 条改为不使用：删除 `cleanup_test.go:97` 的第二个 delete 响应行，避免误导。

---

### 任务 5：C2 实现 — 编排改为先存后删

**文件：**
- 修改：`userscript-console/internal/commands/cleanup.go:117-129`

- [ ] **步骤 1：替换 Apply 分支**

将现有 `if flags.Apply { ... }` 整块（先 for 删除、后 Save）替换为：

```go
		if flags.Apply {
			// SPEC-DATA.md:103 归档先落盘再删评论；删除失败下轮只补删除。
			if err := saveArchive(archivePath, merged); err != nil {
				return Result{}, fmt.Errorf("保存归档失败: %w", err)
			}
			for _, c := range comments {
				if !keptIDs[c.NodeID] {
					if err := env.GHClient.DeleteComment(ctx, c.NodeID); err != nil {
						return Result{}, fmt.Errorf("删除评论失败（归档已保存，下轮只补删除）: %w", err)
					}
					totalDeleted++
				}
			}
		}
```

- [ ] **步骤 2：运行 commands 包测试验证通过**

```
go test ./internal/commands/ -v
```
预期：全部 PASS（含任务 4 四个用例与强化后的既有用例）。

- [ ] **步骤 3：全量门禁**

```
gofmt -l .
go vet ./...
go test ./... -covermode=atomic -coverprofile cover.out
go tool cover -func=cover.out
```
预期：gofmt 无输出；vet 无报错；测试全 PASS；总覆盖 ≥90%（低于则为新代码补边角测试，如 `seen` 空 ID 分支）。

- [ ] **步骤 4：提交 C2（工具仓）**

```bash
git add internal/cleanup/cleanup.go internal/cleanup/cleanup_test.go internal/commands/cleanup.go internal/commands/cleanup_test.go
git commit -m "fix(cleanup): 归档先落盘再删评论并按 ID 幂等保留最新 N 条"
```

---

### 任务 6：C1 验证与提交（两仓）

**文件：**
- `userscript-console/action.yml:194-201`（已改，待验证提交）
- `userscripts/SETUP.md:65`（已改，待提交）

- [ ] **步骤 1：Bash 实测 PAGES_BASE 推导**

写临时文件 `%TEMP%\opencode\c1_verify.sh`（内容如下），然后执行：

```bash
GITHUB_REPOSITORY=acg-q/userscript-console
owner_repo=(${GITHUB_REPOSITORY//\// })
owner="${owner_repo[0]}"
repo="${owner_repo[1]}"
echo "https://${owner}.github.io/${repo}"
```

```
& "D:\Software\Git\bin\bash.exe" "$env:TEMP\opencode\c1_verify.sh"
```
预期输出：`https://acg-q.github.io/userscript-console`（与 `action.yml` 内片段逐字一致）。**禁止**把该片段内联进 PowerShell 命令行（引号转义会被破坏）。

- [ ] **步骤 2：提交工具仓 action.yml**

```bash
git add action.yml
git commit -m "fix(action): PAGES_BASE 按 owner/repo 拆分推导子路径站点基址"
```

- [ ] **步骤 3：提交内容仓 SETUP.md（仅此文件）**

```bash
git add SETUP.md
git commit -m "docs: SETUP 的 PAGES_BASE 示例修正为实际仓名"
```
验证：`git status --short` 仅剩 ` M README.md`（永不提交）。

---

### 任务 7：C3 失败测试 — 相对链接断言

**文件：**
- 修改：`userscript-console/internal/pages/pages_test.go`（末尾追加）

- [ ] **步骤 1：编写失败测试**

```go
// TestBuildLinksAreRelative 站点内链必须是相对路径，Pages 子路径部署不得 404（CUTOVER §3）。
func TestBuildLinksAreRelative(t *testing.T) {
	reg := buildTestRegistry(t)
	opts := Options{Out: t.TempDir(), PagesBase: "https://test.github.io/repo",
		Now: time.Date(2026, 10, 6, 0, 0, 0, 0, time.UTC)}

	// 归档：使命令页与首页导航可用（renderCommands 从 Out 同级 archive/ 读取）
	archiveDir := filepath.Join(filepath.Dir(filepath.Clean(opts.Out)), "archive")
	os.MkdirAll(archiveDir, 0o755)
	archiveJSON := `{"schema":1,"commands":[{"command":"add","author":"u","created_at":"2026-01-01T00:00:00Z","results":[{"id":"r1","author":"u","body":"/add url","created_at":"2026-01-01T00:00:00Z"}]}]}`
	if err := os.WriteFile(filepath.Join(archiveDir, "commands.json"), []byte(archiveJSON), 0o644); err != nil {
		t.Fatal(err)
	}

	out, err := Build(reg, opts, Data{IssueStats: map[string]int{}})
	if err != nil {
		t.Fatalf("Build 失败: %v", err)
	}

	cases := []struct{ name, html, want, forbid string }{
		{"首页脚本卡", out.IndexHTML, `href="scripts/`, `href="/scripts/`},
		{"首页命令归档导航", out.IndexHTML, `href="commands/page-1.html"`, `href="/commands`},
		{"详情页返回首页", out.DetailHTMLs["test1"], `href="../"`, `href="/"`},
		{"命令页返回列表", out.CommandPages[1], `href="index.html"`, `{{.Base}}`},
		{"命令索引分页链接", out.CommandsIndex, `href="page-1.html"`, `/commands/?cmd=`},
	}
	for _, c := range cases {
		if !strings.Contains(c.html, c.want) {
			t.Errorf("%s 应含 %q", c.name, c.want)
		}
		if strings.Contains(c.html, c.forbid) {
			t.Errorf("%s 不应含 %q", c.name, c.forbid)
		}
	}
}
```

注意：`forbid: href="/"` 会匹配 `href="/`（绝对路径前缀）但也可能误伤——`详情页返回首页` 用 `href="/"` 精确子串即可（当前模板是 `href="/"`），若与 `href="//cdn…` 冲突则改为断言 `notContains: 'href="/"'`。实现时先跑再微调断言，不放宽目标。

- [ ] **步骤 2：运行验证失败**

```
go test ./internal/pages/ -run TestBuildLinksAreRelative -v
```
预期：FAIL（首页无命令归档导航、脚本卡为 `/scripts/`、详情页 `href="/"`、命令页 `{{.Base}}` 已渲染为绝对 URL、索引为 `/commands/?cmd=`）。

---

### 任务 8：C3 实现 — 模板与渲染层

**文件：**
- 修改：`internal/pages/templates/index.tmpl`（51 行链接 + 41 行后增导航）
- 修改：`internal/pages/templates/detail.tmpl:127`
- 修改：`internal/pages/templates/commands.tmpl:35`
- 修改：`internal/pages/templates/commands-index.tmpl:25,30`
- 修改：`internal/pages/pages.go`（`indexPageData`、`renderIndex`、`Build`、`renderCommands`、`renderCommandsIndex`、`commandsIndexData`、`commandsPageData`）

- [ ] **步骤 1：改模板**

`index.tmpl`：
- 51 行：`<a href="/scripts/{{.ID}}">` → `<a href="scripts/{{.ID}}.html">`
- 41 行 `<h1>脚本控制台</h1>` 之后插入：

```html
        {{if .HasCommands}}<a class="back" href="commands/page-1.html">命令归档</a>{{end}}
```

`detail.tmpl`：
- 127 行：`href="/"` → `href="../"`

`commands.tmpl`：
- 35 行：`href="{{.Base}}/commands"` → `href="index.html"`

`commands-index.tmpl`：
- 25 行：`href="{{.Base}}/commands"` → `href="index.html"`
- 30 行：`<a href="/commands/?cmd={{.}}">` → `<a href="page-{{index .FirstPage .}}.html">`

- [ ] **步骤 2：改 pages.go**

1. `indexPageData` 增字段 `HasCommands bool`；`renderIndex` 签名改为 `renderIndex(scripts []registry.Script, opts Options, reg *registry.Registry, hasCommands bool)`，函数内 `HasCommands: hasCommands`。
2. `Build` 中把命令渲染段（现 142-149 行）整体移到 index 渲染（现 105 行）之前，调用改为：
   ```go
   cp, cidx, err := renderCommands(opts)
   if err != nil {
       out.BuildWarnings = append(out.BuildWarnings, fmt.Sprintf("W3: %v", err))
   }
   out.CommandPages = cp
   out.CommandsIndex = cidx
   // （后续 index 渲染）
   idx, err := renderIndex(active, opts, reg, len(cp) > 0)
   ```
   保持 W3/W1 告警的追加顺序与现状一致（W3 先、W1 后）。
3. `renderCommands` 内维护 `firstPage := make(map[string]int)`，在每个命令的分页循环首次迭代时记录 `firstPage[cmdName] = pageNum`；`renderCommandsIndex(cmdNames, firstPage, opts.PagesBase)` 改传映射（`opts.PagesBase` 参数随之删除）。
4. `commandsIndexData` 增 `FirstPage map[string]int`，删 `Base`；`commandsPageData` 删 `Base`；`renderCommandPage` 删 `base` 参数；相应调用同步。
5. 全仓 grep `\.Base`、`renderIndex(`、`renderCommandsIndex(`、`renderCommandPage(` 确认无残留调用（含测试文件）。

- [ ] **步骤 3：运行验证通过**

```
gofmt -l .
go vet ./...
go test ./internal/pages/ -v
```
预期：`TestBuildLinksAreRelative` 及全部既有用例 PASS。

---

### 任务 9：C3 快照与产物级验证

- [ ] **步骤 1：刷新快照基线并人工过目**

```
go run ./cmd/usm snapshot update
git diff --stat
git diff
```
预期：diff 仅含 `site/` 快照中链接相关变化（`/scripts/` → `scripts/…html`、新增命令归档导航、`../` 返回、`page-1.html`）；逐文件确认无其他语义变化后接受。若 diff 出现链接之外的意外变化，回到任务 8 排查。

- [ ] **步骤 2：产物级链接验证（生成真实 dist）**

查 `cmd/usm` 的 site 子命令用法（`go run ./cmd/usm site --help`），在临时目录生成站点后执行检查脚本 `%TEMP%\opencode\c3_verify.sh`：

```bash
cd "$1"
! grep -R 'href="/scripts/\|href="/commands\|href="/"' index.html scripts/*.html commands/*.html
grep -q 'href="scripts/.*\.html"' index.html
grep -q 'href="commands/page-1.html"' index.html
grep -q 'href="../"' scripts/*.html
grep -q 'href="index.html"' commands/*.html
grep -q 'href="page-1.html"' commands/index.html
echo C3-PRODUCT-OK
```
运行：`& "D:\Software\Git\bin\bash.exe" "$env:TEMP\opencode\c3_verify.sh" <dist目录>`
预期：末行 `C3-PRODUCT-OK`，且 `! grep` 无输出（无绝对根路径残留）。

- [ ] **步骤 3：全量门禁（同任务 5 步骤 3）**

```
gofmt -l .
go vet ./...
go test ./... -covermode=atomic -coverprofile cover.out
go tool cover -func=cover.out
go run ./cmd/usm snapshot check
go build ./...
```
预期：全绿、总覆盖 ≥90%、snapshot check 通过。

- [ ] **步骤 4：提交 C3（工具仓）**

```bash
git add internal/pages cmd/usm
git commit -m "fix(pages): 站点内链改相对路径并补首页命令归档导航"
```

---

### 任务 10：批次 1 收口 — 双仓推送、CI 绿、勾销

- [ ] **步骤 1：内容仓 tools 门禁（基线提交后已含，双保险）**

```
python -m unittest discover tools/tests -q
python tools/validate_workflows.py
```
预期：全绿 / `ALL CHECKS PASSED`。

- [ ] **步骤 2：推送两仓并轮询 CI**

工具仓（含 C1/C2/C3 三个 commit）与内容仓（基线 + SETUP 两个 commit）分别：

```bash
git push origin HEAD
```
轮询：优先 `webfetch` 查 actions runs（`rate_limit.remaining>0` 时才允许 PowerShell `Invoke-RestMethod`）。预期：工具仓 Test workflow 绿；内容仓 validate/Deploy 相关 workflow 绿。**CI 红 → 修复后新 commit，禁止 amend 已推送 commit。**

- [ ] **步骤 3：勾销基线**

编辑 `docs/reviews/2026-10-07-baseline.md`：C1/C2/C3 状态 → `fixed`（附 commit 短哈希）；批次 1 关闭条件核对：**基线中所有 Critical 均为 fixed**（若批次 0 重建出新 Critical，先修再关）。提交：

```bash
git add docs/reviews/2026-10-07-baseline.md
git commit -m "docs: 勾销 C1-C3（批次 1 完成）"
git push origin HEAD
```

- [ ] **步骤 4：向用户汇报**

汇报：基线总条数与构成、批次 1 勾销情况、各 CI 结果、批次 2（13 Important 四波）待用户确认后开始。

---

## 自检记录

1. **规格覆盖度：** §3 批次 0/1 → 任务 1-10；§4.1 C1/C2/C3 全部有对应任务；§5 测试三路径 → C2 用例含正常/归档失败/删除失败；§6 回滚 → 每任务独立 commit、CI 红新 commit 不 amend；§3 未提交改动盘点 → 任务 1 步骤 5 + 任务 6 步骤 3 验证。批次 2-5 明确不在本计划（规格 D5/范围：基线落盘后另写计划 2）。
2. **占位符扫描：** 无"待定/TODO"；任务 1 审查步骤给出具体文件清单与嫌疑登记表，属调查性步骤而非代码占位。
3. **类型一致性：** `saveArchive`（声明于任务 4 步骤 1、使用于任务 5）；`firstPage`/`HasCommands`/`FirstPage`（任务 8 内定义与引用一致）；`renderIndex` 新签名仅 Build 调用（任务 8 步骤 2.2 与 2.5 交叉核对）。
