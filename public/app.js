/* git-release digest — Bento Grid Edition */
'use strict';

import {
  esc, renderInline, formatDate, safeSev, loadDomain, applyTabBadges, readQuery, writeQuery,
} from './common.js';
import { groupByMinor, minorOf } from './minor.js';

let allRecords = [];
let allAdvisories = [];
let activeSev = 'medium';
let activeGroup = 'all';
let activeRepo = 'all';
let releaseRecords = [];

function majorOf(tag) {
  const m = /^v?(\d+)\./.exec(tag ?? '');
  return m ? m[1] : '';
}

// Severity filter is "at least": the default hides none/low/unknown noise.
const NON_RELEASE_GROUPS = new Set(['dbt-packages', 'bigquery', 'lakehouse', 'scaleway']);
const SEV_RANK = { critical: 4, high: 3, medium: 2, low: 1, none: 0, unknown: 0 };

const REPO_DISPLAY = {
  'dagster-io/dagster':      'Dagster',
  'kestra-io/kestra':        'Kestra',
  'apache/airflow':          'Airflow',
};

const GROUP_MAP = {
  'dbt-core':     ['dbt-core'],
  'dbt-v2':       ['dbt-core'],
  'dbt-adapters': ['dbt-adapters'],
  orchestration:  ['orchestration'],
};

const REPO_CHIPS = {
  'dbt-adapters': [
    { label: 'dbt-bigquery', repo: 'dbt-labs/dbt-bigquery' },
    { label: 'dbt-trino',    repo: 'starburstdata/dbt-trino' },
    { label: 'dbt-duckdb',   repo: 'duckdb/dbt-duckdb' },
  ],
  orchestration: [
    { label: 'Dagster', repo: 'dagster-io/dagster' },
    { label: 'Kestra',  repo: 'kestra-io/kestra' },
    { label: 'Airflow', repo: 'apache/airflow' },
  ],
};

const QUERY_SPEC = {
  sev:   { def: 'medium', allowed: ['all', 'critical', 'high', 'medium'] },
  group: { def: 'all', allowed: ['all', ...Object.keys(GROUP_MAP)] },
  repo:  { def: 'all', allowed: Object.values(REPO_CHIPS).flat().map(r => r.repo) },
  q:     { def: '' },
};

function restoreFilters() {
  const q = readQuery(QUERY_SPEC);
  activeSev = q.sev;
  activeGroup = q.group;
  const repoInGroup = (REPO_CHIPS[q.group] ?? []).some(r => r.repo === q.repo);
  activeRepo = repoInGroup ? q.repo : 'all';
  document.getElementById('search').value = q.q;
  document.getElementById('sev-filter').value = activeSev;
}

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  restoreFilters();
  setupTabs();
  setupSearch();
  setupSevFilters();
  setupGroupChips();
  setupDrawer();
  loadDigest();
});

// ── Drawer ─────────────────────────────────────────────────────────────────
function setupDrawer() {
  const backdrop = document.getElementById('drawer-backdrop');
  const drawer   = document.getElementById('drawer');
  const closeBtn = document.getElementById('drawer-close');

  function closeDrawer() {
    drawer.classList.remove('open');
    backdrop.classList.add('hidden');
    document.body.style.overflow = '';
  }

  closeBtn.addEventListener('click', closeDrawer);
  backdrop.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });
}

