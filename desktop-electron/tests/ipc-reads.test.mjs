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

test('an idle host still dispatches every action', () => {
  assert.equal(reads.exclusiveInFlight(idle), false);
  for (const method of ['previewLoudness', 'runAiRequest', 'getLibraryStatus', 'getPrepCatalog', 'cancelCurrent']) {
    assert.doesNotThrow(() => reads.assertDispatchable(method, idle), `${method} must dispatch on an idle host`);
  }
});

test('every exclusive source is exclusive', () => {
  for (const source of SOURCES) {
    assert.equal(reads.exclusiveInFlight(busy({[source]: true})), true, `${source} must hold the host`);
  }
});

test('the inline catalog read keeps answering while an exclusive task holds the host', () => {
  // The core's single worker serves prep.catalog inline, so this read needs no job slot.
  for (const source of SOURCES) {
    assert.doesNotThrow(() => reads.assertDispatchable('getPrepCatalog', busy({[source]: true})), `getPrepCatalog must survive ${source}`);
  }
});

test('the cached watcher status keeps answering while an exclusive task holds the host', () => {
  // libraryHost.status is read from the native watcher cache and never reaches the core.
  for (const source of SOURCES) {
    assert.doesNotThrow(() => reads.assertDispatchable('getLibraryStatus', busy({[source]: true})), `getLibraryStatus must survive ${source}`);
  }
});

test('cancellation and local draft bookkeeping keep running while an exclusive task holds the host', () => {
  for (const method of ['cancelCurrent', 'setDraftDirty']) {
    assert.doesNotThrow(() => reads.assertDispatchable(method, busy({optionalAi: true})), `${method} must stay available`);
  }
});

test('the whitelist is exactly the reads this process can answer without the core worker', () => {
  assert.deepEqual([...reads.READ_ONLY_ACTIONS].sort(), ['getLibraryStatus', 'getPrepCatalog']);
  assert.deepEqual([...reads.ALWAYS_ALLOWED_ACTIONS].sort(), ['cancelCurrent', 'setDraftDirty']);
  assert.equal(reads.isAllowedWhileBusy('runAiRequest'), false);
  assert.equal(reads.isAllowedWhileBusy('listPlaylists'), false);
  assert.equal(reads.BUSY_MESSAGE, '[busy] Another task is still running');
});

test('every action outside the whitelist keeps the exact busy refusal', async () => {
  const main = await readMain();
  const dispatched = [...main.matchAll(/case '(\w+)':/g)].map((match) => match[1]);
  assert.ok(dispatched.length > 0, 'main.ts must dispatch actions');
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
  assert.deepEqual(allowed, ['cancelCurrent', 'getLibraryStatus', 'getPrepCatalog', 'setDraftDirty'], 'only the reviewed reads may pass a busy host');
  for (const method of [...reads.READ_ONLY_ACTIONS, ...reads.ALWAYS_ALLOWED_ACTIONS]) {
    assert.ok(dispatched.includes(method), `${method} must be a dispatched action`);
  }
});

test('main.ts routes its busy boundary through the reviewed whitelist', async () => {
  const main = await readMain();
  assert.match(main, /import\s*\{assertDispatchable\}\s*from '\.\/ipc-reads';/, 'the boundary decision must live in ipc-reads');
  assert.match(main, /assertDispatchable\(method,\s*\{legacy:legacy\.busy,offline:offline\.busy,profiles:profiles\.busy,serato:serato\.busy,optionalAi:optionalAi\.busy,loudness:loudness\.busy,library:libraryHost\.busy,dialog:dialogOpen,job:current!==null\}\)/, 'every exclusive source must be reported to the boundary');
  assert.doesNotMatch(main, /!\[[^\]]*'setDraftDirty'[^\]]*\]\.includes\(method\)/, 'the inline always-allowed array must be gone');
});
