/* Group dbt-core releases by minor version (pure, no DOM). */
'use strict';

const SEV_RANK = { critical: 4, high: 3, medium: 2, low: 1, none: 0, unknown: 0 };

export function minorOf(tag) {
  const m = /^v?(\d+)\.(\d+)\./.exec(tag ?? '');
  return m ? { major: +m[1], minor: +m[2], label: `v${m[1]}.${m[2]}` } : null;
}

/**
 * @param {Array} records dbt-core release records (any order)
 * @returns {Array<{label, major, minor, releases, latest, maxSeverity}>} newest minor first,
 *   releases newest first. Records whose tag has no major.minor are dropped.
 */
export function groupByMinor(records) {
  const groups = new Map();
  for (const r of records) {
    const v = minorOf(r.tag);
    if (!v) continue;
    if (!groups.has(v.label)) groups.set(v.label, { ...v, releases: [] });
    groups.get(v.label).releases.push(r);
  }
  const date = r => String(r.published_at ?? '');
  return [...groups.values()]
    .map(g => {
      g.releases.sort((a, b) => date(b).localeCompare(date(a)));
      const sevOf = r => r.analysis?.severity ?? 'none';
      g.latest = g.releases[0];
      g.maxSeverity = g.releases.map(sevOf).reduce(
        (best, s) => ((SEV_RANK[s] ?? 0) > (SEV_RANK[best] ?? 0) ? s : best), 'none');
      return g;
    })
    .sort((a, b) => b.major - a.major || b.minor - a.minor);
}
