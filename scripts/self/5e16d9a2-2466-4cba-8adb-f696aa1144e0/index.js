// ==UserScript==
// @name         GitHub Actions 免登录下载 Artifacts (nightly.link)
// @namespace    https://nightly.link/
// @version      1.4
// @description  在 GitHub Actions 运行页为每个 Artifact 添加基于 nightly.link 的免登录下载按钮 (SVG 图标，登录用户默认不显示)
// @author       ACG-Q
// @match        https://github.com/*/*/actions/runs/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    // ========== 用户配置 ==========
    // 已登录 GitHub 时是否仍然显示 nightly.link 按钮
    // false: 登录用户看到官方下载按钮，不重复显示（推荐）
    // true : 即使登录也显示，方便复制链接分享给未登录的人
    const SHOW_WHEN_LOGGED_IN = false;
    // ==============================

    const BTN_CLASS = 'nightly-dl-btn';

    // 判断是否已登录 GitHub
    function isLoggedIn() {
        const meta = document.querySelector('meta[name="user-login"]');
        if (meta) return !!meta.getAttribute('content');
        // 兜底：body 的 class
        return document.body.classList.contains('logged-in');
    }

    // 获取 owner/repo/runId
    function getRunInfo() {
        const m = location.pathname.match(/^\/([^/]+)\/([^/]+)\/actions\/runs\/(\d+)/);
        if (!m) return null;
        return { owner: m[1], repo: m[2], runId: m[3] };
    }

    function buildNightlyUrl(owner, repo, runId, artifactName) {
        return `https://nightly.link/${owner}/${repo}/actions/runs/${runId}/${encodeURIComponent(artifactName)}.zip`;
    }

    function makeSvgIcon() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 16 16');
        svg.setAttribute('width', '16');
        svg.setAttribute('height', '16');
        svg.setAttribute('fill', 'currentColor');
        svg.setAttribute('aria-hidden', 'true');
        svg.style.verticalAlign = 'text-bottom';
        svg.style.marginRight = '4px';

        const p1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p1.setAttribute('d', 'M2.75 14A1.75 1.75 0 0 1 1 12.25v-2.5a.75.75 0 0 1 1.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25v-2.5a.75.75 0 0 1 1.5 0v2.5A1.75 1.75 0 0 1 13.25 14Z');
        svg.appendChild(p1);

        const p2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p2.setAttribute('d', 'M7.25 7.689V2a.75.75 0 0 1 1.5 0v5.689l1.97-1.969a.749.749 0 1 1 1.06 1.06l-3.25 3.25a.749.749 0 0 1-1.06 0L4.22 6.78a.749.749 0 1 1 1.06-1.06l1.97 1.969Z');
        svg.appendChild(p2);

        return svg;
    }

    function makeButton(url, name) {
        const a = document.createElement('a');
        a.className = `btn btn-sm ${BTN_CLASS}`;
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.title = `由 nightly.link 提供的免登录下载服务\nArtifact: ${name}\n点击后将在新标签页打开 nightly.link 并自动开始下载`;
        a.style.whiteSpace = 'nowrap';
        a.style.display = 'inline-flex';
        a.style.alignItems = 'center';

        a.appendChild(makeSvgIcon());

        const text = document.createElement('span');
        text.textContent = 'Download';
        a.appendChild(text);

        return a;
    }

    function scan() {
        const info = getRunInfo();
        if (!info) return;

        // 登录用户默认不需要（官方已有下载按钮）
        if (!SHOW_WHEN_LOGGED_IN && isLoggedIn()) return;

        const rows = document.querySelectorAll('tr[data-artifact-id]');
        for (const row of rows) {
            if (row.querySelector('.' + BTN_CLASS)) continue;

            const nameEl = row.querySelector('td .text-bold');
            if (!nameEl) continue;
            const name = (nameEl.textContent || '').trim();
            if (!name) continue;

            const url = buildNightlyUrl(info.owner, info.repo, info.runId, name);
            const btn = makeButton(url, name);

            const actionCell = row.querySelector('td:last-child');
            let container = actionCell ? actionCell.querySelector('.d-flex') : null;
            if (!container) container = actionCell;
            if (!container) container = row;

            container.appendChild(btn);
        }
    }

    let scheduled = false;
    function scheduleScan() {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => {
            scheduled = false;
            try { scan(); } catch (e) { console.warn('[nightly-dl]', e); }
        });
    }

    scan();
    new MutationObserver(scheduleScan).observe(document.body, { childList: true, subtree: true });
    document.addEventListener('turbo:load', scheduleScan);
    document.addEventListener('turbo:frame-load', scheduleScan);
    document.addEventListener('pjax:end', scheduleScan);
})();