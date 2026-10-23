/* Helpers shared by every page. */
'use strict';

const R2_BASE = 'https://pub-d7a866e02d744f3fb57bc3859858a5df.r2.dev';
const MANIFEST_URL = `${R2_BASE}/manifest.json`;

const _VALID_SEV = new Set(['critical', 'high', 'medium', 'low', 'none', 'unknown']);
export function safeSev(s) { return _VALID_SEV.has(s) ? s : 'none'; }

export function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function renderInline(str) {
  return esc(str).replace(/`([^`]+)`/g, '<code>$1</code>');
}

export function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
  } catch { return iso; }
}

// ── Data loading ───────────────────────────────────────────────────────────
async function getJson(url, opts) {
  const resp = await fetch(url, opts);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} (${url.split('/').pop()})`);
  return resp.json();
}

const NON_RELEASE_GROUPS = new Set(['dbt-packages', 'bigquery', 'lakehouse', 'scaleway']);

// Same figures as `compute_tab_counts` in src/digest.py; only used when the manifest has no `counts`.
function countsFromDigest(records, advisories) {
  const n = g => records.filter(r => r.group === g).length;
  return {
    releases: records.filter(r => !NON_RELEASE_GROUPS.has(r.group)).length,
    packages: new Set(records.filter(r => r.group === 'dbt-packages').map(r => r.repo)).size,
    bigquery: n('bigquery'),
    lakehouse: n('lakehouse'),
    scaleway: n('scaleway'),
    advisories: advisories.length,
  };
}

/**
 * Load one domain ('dbt' | 'gcp' | 'scaleway' | 'security'). Falls back to the combined
 * digest while the manifest has no per-domain digests.
 */
export async function loadDomain(domain) {
  const manifest = await getJson(MANIFEST_URL, { cache: 'no-store' });
  const data = await getJson(`${R2_BASE}/${manifest.digests?.[domain] ?? manifest.digest}`);
  const records = Array.isArray(data) ? data : (data.releases ?? []);
  const advisories = Array.isArray(data) ? [] : (data.advisories ?? []);
  return { records, advisories, counts: manifest.counts ?? countsFromDigest(records, advisories) };
}

// ── Tab badges ─────────────────────────────────────────────────────────────
const TAB_BADGES = [
  ['releases',   ['release-count', 'digest-count'], null],
  ['advisories', ['advisory-count', 'total-count'], null],
  ['packages',   ['pkg-count'], n => `${n} packages tracked · latest release per package`],
  ['bigquery',   ['bq-count'],  n => `${n} release windows tracked`],
  ['lakehouse',  ['lh-count'],  n => `${n} release windows tracked`],
  ['scaleway',   ['scw-count'], n => `${n} items tracked`],
];

export function applyTabBadges(counts) {
  for (const [key, ids, title] of TAB_BADGES) {
    const n = counts[key] ?? 0;
    for (const id of ids) {
      const el = document.getElementById(id);
      if (!el) continue;
      el.textContent = n || '';
      if (title) el.title = title(n);
    }
  }
}

// ── Filter state in the URL ────────────────────────────────────────────────
/**
 * spec: { key: { def, allowed? } }. Unknown or invalid values fall back to the default.
 */
export function readQuery(spec, search = location.search) {
  const params = new URLSearchParams(search);
  const state = {};
  for (const [key, { def, allowed }] of Object.entries(spec)) {
    const v = params.get(key);
    state[key] = v !== null && (!allowed || allowed.includes(v)) ? v : def;
  }
  return state;
}

/** Write the state with replaceState; values equal to their default are omitted. */
export function writeQuery(spec, state) {
  const params = new URLSearchParams();
  for (const [key, { def }] of Object.entries(spec)) {
    if (state[key] !== def && state[key] !== '') params.set(key, state[key]);
  }
  const qs = params.toString();
  history.replaceState(null, '', `${location.pathname}${qs ? `?${qs}` : ''}${location.hash}`);
}
