'use strict';

import { esc, renderInline, formatDate, loadDomain, applyTabBadges } from '../common.js';


let allReleases = [];
const activeProducts = new Set();
const activeCategories = new Set();

document.addEventListener('DOMContentLoaded', () => {
  setupDrawer();
  setupSearch();
  loadReleases();
});

async function loadReleases() {
  const loading = document.getElementById('loading');
  try {
    const { records, counts } = await loadDomain('scaleway');
    allReleases = records.filter(r =>
      r.group === 'scaleway' || r.repo === 'scaleway/changelog'
    );
    loading.classList.add('hidden');
    applyTabBadges(counts);
    buildFacetDropdown('product', activeProducts, r => r.product);
    buildFacetChips('category-chips', activeCategories, r => r.category);
    render();
  } catch (err) {
    loading.className = 'empty-state';
    loading.textContent = `⚠ Failed to load: ${err.message}`;
  }
}

const FACET_DEFAULT_VISIBLE = 8;

function buildFacetChips(containerId, activeSet, getValue) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const counts = {};
  allReleases.forEach(r => {
    const v = getValue(r);
    if (v) counts[v] = (counts[v] ?? 0) + 1;
  });
  const values = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
  if (!values.length) {
    container.innerHTML = '';
    return;
  }

  let expanded = false;

  function renderChips() {
    const visible = expanded ? values : values.slice(0, FACET_DEFAULT_VISIBLE);
    const hiddenCount = values.length - visible.length;

    const chipsHtml = visible.map(v =>
      `<button type="button" class="chip${activeSet.has(v) ? ' active' : ''}" data-value="${esc(v)}">${esc(v)} <span class="chip-count">${counts[v]}</span></button>`
    ).join('');

    const toggleHtml = hiddenCount > 0
      ? `<button type="button" class="chip chip-toggle">+${hiddenCount} more</button>`
      : expanded && values.length > FACET_DEFAULT_VISIBLE
        ? `<button type="button" class="chip chip-toggle">Show less</button>`
        : '';

    container.innerHTML = chipsHtml + toggleHtml;

    container.querySelectorAll('.chip:not(.chip-toggle)').forEach(btn => {
      btn.addEventListener('click', () => {
        const v = btn.dataset.value;
        if (activeSet.has(v)) activeSet.delete(v);
        else activeSet.add(v);
        renderChips();
        render();
      });
    });

    const toggleBtn = container.querySelector('.chip-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        expanded = !expanded;
        renderChips();
      });
    }
  }

  renderChips();
}

function buildFacetDropdown(prefix, activeSet, getValue) {
  const btn      = document.getElementById(`${prefix}-dropdown-btn`);
  const label    = document.getElementById(`${prefix}-dropdown-label`);
  const panel    = document.getElementById(`${prefix}-dropdown-panel`);
  const wrap     = document.getElementById(`${prefix}-dropdown`);
  if (!btn || !panel || !wrap) return;

  const counts = {};
  allReleases.forEach(r => {
    const v = getValue(r);
    if (v) counts[v] = (counts[v] ?? 0) + 1;
  });
  const values = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
  if (!values.length) {
    wrap.classList.add('hidden');
    return;
  }

  function updateLabel() {
    if (!activeSet.size) label.textContent = 'All products';
    else if (activeSet.size === 1) label.textContent = [...activeSet][0];
    else label.textContent = `${activeSet.size} selected`;
  }

  panel.innerHTML = values.map(v => `
    <label class="facet-dropdown-item">
      <input type="checkbox" value="${esc(v)}" ${activeSet.has(v) ? 'checked' : ''} />
      <span>${esc(v)}</span>
      <span class="chip-count">${counts[v]}</span>
    </label>
  `).join('');

  panel.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      if (cb.checked) activeSet.add(cb.value);
      else activeSet.delete(cb.value);
      updateLabel();
      render();
    });
  });

  function openPanel() {
    panel.classList.remove('hidden');
    btn.setAttribute('aria-expanded', 'true');
  }
  function closePanel() {
    panel.classList.add('hidden');
    btn.setAttribute('aria-expanded', 'false');
  }

  btn.addEventListener('click', e => {
    e.stopPropagation();
    panel.classList.contains('hidden') ? openPanel() : closePanel();
  });
  document.addEventListener('click', e => {
    if (!wrap.contains(e.target)) closePanel();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePanel();
  });

  updateLabel();
}

function setupSearch() {
  document.getElementById('search').addEventListener('input', render);
}

function render() {
  const q = document.getElementById('search').value.trim().toLowerCase();

  let filtered = [...allReleases];
  filtered.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));

  if (activeProducts.size) {
    filtered = filtered.filter(r => activeProducts.has(r.product));
  }
  if (activeCategories.size) {
    filtered = filtered.filter(r => activeCategories.has(r.category));
  }
  if (q) {
    filtered = filtered.filter(r =>
      (r.name || r.tag || '').toLowerCase().includes(q) ||
      (r.analysis?.summary ?? '').toLowerCase().includes(q) ||
      (r.analysis?.tags ?? []).join(' ').toLowerCase().includes(q)
    );
  }

  const countEl = document.getElementById('scw-count');
  if (countEl) countEl.textContent = filtered.length || '';

  const grid  = document.getElementById('scw-grid');
  const empty = document.getElementById('empty-scw');

  if (!filtered.length) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  grid.innerHTML = filtered.map((r, idx) => {
    const a        = r.analysis ?? {};
    const tags     = a.tags ?? [];
    const tagChips = tags.map(t => `<span class="tag">${esc(t)}</span>`).join('');

    return `<article class="card" data-idx="${idx}">
  <div class="card-header">
    <span class="card-repo">Scaleway</span>
  </div>
  <h3 class="card-title">${esc(r.name || r.tag)}</h3>
  <p class="card-date">${formatDate(r.published_at)}</p>
  <p class="card-summary">${renderInline(a.summary ?? '')}</p>
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
  const a = record.analysis ?? {};

  document.getElementById('drawer-repo').textContent = 'Scaleway';
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
