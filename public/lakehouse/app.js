'use strict';

import { esc, renderInline, formatDate, safeSev, loadDomain, applyTabBadges } from '../common.js';


let allReleases = [];
let activeTag = 'all';
let activeSev = 'all';

document.addEventListener('DOMContentLoaded', () => {
  setupDrawer();
  setupSearch();
  setupSevSelect();
  loadReleases();
});

async function loadReleases() {
  const loading = document.getElementById('loading');
  try {
    const { records, counts } = await loadDomain('gcp');
    allReleases = records.filter(r =>
      r.group === 'lakehouse' || r.repo === 'google/lakehouse'
    );
    loading.classList.add('hidden');
    applyTabBadges(counts);
    buildTagFilters(allReleases);
    render();
  } catch (err) {
    loading.className = 'empty-state';
    loading.textContent = `⚠ Failed to load: ${err.message}`;
  }
}

function buildTagFilters(releases) {
  const tagCounts = {};
  releases.forEach(r => {
    (r.analysis?.tags ?? []).forEach(t => {
      tagCounts[t] = (tagCounts[t] ?? 0) + 1;
    });
  });
  const tags = Object.keys(tagCounts).sort();
  if (!tags.length) return;
  const select = document.getElementById('tag-select');
  select.innerHTML = `<option value="all">All tags</option>` +
    tags.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join('');
  select.addEventListener('change', e => {
    activeTag = e.target.value;
    render();
  });
}

function setupSevSelect() {
  document.getElementById('sev-select').addEventListener('change', e => {
    activeSev = e.target.value;
    render();
  });
}

function setupSearch() {
  document.getElementById('search').addEventListener('input', render);
}

function render() {
  const q = document.getElementById('search').value.trim().toLowerCase();

  let filtered = [...allReleases];
  filtered.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));

  if (activeTag !== 'all') {
    filtered = filtered.filter(r => (r.analysis?.tags ?? []).includes(activeTag));
  }
  if (activeSev !== 'all') {
    filtered = filtered.filter(r => (r.analysis?.severity ?? 'none') === activeSev);
  }
  if (q) {
    filtered = filtered.filter(r =>
      (r.name || r.tag || '').toLowerCase().includes(q) ||
      (r.analysis?.summary ?? '').toLowerCase().includes(q) ||
      (r.analysis?.tags ?? []).join(' ').toLowerCase().includes(q) ||
      (r.analysis?.key_changes ?? []).join(' ').toLowerCase().includes(q) ||
      (r.analysis?.breaking_changes ?? []).join(' ').toLowerCase().includes(q)
    );
  }

  const countEl = document.getElementById('lh-count');
  if (countEl) countEl.textContent = filtered.length || '';

  const grid  = document.getElementById('lh-grid');
  const empty = document.getElementById('empty-lh');

  if (!filtered.length) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  grid.innerHTML = filtered.map((r, idx) => {
    const a        = r.analysis ?? {};
    const severity = a.severity ?? 'none';
    const tags     = a.tags ?? [];
    const changes  = (a.key_changes ?? []).slice(0, 3);
    const hasBreaking = (a.breaking_changes ?? []).length > 0;

    const changesList = changes.map(c => `<li>${renderInline(c)}</li>`).join('');
    const tagChips    = tags.map(t => `<span class="tag">${esc(t)}</span>`).join('');

    return `<article class="card" data-idx="${idx}">
  <div class="card-header">
    <span class="card-repo">Lakehouse</span>
    <span class="sev sev-${safeSev(severity)}">${esc(severity)}</span>
  </div>
  <h3 class="card-title">${esc(r.name || r.tag)}</h3>
  <p class="card-date">${formatDate(r.published_at)}</p>
  ${hasBreaking ? `<p class="card-breaking-hint">⚠ Breaking changes</p>` : ''}
  <p class="card-summary">${renderInline(a.summary ?? '')}</p>
  ${changesList ? `<ul class="card-changes">${changesList}</ul>` : ''}
  <div class="card-footer">
    ${tagChips ? `<div class="tags">${tagChips}</div>` : '<div></div>'}
    <span class="card-cta">Details <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2.5 6h7M6.5 3l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
  </div>
</article>`.trim();
  }).join('');

  grid.querySelectorAll('.card').forEach(el => {
    el.addEventListener('click', () => {
      const r = filtered[+el.dataset.idx];
      if (r) openDrawer(r);
    });
  });
}

// ── Drawer ──────────────────────────────────────────────────────────────────
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

  document.getElementById('drawer-repo').textContent = 'Lakehouse';
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

  const breakingWrap = document.getElementById('drawer-breaking-wrap');
  const breakingList = document.getElementById('drawer-breaking');
  const breaking = a.breaking_changes ?? [];
  if (breaking.length) {
    breakingList.innerHTML = breaking.map(c => `<li>${renderInline(c)}</li>`).join('');
    breakingWrap.classList.remove('hidden');
  } else {
    breakingWrap.classList.add('hidden');
  }

  const costWrap = document.getElementById('drawer-cost-wrap');
  const costEl   = document.getElementById('drawer-cost');
  const costText = a.cost_and_performance_impact ?? '';
  if (costText) {
    costEl.innerHTML = renderInline(costText);
    costWrap.classList.remove('hidden');
  } else {
    costWrap.classList.add('hidden');
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

  document.getElementById('drawer-link').href = record.html_url ?? '#';

  const backdrop = document.getElementById('drawer-backdrop');
  const drawer   = document.getElementById('drawer');
  backdrop.classList.remove('hidden');
  drawer.classList.remove('hidden');
  requestAnimationFrame(() => drawer.classList.add('open'));
  document.body.style.overflow = 'hidden';
}

// ── Helpers ──────────────────────────────────────────────────────────────────
