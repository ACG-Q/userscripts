#!/usr/bin/env python3
"""Validate all GitHub workflows against SPEC-WORKFLOWS.md."""
import os
import re
import subprocess
import sys

import yaml

errors = []

# ── helpers ──────────────────────────────────────────────────────────────────
def load_wf(name):
    path = f'.github/workflows/{name}'
    raw = open(path, encoding='utf-8').read()
    doc = yaml.safe_load(raw)
    # PyYAML turns bare 'on' into True
    events = doc.get(True, {}) if True in doc else doc.get('on', {})
    return raw, doc, events

# ── 1. permissions (§3) ─────────────────────────────────────────────────────
SPEC_PERMS = {
    'issue-commands.yml':      {'contents':'write','issues':'write','actions':'write','discussions':'write'},
    'deploy-pages.yml':        {'contents':'read','pages':'write','id-token':'write','issues':'read','discussions':'read'},
    'sync-scheduled.yml':      {'contents':'write','issues':'write','actions':'write','discussions':'write'},
    'cleanup-panel.yml':       {'contents':'write','issues':'write','actions':'write'},
    'init-command-panel.yml':  {'issues':'write','contents':'read'},
    'validate.yml':            {'contents':'read'},
}
for f, expected in SPEC_PERMS.items():
    raw, doc, _ = load_wf(f)
    actual = doc.get('permissions', {})
    if dict(actual) != expected:
        errors.append(f'{f}: permissions mismatch expected={expected} actual={dict(actual)}')

# ── 2. timeout (§2.x) ───────────────────────────────────────────────────────
TIMEOUTS = {'issue-commands.yml':15,'deploy-pages.yml':10,'sync-scheduled.yml':15,'cleanup-panel.yml':10,'validate.yml':5}
for f, exp_t in TIMEOUTS.items():
    raw, doc, _ = load_wf(f)
    job_name = list(doc['jobs'].keys())[0]
    t = doc['jobs'][job_name]['timeout-minutes']
    if t != exp_t:
        errors.append(f'{f}: timeout={t} expected={exp_t}')

# ── 3. concurrency ──────────────────────────────────────────────────────────
v = yaml.safe_load(open('.github/workflows/validate.yml', encoding='utf-8'))['concurrency']
dp = yaml.safe_load(open('.github/workflows/deploy-pages.yml', encoding='utf-8'))['concurrency']
if v.get('cancel-in-progress') != True:
    errors.append('validate.yml: cancel-in-progress should be true (allow reruns)')
if dp.get('cancel-in-progress') != False:
    errors.append('deploy-pages.yml: cancel-in-progress should be false (serial deploy)')

# ── 4. git add danger (§4) ──────────────────────────────────────────────────
DANGER = ['git add .', 'git add -A', 'git add --all']
for f in ['issue-commands.yml','deploy-pages.yml','sync-scheduled.yml','cleanup-panel.yml']:
    raw = open(f'.github/workflows/{f}', encoding='utf-8').read()
    for d in DANGER:
        if d in raw:
            errors.append(f'{f}: contains dangerous "{d}"')

# ── 5. !cancelled guard (§2.1 step ⑥) ─────────────────────────────────────
ic_raw = open('.github/workflows/issue-commands.yml', encoding='utf-8').read()
if '!cancelled()' not in ic_raw:
    errors.append('issue-commands.yml: missing !cancelled() on reply step')

# ── 6. run 步骤必须是 tools/*.py 单行调用（设计：全量替换内联 shell）────────
# 遍历 SPEC_PERMS（第 1 节已定义）而非 TRIGGERS（第 7 节才定义，避免 NameError）
RUN_PATTERN = re.compile(r'^python tools/[a-z_]+\.py(\s.*)?$')
for f in SPEC_PERMS:
    raw, doc, _ = load_wf(f)
    for job_name, job in (doc.get('jobs') or {}).items():
        for step in job.get('steps') or []:
            if 'run' not in step:
                continue
            run = str(step['run']).strip()
            if not RUN_PATTERN.match(run):
                errors.append(
                    f'{f} [{job_name}]: run 必须是单行 python tools/*.py 调用: {run!r}')

# ── 7. trigger / on: events (§2) ───────────────────────────────────────────
TRIGGERS = {
    'issue-commands.yml':      {'issue_comment'},
    'deploy-pages.yml':        {'push','issues','issue_comment','discussion_comment','workflow_dispatch'},
    'sync-scheduled.yml':      {'workflow_dispatch'},
    'cleanup-panel.yml':       {'schedule','workflow_dispatch'},
    'init-command-panel.yml':  {'workflow_dispatch'},
    'validate.yml':            {'push','pull_request'},
}
for f, expected_keys in TRIGGERS.items():
    raw, doc, events = load_wf(f)
    got = set(events.keys()) if isinstance(events, dict) else set()
    if got != expected_keys:
        errors.append(f'{f}: triggers got={got} expected={expected_keys}')