function openDrawer(record) {
  const a   = record.analysis ?? {};
  const sev = a.severity ?? 'none';

  document.getElementById('drawer-repo').textContent = REPO_DISPLAY[record.repo] ?? record.repo.split('/')[1];
  const sevEl = document.getElementById('drawer-sev');
  sevEl.textContent = sev;
  sevEl.className = `sev sev-${safeSev(sev)}`;

  document.getElementById('drawer-title').textContent = record.name || record.tag;
  document.getElementById('drawer-date').textContent  = formatDate(record.published_at);
  document.getElementById('drawer-summary').innerHTML = renderInline(a.summary ?? '');

  const changesWrap = document.getElementById('drawer-changes-wrap');
  const changesList = document.getElementById('drawer-changes');
  const changes = a.key_changes ?? [];
  if (changes.length) {
    changesList.innerHTML = changes.map(c => `<li>${renderInline(c)}</li>`).join('');
    changesWrap.classList.remove('hidden');
  } else {
    changesWrap.classList.add('hidden');
  }

  const tagsWrap = document.getElementById('drawer-tags-wrap');
  const tagsEl   = document.getElementById('drawer-tags');
  const tags = a.tags ?? [];
  if (tags.length) {
    tagsEl.innerHTML = tags.map(t => `<span class="tag">${esc(t)}</span>`).join('');
    tagsWrap.classList.remove('hidden');
  } else {
    tagsWrap.classList.add('hidden');
  }

  const cveWrap = document.getElementById('drawer-cve-wrap');
  const cvesEl  = document.getElementById('drawer-cves');
  const cveRefs = a.cve_references ?? [];
  if (cveRefs.length) {
    cvesEl.innerHTML = cveRefs.map(id =>
      `<a class="drawer-cve-chip" href="https://nvd.nist.gov/vuln/detail/${esc(id)}" target="_blank" rel="noopener">${esc(id)}</a>`
    ).join('');
    cveWrap.classList.remove('hidden');
  } else {
    cveWrap.classList.add('hidden');
  }

  document.getElementById('drawer-link').href = record.html_url ?? '#';

  const backdrop = document.getElementById('drawer-backdrop');
  const drawer   = document.getElementById('drawer');
  backdrop.classList.remove('hidden');
  drawer.classList.remove('hidden');
  requestAnimationFrame(() => drawer.classList.add('open'));
  document.body.style.overflow = 'hidden';
}

// ── Tabs ───────────────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === btn));
      document.querySelectorAll('.tab-panel').forEach(p => {
        const show = p.id === `tab-${btn.dataset.tab}`;
        p.classList.toggle('active', show);
        p.classList.toggle('hidden', !show);
      });
    });
  });
}

// ── Search ─────────────────────────────────────────────────────────────────
function setupSearch() {
  document.getElementById('search').addEventListener('input', () => applyFilters());
}

// ── Severity filters ───────────────────────────────────────────────────────
function setupSevFilters() {
  document.getElementById('sev-filter').addEventListener('change', e => {
    activeSev = e.target.value;
    applyFilters();
  });
}

// ── Group chips ────────────────────────────────────────────────────────────
function setupGroupChips() {
  const container = document.getElementById('group-chips');
  const sub = document.getElementById('repo-chips-sub');

  const groups = [
    { label: 'All',          key: 'all' },
    { label: 'dbt core',     key: 'dbt-core' },
    { label: 'dbt v2',       key: 'dbt-v2' },
    { label: 'dbt-adapters', key: 'dbt-adapters' },
    { label: 'Orchestration',key: 'orchestration' },
  ];

  container.innerHTML = groups.map(g =>
    `<button class="chip${g.key === activeGroup ? ' active' : ''}" data-group="${g.key}">${g.label}</button>`
  ).join('');
  if (REPO_CHIPS[activeGroup]) {
    const repo = activeRepo;
    showRepoChips(activeGroup);
    activeRepo = repo;
    sub.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.repo === repo));
  }

  container.addEventListener('click', e => {
    const btn = e.target.closest('[data-group]');
    if (!btn) return;
    const key = btn.dataset.group;

    if (key === activeGroup && key !== 'all') {
      activeGroup = 'all';
      activeRepo = 'all';
      showRepoChips(null);
    } else {
      activeGroup = key;
      activeRepo = 'all';
      showRepoChips(key === 'all' ? null : key);
    }

    container.querySelectorAll('.chip').forEach(c =>
      c.classList.toggle('active', c.dataset.group === activeGroup)
    );
    applyFilters();
  });

  sub.addEventListener('click', e => {
    const btn = e.target.closest('[data-repo]');
    if (!btn) return;
    const repo = btn.dataset.repo;
    activeRepo = repo === activeRepo ? 'all' : repo;
    sub.querySelectorAll('.chip').forEach(c =>
      c.classList.toggle('active', c.dataset.repo === activeRepo)
    );
    applyFilters();
  });
}

