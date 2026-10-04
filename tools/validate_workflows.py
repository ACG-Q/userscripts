#!/usr/bin/env python3
"""Validate all GitHub workflows against SPEC-WORKFLOWS.md."""
import yaml, re, sys

errors = []
warnings = []

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
    # Split into steps by "- name:"
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
        # skip pure-echo warnings and gh workflow run || true
        if first.startswith('echo'):
            continue
        if 'gh workflow run' in run_body and '||' in run_body:
            continue
        # Reply step intentionally uses set -uo (not -e) to always post at least partial result
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

# ── 8. tool SHA pinning ────────────────────────────────────────────────────
TOOL_SHA = 'ffd137cd20c780e1b582e752c8631e9dbe1cc31c'
REPO = 'acg-q/userscript-console'
for f in ['issue-commands.yml','deploy-pages.yml','sync-scheduled.yml','cleanup-panel.yml','validate.yml']:
    raw = open(f'.github/workflows/{f}', encoding='utf-8').read()
    refs = re.findall(f'{re.escape(REPO)}@([a-f0-9]+)', raw)
    for sha in refs:
        if sha != TOOL_SHA:
            errors.append(f'{f}: stale tool pin {sha} (expected {TOOL_SHA})')

# ── report ──────────────────────────────────────────────────────────────────
if errors:
    print('VALIDATION FAILED:')
    for e in errors:
        print(f'  ERROR: {e}')
    sys.exit(1)
else:
    print('ALL CHECKS PASSED — workflows match SPEC-WORKFLOWS.md')
    print(f'  tool SHA pin: {TOOL_SHA} across 5 workflows')
    print(f'  permissions: 6 workflows verified')
    print(f'  timeouts:     5 checked')
    print(f'  git add:      no dangerous patterns')
    print(f'  euo pipefail: critical run steps covered')
    print(f'  !cancelled:   reply step guarded')