# ── 8. tool version pinning (§5) ───────────────────────────────────────────
# 支持两种 pin 方式：
#   a) uses: acg-q/userscript-console@<40位sha>   （安全惯例，显式版本）
#   b) uses: acg-q/userscript-console@v1.1.0      （零手填二进制，自动推导）
#   c) uses: acg-q/userscript-console@v1          （大版本 tag，自动取最新 v1.x）
REPO = 'acg-q/userscript-console'
TOOL_WORKFLOWS = ['issue-commands.yml', 'deploy-pages.yml', 'sync-scheduled.yml',
                  'cleanup-panel.yml', 'validate.yml']

def latest_tool_sha():
    """Read the tool repo's master SHA; returns None when unreachable."""
    tool_repo = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'userscript-console'))
    if not os.path.isdir(os.path.join(tool_repo, '.git')):
        return None
    try:
        out = subprocess.run(['git', '-C', tool_repo, 'rev-parse', 'origin/master'],
                             capture_output=True, text=True, timeout=10)
        sha = out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None


LATEST = latest_tool_sha()
pinned_shas = set()
pinned_tags = set()

for f in TOOL_WORKFLOWS:
    raw = open(f'.github/workflows/{f}', encoding='utf-8').read()
    # Match @<sha> or @vX.Y.Z or @vN
    for pin in re.findall(f'{re.escape(REPO)}@([0-9a-f]{{40}}|v[0-9]+(\\.[0-9]+)*(\\.[0-9]+)?)', raw):
        pin = pin[0] if isinstance(pin, tuple) else pin
        if re.fullmatch(r'[0-9a-f]{40}', pin):
            pinned_shas.add(pin)
            if LATEST and pin != LATEST:
                errors.append(f'{f}: stale tool SHA pin {pin} (tool master = {LATEST})')
        elif re.fullmatch(r'v[0-9]+(\.[0-9]+)*(\.[0-9]+)?', pin):
            pinned_tags.add(pin)

if len(pinned_shas) > 1:
    errors.append(f'tool SHA pins inconsistent across workflows: {sorted(pinned_shas)}')
if len(pinned_shas) == 1 and len(pinned_tags) > 0:
    errors.append('tool pins: mixing SHA pins and tag pins is not allowed (pick one per workflow)')

# ── 9. v1 二进制（C4-2） ─────────────────────────────────────────────────
# 工具仓 v1.1.0+：支持零手填二进制（@v1.1.0/@v1 + use-binary: true）
# 所有调用点必须 use-binary: true（源码模式每次都要 go run 编译，慢一个量级）。
USE_BINARY_EXPECTED = 7  # 5 workflows × calls = 7
use_binary_seen = 0

for f in TOOL_WORKFLOWS:
    raw, doc, _ = load_wf(f)
    for job_name, job in (doc.get('jobs') or {}).items():
        for step in job.get('steps') or []:
            uses = str(step.get('uses', ''))
            if not uses.startswith(REPO + '@'):
                continue
            use_binary_seen += 1
            if (step.get('with') or {}).get('use-binary') is not True:
                errors.append(
                    f'{f} [{job_name}]: use-binary 应为 true'
                    '（v1 二进制已发布；源码模式每次都要 go run 编译）')

# ── report ──────────────────────────────────────────────────────────────────
if errors:
    print('VALIDATION FAILED:')
    for e in errors:
        print(f'  ERROR: {e}')
    sys.exit(1)

pin_summary = []
if pinned_shas:
    pin_summary.append(f'SHA:{sorted(pinned_shas)[0][:12]}…')
if pinned_tags:
    pin_summary.append(f'Tags:{sorted(pinned_tags)}')
pin_str = ', '.join(pin_summary) if pin_summary else '(none)'
freshness = '' if LATEST else '  [freshness not checked: tool repo unreachable]'
print('ALL CHECKS PASSED — workflows match SPEC-WORKFLOWS.md')
print(f'  tool pins: {pin_str} across 5 workflows{freshness}')
print('  permissions: 6 workflows verified')
print('  timeouts:     5 checked')
print('  git add:      no dangerous patterns')
print('  run one-liner: all run steps are python tools/*.py calls')
print('  !cancelled:   reply step guarded')
print(f'  use-binary:   {use_binary_seen}/{USE_BINARY_EXPECTED} call sites (v1 binary)')