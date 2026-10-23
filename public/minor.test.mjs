import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupByMinor, minorOf } from './minor.js';

const rel = (tag, sev, day) => ({ tag, published_at: `2026-09-${day}`, analysis: { severity: sev } });

test('one group per minor, newest minor first, max severity', () => {
  const groups = groupByMinor([
    rel('v1.11.1', 'low', '01'), rel('v2.0.0', 'critical', '14'), rel('v1.11.0', 'high', '02'),
    rel('v2.0.1', 'none', '15'), rel('v1.12.0', 'medium', '10'),
  ]);
  assert.deepEqual(groups.map(g => g.label), ['v2.0', 'v1.12', 'v1.11']);
  assert.equal(groups[0].maxSeverity, 'critical');
  assert.equal(groups[2].maxSeverity, 'high');
  assert.equal(groups[0].latest.tag, 'v2.0.1');
  assert.deepEqual(groups[2].releases.map(r => r.tag), ['v1.11.0', 'v1.11.1']);
});

test('v1.10 ordering uses numbers, not strings', () => {
  const labels = groupByMinor([rel('v1.9.0', 'none', '01'), rel('v1.10.0', 'none', '02')]).map(g => g.label);
  assert.deepEqual(labels, ['v1.10', 'v1.9']);
});

test('tags without major.minor are dropped', () => {
  assert.equal(minorOf('nightly'), null);
  assert.deepEqual(groupByMinor([rel('nightly', 'none', '01')]), []);
});
