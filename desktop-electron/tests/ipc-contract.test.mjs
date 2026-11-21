import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';

const require = createRequire(import.meta.url);
const {validateRequest} = require('../.out/main/security.js');
const reads = require('../.out/main/ipc-reads.js');
const {savedPlaylistReview} = require('../.out/main/review-security.js');

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

// S6: opening a saved list hands the core's own review payload through untouched, and only an
// answer without a review identity keeps the read-only fallback the host used to fabricate.
test('opening a saved list keeps only the legacy fallback the host still owns', async () => {
  const main = await read('main.ts');
  const start = main.indexOf("case 'openPlaylist':");
  assert.notEqual(start, -1, 'openPlaylist must stay dispatched');
  const open = main.slice(start, main.indexOf("case 'cancelCurrent':", start));

  // PRESERVE: the one validated playlist identity still reaches playlist.open unchanged.
  assert.match(open, /run\('playlist\.open',\{playlistId:Number\(params\.playlistId\)\}\)/, 'openPlaylist must keep sending the one validated playlist identity');
  for (const fabricated of ['savedPlaylistId', 'needs_review', 'blockers', 'warnings'])
    assert.doesNotMatch(open, new RegExp(fabricated), `the host must not fabricate ${fabricated}: the core owns the review payload`);
  assert.match(open, /savedPlaylistReview\(/, 'openPlaylist must fill only the legacy fallback through savedPlaylistReview');

  // A core answer that carries a reviewId is the review: not one field is rewritten.
  const saved = {reviewId: '11111111-1111-4111-8111-111111111111', variant: 'saved', savedPlaylistId: '7', name: 'Set', canSave: true, canUndo: false, canRedo: false, tracks: [], editable: true};
  assert.equal(savedPlaylistReview(saved), saved, 'a saved list review must pass through untouched');

  // The read-only fallback has no review of its own and keeps exactly today's three additions.
  assert.deepEqual(
    savedPlaylistReview({id: 7, name: 'Set', tracks: [], missingTrackCount: 2, editable: false}),
    {id: 7, name: 'Set', tracks: [], missingTrackCount: 2, editable: false, savedPlaylistId: '7', reviewId: '', variant: 'saved', canSave: false, warnings: ['2 pistas no disponibles'], blockers: [], readiness: 'needs_review'},
    'the read-only fallback must gain the review fields the screen reads',
  );
  assert.deepEqual(savedPlaylistReview({id: 7, reviewId: ''}), {id: 7, savedPlaylistId: '7', reviewId: '', variant: 'saved', canSave: false, warnings: [], blockers: [], readiness: 'needs_review'}, 'an empty review identity is no review');
  // The screen reads warnings, blockers and readiness of every saved list; without them it throws.
  const readOnly = savedPlaylistReview({id: 9, name: 'Set', tracks: [], missingTrackCount: 2, editable: false});
  assert.deepEqual(readOnly.warnings, ['2 pistas no disponibles']); assert.deepEqual(readOnly.blockers, []); assert.equal(readOnly.readiness, 'needs_review'); assert.equal(readOnly.savedPlaylistId, '9');
});

// S6: saving a saved list's edits is a mutation like reviewReplace — one review uuid, no dialog,
// and the whole host is refused while any exclusive task holds it.
test('saving a saved list review reaches playlist.save_review as one exclusive mutation', async () => {
  const [main, preload] = await Promise.all([read('main.ts'), read('preload.ts')]);
  const reviewId = '11111111-1111-4111-8111-111111111111';

  assert.match(main, /case 'savePlaylistReview':return run\('playlist\.save_review',params\);/, 'savePlaylistReview must reach playlist.save_review and do nothing else, with no dialog');
  assert.match(preload, /savePlaylistReview:\(params:unknown\)=>invoke\('savePlaylistReview',params\)/, 'savePlaylistReview must be bridged with its params');

  assert.deepEqual(validateRequest('savePlaylistReview', {reviewId}), {reviewId});
  for (const rejected of [{}, {reviewId: '../private'}, {reviewId: 'AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'}, {reviewId: 42}, {reviewId: reviewId.slice(1)}, {reviewId, name: 'Set'}, {reviewId, playlistId: '12'}, {reviewId, trackIds: []}])
    assert.throws(() => validateRequest('savePlaylistReview', rejected), `savePlaylistReview must accept exactly one review uuid: ${JSON.stringify(rejected)}`);

  assert.equal(reads.isAllowedWhileBusy('savePlaylistReview'), false, 'saving a review is never a busy-time read');
  for (const source of EXCLUSIVE_SOURCES) {
    assert.throws(() => reads.assertDispatchable('savePlaylistReview', busyWith(source)), (error) => error.message === '[busy] Another task is still running', `savePlaylistReview must keep the exact busy refusal while ${source} runs`);
  }
});

// S4: following what Serato plays is a parameterless read-only action, so it answers
// while a job runs and carries no renderer data of its own.
test('live follow reaches live.follow as a parameterless read-only action', async () => {
  const [main, preload] = await Promise.all([read('main.ts'), read('preload.ts')]);

  assert.match(main, /case 'liveFollow':return core\.request\('live\.follow'\);/, 'liveFollow must reach live.follow with no renderer parameters');
  assert.match(preload, /liveFollow:\(\)=>invoke\('liveFollow'\)/, 'liveFollow must be bridged as a parameterless action');

  assert.deepEqual(validateRequest('liveFollow', undefined), {});
  assert.deepEqual(validateRequest('liveFollow', {}), {});
  for (const rejected of [{path: '/Volumes/dd/Library/master.sqlite'}, {sessionId: '11111111-1111-4111-8111-111111111111'}, {follow: true}, {deck: 1}])
    assert.throws(() => validateRequest('liveFollow', rejected), `liveFollow must accept no parameter: ${JSON.stringify(rejected)}`);

  assert.equal(reads.isAllowedWhileBusy('liveFollow'), true, 'following Serato is a busy-time read');
  for (const source of EXCLUSIVE_SOURCES)
    assert.doesNotThrow(() => reads.assertDispatchable('liveFollow', busyWith(source)), `liveFollow must answer while ${source} runs`);
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