function showRepoChips(group) {
  const sub = document.getElementById('repo-chips-sub');
  activeRepo = 'all';

  if (!group || !REPO_CHIPS[group]) {
    sub.classList.add('hidden');
    sub.innerHTML = '';
    return;
  }

  sub.innerHTML = REPO_CHIPS[group].map(r =>
    `<button class="chip" data-repo="${r.repo}">${r.label}</button>`
  ).join('');
  sub.classList.remove('hidden');
}


// ── Filters ────────────────────────────────────────────────────────────────
const sevPasses = sev => activeSev === 'all' || (SEV_RANK[sev] ?? 0) >= SEV_RANK[activeSev];

// A dbt-core minor row lists its releases; those below the severity threshold are hidden and counted.
function filterMinorItems(card) {
  let visible = 0;
  const items = card.querySelectorAll('.minor-item');
  items.forEach(li => {
    const ok = sevPasses(li.dataset.severity);
    li.hidden = !ok;
    if (ok) visible++;
  });
  const hidden = items.length - visible;
  card.querySelector('.minor-hidden').textContent = hidden ? `+${hidden} hidden` : '';
  return visible > 0;
}

function majorOk(card) {
  if (activeGroup === 'dbt-v2') return card.dataset.major === '2';
  if (activeGroup === 'dbt-core') return card.dataset.major === '1';
  return true;
}

function applyFilters() {
  const q = document.getElementById('search').value.trim().toLowerCase();

  const cards = document.querySelectorAll('.card');
  let visibleCards = 0;
  cards.forEach(c => {
    const sevOk = c.classList.contains('card-minor') ? filterMinorItems(c) : sevPasses(c.dataset.severity);
    const groupOk = activeGroup === 'all' || (GROUP_MAP[activeGroup] ?? []).includes(c.dataset.group);
    const repoOk = activeRepo === 'all' || c.dataset.repo === activeRepo;
    const searchOk = !q ||
      (c.dataset.text ??= c.textContent.toLowerCase()).includes(q) ||
      c.dataset.repo.toLowerCase().includes(q) ||
      c.dataset.tags.toLowerCase().includes(q);
    const show = sevOk && groupOk && repoOk && searchOk && majorOk(c);
    c.classList.toggle('hidden', !show);
    if (show) visibleCards++;
  });

  document.getElementById('empty-digest').classList.toggle('hidden', visibleCards > 0 || cards.length === 0);
  updateDigestCount(releaseRecords);
  writeQuery(QUERY_SPEC, {
    sev: activeSev, group: activeGroup, repo: activeRepo,
    q: document.getElementById('search').value.trim(),
  });
}

// ── Data fetch ─────────────────────────────────────────────────────────────
async function loadDigest() {
  const loading = document.getElementById('loading');
  try {
    const { records, advisories, counts } = await loadDomain('dbt');
    allRecords = records;
    allAdvisories = advisories;
    loading.classList.add('hidden');
    const nonPkg = allRecords.filter(r => !NON_RELEASE_GROUPS.has(r.group));
    renderGrid(nonPkg);
    applyTabBadges(counts);
    updateDigestCount(nonPkg);
  } catch (err) {
    loading.className = 'empty-state';
    loading.textContent = `⚠ Failed to load: ${err.message}`;
  }
}

function updateDigestCount(records) {
  const shown = records.filter(r => sevPasses(r.analysis?.severity ?? 'none')).length;
  document.getElementById('digest-count').textContent = shown || '';
}

