import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { audioUrl, filterTracks, formatDuration, OperationGate, validateTrackCount } from '../renderer/model.ts';

const tracks = [
  { id: 'a', title: '<img onerror=alert(1)>', artist: 'Björk', bpm: 124, key: '8A', energy: 6, duration: 245 },
  { id: 'b', title: 'Midnight', artist: 'Other', bpm: null, key: null, energy: null, duration: null },
];

test('library search is case-insensitive and filters missing metadata without changing source tracks', () => {
  assert.deepEqual(filterTracks(tracks, 'BJÖRK', 'all'), [tracks[0]]);
  assert.deepEqual(filterTracks(tracks, '', 'ready'), [tracks[0]]);
  assert.deepEqual(filterTracks(tracks, '', 'incomplete'), [tracks[1]]);
  assert.equal(tracks.length, 2);
});

test('duration handles missing, invalid, normal and long recordings', () => {
  assert.equal(formatDuration(null), '—');
  assert.equal(formatDuration(Number.NaN), '—');
  assert.equal(formatDuration(-1), '—');
  assert.equal(formatDuration(245.9), '4:05');
  assert.equal(formatDuration(3723), '1:02:03');
});

test('prep count permits only integers in the supported 2 to 100 range', () => {
  for (const value of ['2', '100', '20']) assert.equal(validateTrackCount(value), Number(value));
  for (const value of ['', '1', '101', '2.5', 'twenty', 'Infinity']) assert.equal(validateTrackCount(value), null);
});

test('preview addresses use only opaque IDs and reject paths or URL injection', () => {
  assert.equal(audioUrl('track-a_123'), 'xfin-audio://track/track-a_123');
  for (const value of ['', '../secret', 'file:///x', 'a?x=2', 'a/b']) assert.throws(() => audioUrl(value));
});

test('operation gate prevents double submit and keeps cancelled operations busy until settled', () => {
  const gate = new OperationGate();
  const first = gate.begin(0);
  assert.ok(first);
  assert.equal(gate.begin(0), null);
  assert.equal(gate.isCurrent(first), true);
  gate.requestCancel();
  assert.equal(gate.isCurrent(first), false);
  assert.equal(gate.busy, true);
  assert.equal(gate.begin(1), null);
  assert.equal(gate.finish(first), true);
  const second = gate.begin(1);
  assert.ok(second);
  assert.equal(gate.isCurrent(first), false);
  assert.equal(gate.finish(first), false);
  assert.equal(gate.isCurrent(second), true);
});

test('renderer supplies four route panels, one persistent player, accessible progress, and local assets', async () => {
  const html = await readFile(new URL('../renderer/index.html', import.meta.url), 'utf8');
  for (const name of ['library', 'prep', 'review', 'playlists']) assert.match(html, new RegExp(`id="page-${name}"`));
  assert.equal((html.match(/<audio\b/g) || []).length, 1);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /id="cancel-operation"/);
  assert.match(html, /type="module" src="\.\/app.js"/);
  assert.doesNotMatch(html, /https?:\/\//);
});

test('renderer writes metadata as text and exposes cancellable, explicit-save flows without Node access', async () => {
  const app = await readFile(new URL('../renderer/app.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(app, /\.innerHTML\s*=|\beval\(|require\(|node:/);
  assert.match(app, /\.textContent\s*=/);
  assert.match(app, /cancelCurrent/);
  assert.match(app, /reviewId/);
  assert.match(app, /routeRevision/);
  const player = await readFile(new URL('../renderer/player.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(player, /new Audio\(/);
  assert.match(player, /audio\.pause\(\)/);
  assert.match(player, /audio\.currentTime\s*=/);
});

test('review save eligibility rejects saved, blocked, empty, stale and already-saved candidates', async () => {
  const { canSaveReview } = await import('../renderer/model.ts');
  const review = { reviewId: 'fresh', tracks, blockers: [], warnings: [], name: 'Set', variant: 'balanced', readiness: 'ready' };
  assert.equal(canSaveReview(review), true);
  assert.equal(canSaveReview({ ...review, readiness: 'needs_review' }), true);
  for (const invalid of [null, { ...review, variant: 'saved' }, { ...review, readiness: 'blocked' }, { ...review, blockers: ['Missing metadata'] }, { ...review, reviewId: '' }, { ...review, tracks: [] }, { ...review, canSave: false }]) assert.equal(canSaveReview(invalid), false);
});

test('optional Prep name has a valid Spanish fallback before invoking the host', async () => {
  const { normalizePrepName } = await import('../renderer/model.ts');
  assert.equal(normalizePrepName(''), 'Sesión equilibrada');
  assert.equal(normalizePrepName('   '), 'Sesión equilibrada');
  assert.equal(normalizePrepName('  Mi sesión  '), 'Mi sesión');
  const app = await readFile(new URL('../renderer/app.ts', import.meta.url), 'utf8');
  assert.match(app, /const name = normalizePrepName\(/);
});

test('core disconnect is handled before operation-only progress filters and gates mutations', async () => {
  const { isCoreFailure } = await import('../renderer/model.ts');
  assert.equal(isCoreFailure({ operation: 'core', phase: 'error' }), true);
  assert.equal(isCoreFailure({ operation: 'scan', phase: 'error' }), false);
  assert.equal(isCoreFailure({ operation: 'core', phase: 'ready' }), false);
  const app = await readFile(new URL('../renderer/app.ts', import.meta.url), 'utf8');
  assert.ok(app.indexOf('if (isCoreFailure(event))') < app.indexOf('if (!gate.busy || gate.cancelled || !cancellable)'));
  assert.match(app, /coreAvailable = false/);
  assert.match(app, /button.disabled = gate.busy \|\| !coreAvailable/);
  assert.match(app, /if \(!coreAvailable\) \{/);
});
