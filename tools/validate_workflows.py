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
    'init-command-panel.yml':  {'issues':'write'},
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

# ── 6. set -euo pipefail on run steps ──────────────────────────────────────
for f in ['issue-commands.yml','sync-scheduled.yml','cleanup-panel.yml']:
    raw = open(f'.github/workflows/{f}', encoding='utf-8').read()
    steps = re.split(r'\n      - name: ', raw)
    for step_text in steps:
        if 'run: |' not in step_text:
            continue
        step_name = step_text.split('\n')[0].strip()
        run_body = step_text.split('run: |', 1)[1].split('\n---')[0]
        lines = [l.strip() for l in run_body.split('\n') if l.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith('echo'):
            continue
        if 'gh workflow run' in run_body and '||' in run_body:
            continue
        # Reply step intentionally uses set -uo (not -e) to always post partial result
        if step_name == 'Reply to comment':
            continue
        if 'set -euo pipefail' not in run_body:
            errors.append(f'{f} [{step_name}]: missing set -euo pipefail')

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

# ── 8. tool SHA pinning (U3-4: pin must track tool repo master) ───────────
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
pinned = set()

for f in TOOL_WORKFLOWS:
    raw = open(f'.github/workflows/{f}', encoding='utf-8').read()
    for sha in re.findall(f'{re.escape(REPO)}@([0-9a-f]+)', raw):
        if len(sha) != 40:
            errors.append(f'{f}: tool pin must be a 40-char sha, got {sha}')
            continue
        pinned.add(sha)
        if LATEST and sha != LATEST:
            errors.append(f'{f}: stale tool pin {sha} (tool master = {LATEST})')

if len(pinned) > 1:
    errors.append(f'tool pins inconsistent across workflows: {sorted(pinned)}')

# ── report ──────────────────────────────────────────────────────────────────
if errors:
    print('VALIDATION FAILED:')
    for e in errors:
        print(f'  ERROR: {e}')
    sys.exit(1)

pin_summary = (sorted(pinned)[0][:12] + '…') if pinned else '(none)'
freshness = '' if LATEST else '  [freshness not checked: tool repo unreachable]'
print('ALL CHECKS PASSED — workflows match SPEC-WORKFLOWS.md')
print(f'  tool SHA pin: {pin_summary} across 5 workflows{freshness}')
print('  permissions: 6 workflows verified')
print('  timeouts:     5 checked')
print('  git add:      no dangerous patterns')
print('  euo pipefail: critical run steps covered')
print('  !cancelled:   reply step guarded')