// ── Bento Grid ─────────────────────────────────────────────────────────────
function releaseCard(r, idx) {
  const a          = r.analysis ?? {};
  const severity   = a.severity ?? 'none';
  const allTags    = a.tags ?? [];
  const isPreRel   = allTags.includes('pre-release');
  const tags       = allTags.filter(t => t !== 'pre-release').slice(0, 3);
  const changes    = (a.key_changes ?? []).slice(0, 3);

  const changesList = changes.map(c => `<li>${renderInline(c)}</li>`).join('');
  const tagChips    = tags.map(t => `<span class="tag">${esc(t)}</span>`).join('');
  const preRelBadge = isPreRel
    ? `<span class="tag tag-prerelease">pre-release</span>`
    : '';

  return `<article class="card" data-idx="${idx}"
  data-repo="${esc(r.repo)}"
  data-group="${esc(r.group ?? '')}"
  data-tags="${esc(allTags.join(' '))}"
  data-severity="${esc(severity)}"
  data-major="${esc(majorOf(r.tag))}">
  <div class="card-header">
    <span class="card-repo">${esc(REPO_DISPLAY[r.repo] ?? r.repo.split('/')[1])}</span>
    <div style="display:flex;align-items:center;gap:6px;">${preRelBadge}<span class="sev sev-${safeSev(severity)}">${esc(severity)}</span></div>
  </div>
  <h3 class="card-title">${esc(r.name || r.tag)}</h3>
  <p class="card-date">${formatDate(r.published_at)}</p>
  <p class="card-summary">${renderInline(a.summary ?? '')}</p>
  ${changesList ? `<ul class="card-changes">${changesList}</ul>` : ''}
  <div class="card-footer">
    ${tagChips ? `<div class="tags">${tagChips}</div>` : '<div></div>'}
    <span class="card-cta">Details <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 6h7M6.5 3l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
  </div>
</article>`.trim();
}

// One row per dbt-core minor: latest release up front, every release listed (collapsed) below.
function minorCard(g, indexOf) {
  const latest = g.latest;
  const a = latest.analysis ?? {};
  const items = g.releases.map(r => {
    const sev = r.analysis?.severity ?? 'none';
    return `<li class="minor-item" data-severity="${esc(sev)}">
      <button type="button" class="minor-link" data-idx="${indexOf.get(r)}">${esc(r.tag)}</button>
      <span class="card-date">${formatDate(r.published_at)}</span>
      <span class="sev sev-${safeSev(sev)}">${esc(sev)}</span>
    </li>`;
  }).join('');

  return `<article class="card card-minor" data-idx="${indexOf.get(latest)}"
  data-repo="${esc(latest.repo)}"
  data-group="${esc(latest.group ?? '')}"
  data-tags="${esc((a.tags ?? []).join(' '))}"
  data-severity="${esc(g.maxSeverity)}"
  data-major="${g.major}">
  <div class="card-header">
    <span class="card-repo">dbt-core</span>
    <span class="sev sev-${safeSev(g.maxSeverity)}">${esc(g.maxSeverity)}</span>
  </div>
  <h3 class="card-title">dbt-core ${esc(g.label)}</h3>
  <p class="card-date">${g.releases.length} release${g.releases.length > 1 ? 's' : ''} · latest ${esc(latest.tag)} · ${formatDate(latest.published_at)}</p>
  <p class="card-summary">${renderInline(a.summary ?? '')}</p>
  <details class="minor-list">
    <summary>Releases <span class="minor-hidden"></span></summary>
    <ul>${items}</ul>
  </details>
</article>`.trim();
}

function renderGrid(records) {
  const grid = document.getElementById('grid');
  releaseRecords = records;
  if (!records.length) {
    document.getElementById('empty-digest').classList.remove('hidden');
    return;
  }

  const indexOf = new Map(records.map((r, i) => [r, i]));
  const minorRows = new Map(
    groupByMinor(records.filter(r => r.group === 'dbt-core')).map(g => [g.label, g])
  );
  const placed = new Set();
  grid.innerHTML = records.map((r, idx) => {
    if (r.group !== 'dbt-core') return releaseCard(r, idx);
    const label = minorOf(r.tag)?.label;
    if (!label || placed.has(label)) return '';
    placed.add(label);
    return minorCard(minorRows.get(label), indexOf);
  }).join('');

  applyFilters();

  grid.querySelectorAll('.card').forEach(el => {
    el.addEventListener('click', e => {
      const link = e.target.closest('.minor-link');
      if (link) return openDrawer(records[+link.dataset.idx]);
      if (e.target.closest('details')) return;
      const r = records[+el.dataset.idx];
      if (r) openDrawer(r);
    });
  });
}

// ── Security Advisories ────────────────────────────────────────────────────

// ── Helpers ────────────────────────────────────────────────────────────────
