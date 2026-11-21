import test from 'node:test';
import assert from 'node:assert/strict';
import * as nodeFs from 'node:fs/promises';
import {mkdtemp, readFile, readdir, rm, stat, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';

const require = createRequire(import.meta.url);
const setup = require('../.out/main/preview-setup.js');
const {validateRequest} = require('../.out/main/security.js');
const reads = require('../.out/main/ipc-reads.js');
const {validatePreviewSetup, createPreviewSetupStore, PREVIEW_SETUP_FILE, PREVIEW_SETUP_MAX_BYTES} = setup;

const read = (file) => readFile(new URL(`../src/${file}`, import.meta.url), 'utf8');
const scratchDir = () => mkdtemp('/private/tmp/xfin-preview-setup-');
const EMPTY = {output: null, calibration: {}};
const store = (directory) => createPreviewSetupStore({directory, fs: nodeFs});
const setupFile = (directory) => path.join(directory, PREVIEW_SETUP_FILE);
const saved = {output: {label: 'Rane FOUR', pair: '5-6'}, calibration: {'Rane FOUR': {'5-6': 'phones', '1-2': 'silent'}, FLX4: {'1-2': 'channel:2', '3-4': 'room'}}};

test('a valid preview setup round-trips through save and load', async () => {
  const directory = await scratchDir();
  try {
    const fs = store(directory);
    assert.equal(await fs.save(saved), null, 'saving answers nothing, so no path can cross');
    assert.deepEqual(await fs.load(), saved, 'the stored value must come back unchanged');

    // The half-chosen output of S11 (a label chosen, no pair) and the system output both pass.
    for (const value of [{output: {label: null, pair: '1-2'}, calibration: {}}, {output: null, calibration: {}}, {output: {label: 'Salida', pair: '13-14'}, calibration: {'A': {'9-10': 'phones'}}}]) {
      assert.doesNotThrow(() => validatePreviewSetup(value), `${JSON.stringify(value)} must be a valid setup`);
      await fs.save(value);
      assert.deepEqual(await fs.load(), value);
    }
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test('the stored file is private and leaves no temporary file behind', async () => {
  const directory = await scratchDir();
  try {
    const fs = store(directory);
    await fs.save(saved);
    assert.equal((await stat(setupFile(directory))).mode & 0o777, 0o600, 'the setup file must be readable by its owner only');
    assert.deepEqual(await readdir(directory), [PREVIEW_SETUP_FILE], 'a rename must leave no temporary file next to it');
    assert.deepEqual(JSON.parse(await readFile(setupFile(directory), 'utf8')), saved);

    // A second save replaces the first through the same atomic path.
    await fs.save({output: null, calibration: {}});
    assert.deepEqual(await readdir(directory), [PREVIEW_SETUP_FILE], 'replacing the file must leave no temporary file behind');
    assert.equal((await stat(setupFile(directory))).mode & 0o777, 0o600);
    assert.deepEqual(await fs.load(), EMPTY);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test('an absent, unreadable, oversized or invalid file reads as an empty setup', async () => {
  const directory = await scratchDir();
  try {
    const fs = store(directory);
    // Absent: nothing has been chosen yet.
    assert.deepEqual(await fs.load(), EMPTY);

    const invalid = {
      corrupt: '{not json',
      scalar: '"phones"',
      list: '[{"output":null}]',
      extraKey: JSON.stringify({...saved, path: '/Users/someone/Music'}),
      missingKey: JSON.stringify({output: null}),
      prototypeLabel: '{"output":null,"calibration":{"__proto__":{"1-2":"phones"}}}',
      badRole: JSON.stringify({output: null, calibration: {A: {'1-2': 'headphones'}}}),
      oversized: 'x'.repeat(PREVIEW_SETUP_MAX_BYTES + 1),
    };
    assert.equal(PREVIEW_SETUP_MAX_BYTES, 64 * 1024, 'the oversize bound is the one the spec names');
    for (const [name, content] of Object.entries(invalid)) {
      await writeFile(setupFile(directory), content);
      assert.deepEqual(await fs.load(), EMPTY, `a ${name} file must read as an empty setup`);
    }

    // A file at the bound but unparseable is still empty, never a throw.
    await writeFile(setupFile(directory), ' '.repeat(PREVIEW_SETUP_MAX_BYTES));
    assert.deepEqual(await fs.load(), EMPTY);

    // Unreadable: the name is a directory, so opening it fails.
    await rm(setupFile(directory));
    await nodeFs.mkdir(setupFile(directory));
    assert.deepEqual(await fs.load(), EMPTY);

    // An empty file is corrupt, not an empty setup that was saved.
    await rm(setupFile(directory), {recursive: true});
    await writeFile(setupFile(directory), '');
    assert.deepEqual(await fs.load(), EMPTY);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

const labels = (count) => Object.fromEntries(Array.from({length: count}, (_, index) => [`Label ${index + 1}`, {'1-2': 'phones'}]));
const pairs = (count) => Object.fromEntries(Array.from({length: count}, (_, index) => [`${index + 1}-${index + 2}`, 'silent']));

test('every invalid shape of the preview setup is refused', () => {
  const invalid = {
    'a non-object': 'Rane FOUR',
    'a list': [saved],
    'null': null,
    'an extra key': {...saved, path: '/Users/someone/Music'},
    'no output': {calibration: {}},
    'no calibration': {output: null},
    'a non-object output': {output: 'Rane FOUR', calibration: {}},
    'an output with an extra key': {output: {label: 'Rane FOUR', pair: '1-2', deviceId: 'x'}, calibration: {}},
    'a bad pair': {output: {label: 'Rane FOUR', pair: '1-2-3'}, calibration: {}},
    'a three digit pair': {output: {label: 'Rane FOUR', pair: '123-4'}, calibration: {}},
    'an en dash pair': {output: {label: 'Rane FOUR', pair: '1–2'}, calibration: {}},
    'a numeric pair': {output: {label: 'Rane FOUR', pair: 12}, calibration: {}},
    'an empty label': {output: {label: '', pair: '1-2'}, calibration: {}},
    'a long label': {output: {label: 'x'.repeat(201), pair: '1-2'}, calibration: {}},
    'a non-string label': {output: {label: 7, pair: '1-2'}, calibration: {}},
    'a list of calibration labels': {output: null, calibration: []},
    'a non-object calibration': {output: null, calibration: 'phones'},
    'a bad role': {output: null, calibration: {A: {'1-2': 'headphones'}}},
    'a channel above four': {output: null, calibration: {A: {'1-2': 'channel:5'}}},
    'a channel below one': {output: null, calibration: {A: {'1-2': 'channel:0'}}},
    'an uppercase role': {output: null, calibration: {A: {'1-2': 'PHONES'}}},
    'a non-string role': {output: null, calibration: {A: {'1-2': 1}}},
    'a bad calibration pair': {output: null, calibration: {A: {'1-2-3': 'phones'}}},
    'a calibration pair list': {output: null, calibration: {A: ['1-2']}},
    'a long calibration label': {output: null, calibration: {['x'.repeat(201)]: {'1-2': 'phones'}}},
    'a __proto__ label': JSON.parse('{"output":null,"calibration":{"__proto__":{"1-2":"phones"}}}'),
    'a constructor label': {output: null, calibration: {constructor: {'1-2': 'phones'}}},
    'a prototype label': {output: null, calibration: {prototype: {'1-2': 'phones'}}},
    'seventeen labels': {output: null, calibration: labels(17)},
    'thirty-three pairs': {output: null, calibration: {A: pairs(33)}},
  };
  for (const [name, value] of Object.entries(invalid)) {
    assert.throws(() => validatePreviewSetup(value), `the validator must refuse ${name}`);
    assert.throws(() => validateRequest('savePreviewSetup', value), `the request boundary must refuse ${name}`);
  }

  // PRESERVE: the bounds themselves are accepted, and the validator rebuilds the value.
  for (const value of [
    saved,
    {output: null, calibration: labels(16)},
    {output: null, calibration: {A: pairs(32)}},
    {output: {label: 'x'.repeat(200), pair: '99-99'}, calibration: {}},
  ]) assert.doesNotThrow(() => validatePreviewSetup(value), `${JSON.stringify(value).slice(0, 80)} must be accepted`);
  assert.deepEqual(validatePreviewSetup({output: null, calibration: {A: {'1-2': 'room'}}}), {output: null, calibration: {A: {'1-2': 'room'}}});
  assert.deepEqual(validatePreviewSetup(saved), saved);
  const rebuilt = validatePreviewSetup(saved);
  assert.notEqual(rebuilt, saved, 'the validator must answer its own value, never the caller object');
  assert.notEqual(rebuilt.calibration['Rane FOUR'], saved.calibration['Rane FOUR']);
});

test('the preview setup actions carry no path and getPreviewSetup carries no parameters', async () => {
  const directory = await scratchDir();
  try {
    const fs = store(directory);
    await fs.save(saved);
    const answer = await fs.load();
    assert.deepEqual(Object.keys(answer).sort(), ['calibration', 'output']);
    assert.doesNotMatch(JSON.stringify(answer), new RegExp(directory), 'the answer must never name the file it came from');
    assert.match(JSON.stringify(answer), /Rane FOUR/);

    assert.deepEqual(validateRequest('getPreviewSetup', undefined), {});
    assert.deepEqual(validateRequest('getPreviewSetup', {}), {});
    assert.deepEqual(validateRequest('savePreviewSetup', saved), saved);
    for (const rejected of [{output: null}, {calibration: {}}, {path: '/Users/someone/Music'}, {directory: '/private/tmp'}, {file: setupFile(directory)}])
      assert.throws(() => validateRequest('getPreviewSetup', rejected), `getPreviewSetup must refuse ${JSON.stringify(rejected)}`);
    assert.doesNotThrow(() => validateRequest('savePreviewSetup', saved), 'the valid setup must pass the request boundary');
    for (const rejected of [{...saved, path: setupFile(directory)}, {output: null}, {calibration: {}}])
      assert.throws(() => validateRequest('savePreviewSetup', rejected), `savePreviewSetup must accept exactly output and calibration: ${JSON.stringify(rejected).slice(0, 80)}`);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test('both preview setup actions answer while a core job owns the host', async () => {
  const main = await read('main.ts');
  const preload = await read('preload.ts');

  // The store is wired with the app's data folder and the host's own file system.
  assert.match(main, /const previewSetup=createPreviewSetupStore\(\{directory:app\.getPath\('userData'\),fs:\{readFile,stat,writeFile,rename,unlink\}\}\);/, 'main.ts must wire the store with app.getPath(userData)');
  assert.match(main, /case 'getPreviewSetup':return previewSetup\.load\(\);/, 'getPreviewSetup must answer the store value and nothing else');
  assert.match(main, /case 'savePreviewSetup':return previewSetup\.save\(params\);/, 'savePreviewSetup must store the validated value and nothing else');
  assert.match(preload, /getPreviewSetup:\(\)=>invoke\('getPreviewSetup'\)/, 'getPreviewSetup must be a parameterless bridge action');
  assert.match(preload, /savePreviewSetup:\(params:unknown\)=>invoke\('savePreviewSetup',params\)/, 'savePreviewSetup must be bridged with its params');

  // S14a: neither action reaches the core, so neither is part of the reviewed read whitelist;
  // main.ts answers them before the busy boundary, which otherwise keeps its exact shape.
  assert.equal(reads.isAllowedWhileBusy('getPreviewSetup'), false, 'the preview setup never reaches the core, so it must not join the read whitelist');
  assert.equal(reads.isAllowedWhileBusy('savePreviewSetup'), false);
  assert.match(main, /const PREVIEW_SETUP_ACTIONS:ReadonlySet<string>=new Set\(\['getPreviewSetup','savePreviewSetup'\]\);/, 'the two host-local actions must be named where the busy boundary is decided');
  assert.match(main, /if\(!PREVIEW_SETUP_ACTIONS\.has\(method\)\)assertDispatchable\(method,\{legacy:legacy\.busy,/, 'only these two actions may skip the busy boundary');

  // No case body may reach for a job slot or the core.
  for (const action of ['getPreviewSetup', 'savePreviewSetup']) {
    const start = main.indexOf(`case '${action}':`);
    const body = main.slice(start, main.indexOf('case ', start + 1));
    assert.doesNotMatch(body, /run\(|core\.request|randomUUID/, `${action} must never dispatch a core job`);
  }
});
