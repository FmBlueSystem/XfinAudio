import assert from 'node:assert/strict';
import test from 'node:test';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';

const require = createRequire(import.meta.url);
const reads = require('../.out/main/ipc-reads.js');

const idle = {legacy: false, offline: false, profiles: false, serato: false, optionalAi: false, loudness: false, library: false, dialog: false, job: false};
const busy = (patch) => ({...idle, ...patch});
const SOURCES = ['legacy', 'offline', 'profiles', 'serato', 'optionalAi', 'loudness', 'library', 'dialog', 'job'];
const readMain = () => readFile(new URL('../src/main.ts', import.meta.url), 'utf8');
const readServer = () => readFile(new URL('../../src/xfinaudio/headless/server.py', import.meta.url), 'utf8');

// The reviewed contract: read-only actions admitted while an exclusive task owns the host.
const ALLOWED_ACTIONS = [
  'cancelCurrent', 'comparePlaylists', 'getAiStatus', 'getLibraryStatus', 'getLiveStatus', 'getLoudnessStatus',
  'getMetadataReport', 'getPreferences', 'getPrepCatalog', 'getProfileSettings', 'getProfileStatus',
  'listDeletedPlaylists', 'listLibrary', 'listPlaylists', 'openPlaylist', 'prepSettings', 'queryLibrary',
  'searchPlaylists', 'setDraftDirty',
];
// The same set without the two always-allowed local actions.
const READ_ONLY_ACTIONS = [
  'comparePlaylists', 'getAiStatus', 'getLibraryStatus', 'getLiveStatus', 'getLoudnessStatus',
  'getMetadataReport', 'getPreferences', 'getPrepCatalog', 'getProfileSettings', 'getProfileStatus',
  'listDeletedPlaylists', 'listLibrary', 'listPlaylists', 'openPlaylist', 'prepSettings', 'queryLibrary',
  'searchPlaylists',
];
// The core methods `JsonlServer.process_line` answers inline while its single worker runs.
const INLINE_CORE_METHODS = [
  'ai.status', 'library.list', 'library.query', 'live.status', 'loudness.status', 'metadata.report',
  'playlist.compare', 'playlist.deleted.list', 'playlist.list', 'playlist.open', 'playlist.search',
  'prep.catalog', 'prep.settings.get', 'profiles.settings.get', 'profiles.status', 'settings.get',
  'track.resolve',
];

test('an idle host still dispatches every action', () => {
  assert.equal(reads.exclusiveInFlight(idle), false);
  for (const method of ['previewLoudness', 'runAiRequest', 'getLibraryStatus', 'getPrepCatalog', 'listLibrary', 'getMetadataReport', 'cancelCurrent']) {
    assert.doesNotThrow(() => reads.assertDispatchable(method, idle), `${method} must dispatch on an idle host`);
  }
});

test('every exclusive source is exclusive', () => {
  for (const source of SOURCES) {
    assert.equal(reads.exclusiveInFlight(busy({[source]: true})), true, `${source} must hold the host`);
  }
});

test('every reviewed read keeps answering while any exclusive task holds the host', () => {
  for (const method of READ_ONLY_ACTIONS) {
    for (const source of SOURCES) {
      assert.doesNotThrow(() => reads.assertDispatchable(method, busy({[source]: true})), `${method} must survive ${source}`);
    }
  }
});

test('cancellation and local draft bookkeeping keep running while an exclusive task holds the host', () => {
  for (const method of ['cancelCurrent', 'setDraftDirty']) {
    assert.doesNotThrow(() => reads.assertDispatchable(method, busy({optionalAi: true})), `${method} must stay available`);
  }
});

test('the whitelist is exactly the reads this process can answer without the core worker', () => {
  assert.deepEqual([...reads.READ_ONLY_ACTIONS].sort(), READ_ONLY_ACTIONS);
  assert.deepEqual([...reads.ALWAYS_ALLOWED_ACTIONS].sort(), ['cancelCurrent', 'setDraftDirty']);
  assert.deepEqual([...reads.LOCAL_READ_ACTIONS].sort(), ['getLibraryStatus']);
  assert.equal(reads.isAllowedWhileBusy('runAiRequest'), false);
  assert.equal(reads.isAllowedWhileBusy('savePreferences'), false);
  assert.equal(reads.BUSY_MESSAGE, '[busy] Another task is still running');
});

