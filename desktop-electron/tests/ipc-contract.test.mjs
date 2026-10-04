import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';

const require = createRequire(import.meta.url);
const {validateRequest} = require('../.out/main/security.js');

const read = (file) => readFile(new URL(`../src/${file}`, import.meta.url), 'utf8');

// Extract the keys of an object/record literal that maps keys to array values.
const keysBetween = (text, start, end) => {
  const searchFrom = text.indexOf(start);
  const slice = text.slice(searchFrom, text.indexOf(end, searchFrom));
  return [...slice.matchAll(/([A-Za-z]\w*):\s*\[/g)].map((match) => match[1]);
};

test('the Electron IPC action boundary is fail-closed and three-way exhaustive', async () => {
  const [security, main, preload, offline, review] = await Promise.all([
    read('security.ts'),
    read('main.ts'),
    read('preload.ts'),
    read('offline-security.ts'),
    read('review-security.ts'),
  ]);

  // A: validateRequest's effective allowlist, expanding the two spread tables a naive key scan misses.
  const allowlisted = new Set([
    ...keysBetween(security, 'const fields', 'if (!Object.hasOwn(fields,method))'),
    ...keysBetween(offline, 'OFFLINE_FIELDS', '};'),
    ...keysBetween(review, 'REVIEW_CONTROL_FIELDS', '};'),
  ]);

  // S: dispatch cases inside action()'s switch, and P: actions exposed on window.xfin by preload.
  const dispatch = main.slice(main.indexOf('switch(method) {'), main.indexOf('async function start()'));
  const dispatched = new Set([...dispatch.matchAll(/case '(\w+)':/g)].map((match) => match[1]));
  const bridged = new Map(
    [...preload.slice(preload.indexOf('Object.freeze({')).matchAll(/([A-Za-z]\w*):\([^)]*\)=>invoke\('(\w+)'/g)].map((match) => [match[1], match[2]]),
  );

  // R1: an allowlisted action with no dispatch case must reject, not resolve undefined.
  assert.match(dispatch, /default:\s*throw new Error\('Unsupported action'\)/, 'R1: action() must end in a throwing default arm');

  // R2: the allowlist, the dispatch switch and the preload bridge must be the same action set.
  assert.deepEqual([...dispatched].sort(), [...allowlisted].sort(), 'R2: dispatch cases must equal the validateRequest allowlist');
  assert.deepEqual([...bridged.keys()].sort(), [...dispatched].sort(), 'R2: preload keys must equal the dispatched action set');

  // R3: each bridge key dispatches its own action, never an alias.
  for (const [key, method] of bridged) {
    assert.equal(key, method, `R3: ${key} must invoke ${key}`);
  }

  // R5: every dispatched action is recognized by the allowlist (the runtime half of R2).
  for (const method of dispatched) {
    assert.doesNotThrow(() => {
      try {
        validateRequest(method, {__probe: true});
      } catch (error) {
        if (error.message === 'Unsupported action') throw error;
      }
    }, `R5: ${method} must be recognized by validateRequest`);
  }
});
