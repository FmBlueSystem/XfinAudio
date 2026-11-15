import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';

const require = createRequire(import.meta.url);
const {validateRequest} = require('../.out/main/security.js');
const reads = require('../.out/main/ipc-reads.js');

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

// S6: the chat conversation reaches its core methods and carries no renderer data of its own.
// S4: applying a proposed change is a mutation like reviewReplace — one uuid, no dialog,
// and the whole host is refused while any exclusive task holds it.
const EXCLUSIVE_SOURCES = ['legacy', 'offline', 'profiles', 'serato', 'optionalAi', 'loudness', 'library', 'dialog', 'job'];
const busyWith = (source) => Object.fromEntries(EXCLUSIVE_SOURCES.map((name) => [name, name === source]));
test('an applied proposed change reaches ai.chat.apply as one exclusive mutation', async () => {
  const [main, preload] = await Promise.all([read('main.ts'), read('preload.ts')]);
  const actionId = '11111111-1111-4111-8111-111111111111';

  // R4: the click itself is the consent, so the case body is exactly the mutation dispatch.
  assert.match(main, /case 'aiChatApply':return run\('ai\.chat\.apply',params\);/, 'aiChatApply must reach ai.chat.apply and do nothing else, with no dialog');
  assert.match(preload, /aiChatApply:\(params:unknown\)=>invoke\('aiChatApply',params\)/, 'aiChatApply must be bridged with its params');

  assert.deepEqual(validateRequest('aiChatApply', {actionId}), {actionId});
  for (const rejected of [{}, {actionId: '../private'}, {actionId: 'AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'}, {actionId: 42}, {actionId: actionId.slice(1)}]) assert.throws(() => validateRequest('aiChatApply', rejected), 'aiChatApply must accept exactly one uuid');
  for (const rejected of [{actionId, position: 1}, {actionId, type: 'move'}, {actionId, reviewId: actionId}, {actionId, confirmed: true}]) assert.throws(() => validateRequest('aiChatApply', rejected), 'aiChatApply must reject any second parameter');

  assert.equal(reads.isAllowedWhileBusy('aiChatApply'), false, 'applying a change is never a busy-time read');
  for (const source of EXCLUSIVE_SOURCES) {
    assert.throws(() => reads.assertDispatchable('aiChatApply', busyWith(source)), (error) => error.message === '[busy] Another task is still running', `aiChatApply must keep the exact busy refusal while ${source} runs`);
  }
});

// S2: extending a list is a review mutation like reviewReplace — one uuid plus a bounded count.
test('extending the review reaches review.extend as one exclusive mutation', async () => {
  const [main, preload] = await Promise.all([read('main.ts'), read('preload.ts')]);
  const reviewId = '11111111-1111-4111-8111-111111111111';

  assert.match(main, /case 'reviewExtend':return run\('review\.extend',params\);/, 'reviewExtend must reach review.extend and do nothing else, with no dialog');
  assert.match(preload, /reviewExtend:\(params:unknown\)=>invoke\('reviewExtend',params\)/, 'reviewExtend must be bridged with its params');

  assert.deepEqual(validateRequest('reviewExtend', {reviewId, targetTrackCount: 20}), {reviewId, targetTrackCount: 20});
  for (const targetTrackCount of [2, 100]) assert.doesNotThrow(() => validateRequest('reviewExtend', {reviewId, targetTrackCount}), `reviewExtend must accept ${targetTrackCount}`);
  for (const rejected of [
    {reviewId}, {targetTrackCount: 20}, {reviewId, targetTrackCount: 1}, {reviewId, targetTrackCount: 101},
    {reviewId, targetTrackCount: 2.5}, {reviewId, targetTrackCount: '20'}, {reviewId, targetTrackCount: true},
    {reviewId: '../private', targetTrackCount: 20}, {reviewId: reviewId.slice(1), targetTrackCount: 20},
    {reviewId, targetTrackCount: 20, trackId: 'a'.repeat(64)}, {reviewId, targetTrackCount: 20, path: '/x'},
  ]) assert.throws(() => validateRequest('reviewExtend', rejected), Error, `${JSON.stringify(rejected)} must be rejected`);

  assert.equal(reads.isAllowedWhileBusy('reviewExtend'), false, 'extending a list is never a busy-time read');
  for (const source of EXCLUSIVE_SOURCES) {
    assert.throws(() => reads.assertDispatchable('reviewExtend', busyWith(source)), (error) => error.message === '[busy] Another task is still running', `reviewExtend must keep the exact busy refusal while ${source} runs`);
  }
});

test('the chat conversation actions reach their exact core methods with no renderer parameters', async () => {
  const [main, preload] = await Promise.all([read('main.ts'), read('preload.ts')]);
  const routes = [['aiChatHistory', 'ai.chat.history'], ['aiChatReset', 'ai.chat.reset']];
  for (const [action, coreMethod] of routes) {
    const escaped = coreMethod.replace(/\./g, '\\.');
    assert.match(main, new RegExp(`case '${action}':return run\\('${escaped}'(?:,\\s*\\{\\})?\\);`), `${action} must reach ${coreMethod} with no renderer parameters`);
    assert.match(preload, new RegExp(`${action}:\\(\\)=>invoke\\('${action}'\\)`), `${action} must be bridged as a parameterless action`);
  }
});