test('every admitted read maps to an inline core query and every inline query is reachable', () => {
  const mapped = new Set(Object.values(reads.READ_ONLY_CORE));
  for (const coreMethod of mapped) {
    assert.ok(reads.INLINE_CORE_METHODS.has(coreMethod), `${coreMethod} must be an inline core method`);
  }
  assert.deepEqual([...reads.INLINE_CORE_METHODS].sort(), INLINE_CORE_METHODS, 'the inline set must be exactly the reviewed core queries');
  assert.deepEqual([...reads.INLINE_CORE_METHODS].filter((method) => !mapped.has(method)), ['track.resolve'], 'only track.resolve is inline without a read action');
  assert.deepEqual([...Object.keys(reads.READ_ONLY_CORE)].sort(), READ_ONLY_ACTIONS.filter((action) => action !== 'getLibraryStatus'));
});

test('the Electron inline set matches the Python core inline set', async () => {
  const server = await readServer();
  const block = server.match(/INLINE_METHODS = frozenset\(\s*\{([\s\S]*?)\}\s*\)/);
  assert.ok(block, 'server.py must declare INLINE_METHODS');
  const python = [...block[1].matchAll(/"([a-z][a-z._]*)"/g)].map((match) => match[1]).sort();
  assert.deepEqual(python, INLINE_CORE_METHODS, 'both boundaries must agree on exactly which queries answer inline');
  assert.deepEqual([...reads.INLINE_CORE_METHODS].sort(), python);
});

test('every action outside the whitelist keeps the exact busy refusal', async () => {
  const main = await readMain();
  const dispatched = [...main.matchAll(/case '(\w+)':/g)].map((match) => match[1]);
  assert.ok(dispatched.length > 40, 'main.ts must dispatch actions');
  const refused = dispatched.filter((method) => !reads.isAllowedWhileBusy(method));
  assert.ok(refused.length > 40, 'the refusal boundary must cover the whole dispatch table');
  for (const method of refused) {
    for (const source of SOURCES) {
      assert.throws(
        () => reads.assertDispatchable(method, busy({[source]: true})),
        (error) => error.message === '[busy] Another task is still running',
        `${method} must keep failing while ${source} is running`,
      );
    }
  }
  const allowed = dispatched.filter((method) => reads.isAllowedWhileBusy(method)).sort();
  assert.deepEqual(allowed, ALLOWED_ACTIONS, 'only the reviewed reads may pass a busy host');
  for (const method of [...reads.READ_ONLY_ACTIONS, ...reads.ALWAYS_ALLOWED_ACTIONS]) {
    assert.ok(dispatched.includes(method), `${method} must be a dispatched action`);
  }
});

test('main.ts routes its busy boundary through the reviewed whitelist', async () => {
  const main = await readMain();
  assert.match(main, /import\s*\{assertDispatchable,\s*INLINE_CORE_METHODS\}\s*from '\.\/ipc-reads';/, 'the boundary decision must live in ipc-reads');
  assert.match(main, /assertDispatchable\(method,\s*\{legacy:legacy\.busy,offline:offline\.busy,profiles:profiles\.busy,serato:serato\.busy,optionalAi:optionalAi\.busy,loudness:loudness\.busy,library:libraryHost\.busy,dialog:dialogOpen,job:current!==null\}\)/, 'every exclusive source must be reported to the boundary');
  assert.doesNotMatch(main, /!\[[^\]]*'setDraftDirty'[^\]]*\]\.includes\(method\)/, 'the inline always-allowed array must be gone');
});

test('the shared core request only lets reviewed inline queries bypass the active job', async () => {
  const main = await readMain();
  assert.match(
    main,
    /if\(current\)\{[\s\S]*?if\(INLINE_CORE_METHODS\.has\(method\)\)return core\.request\(method,params\);\s*throw new Error\('Another task is still running'\);\s*\}/,
    'run must forward only inline queries while a job is active',
  );
});
