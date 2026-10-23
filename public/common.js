/* Helpers shared by every page. */
'use strict';

export const R2_BASE = 'https://pub-d7a866e02d744f3fb57bc3859858a5df.r2.dev';
export const MANIFEST_URL = `${R2_BASE}/manifest.json`;

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
