import assert from 'node:assert/strict';
import test from 'node:test';
import { createDiscardGuard, createDiscardPrompt, DISCARD_CANCEL, DISCARD_CONFIRM, DISCARD_MESSAGE } from '../.out/renderer/discard-guard.js';

const plain = (reviewId) => ({ reviewId });

test('a review is edited only when its id differs from the one that was generated or chosen', () => {
  const guard = createDiscardGuard();
  assert.equal(guard.edited(null), false, 'no review in hand is never an edit');
  guard.reset('review-1');
  assert.equal(guard.edited(plain('review-1')), false, 'the generated review is the baseline');
  assert.equal(guard.edited(plain('review-2')), true, 'every edit mints a new reviewId');
  guard.reset('review-2');
  assert.equal(guard.edited(plain('review-2')), false, 'a chosen variant becomes the new baseline');
  assert.equal(guard.edited(plain('review-3')), true, 'editing the chosen variant is an edit again');
});

test('clearing the review drops the baseline so the next opened list is not an edit', () => {
  const guard = createDiscardGuard();
  guard.reset('review-1');
  guard.reset(null);
  assert.equal(guard.edited(plain('opened')), false);
  guard.reset('opened');
  assert.equal(guard.edited(plain('opened')), false);
  assert.equal(guard.edited(plain('opened-again')), true);
});

test('the question uses the exact Spanish copy from the spec', () => {
  assert.equal(DISCARD_MESSAGE, 'Vas a descartar los cambios de esta lista. ¿Continuar?');
  assert.equal(DISCARD_CONFIRM, 'Descartar cambios');
  assert.equal(DISCARD_CANCEL, 'Seguir editando');
});

class Node extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; id = ''; className = ''; type = ''; open = false; hidden = false; disabled = false;
  children = []; attrs = {};
  setAttribute(key, value) { this.attrs[key] = value; }
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
}

const walk = (node) => [node, ...node.children.flatMap(walk)];
const find = (root, id) => walk(root).find((node) => node.id === id);

async function promptFixture(canAct = () => true) {
  const previous = globalThis.document;
  globalThis.document = { createElement: (tag) => new Node(tag) };
  const container = new Node('main');
  const prompt = createDiscardPrompt(container, { canAct });
  return { container, prompt, restore: () => { globalThis.document = previous; } };
}

test('the prompt asks the exact question and«Seguir editando» answers no', async () => {
  const f = await promptFixture();
  try {
    const dialog = f.container.children[0];
    assert.equal(dialog.id, 'discard-guard');
    assert.equal(dialog.open, false, 'no question before an action needs one');
    const answer = f.prompt.ask();
    assert.equal(dialog.open, true);
    assert.equal(find(dialog, 'discard-guard-message').textContent, DISCARD_MESSAGE);
    assert.equal(find(dialog, 'discard-guard-confirm').textContent, DISCARD_CONFIRM);
    assert.equal(find(dialog, 'discard-guard-cancel').textContent, DISCARD_CANCEL);
    find(dialog, 'discard-guard-cancel').dispatchEvent(new Event('click'));
    assert.equal(await answer, false);
    assert.equal(dialog.open, false);
  } finally { f.restore(); }
});

test('«Descartar cambios» answers yes and a blocked host cannot confirm', async () => {
  let enabled = false;
  const f = await promptFixture(() => enabled);
  try {
    const dialog = f.container.children[0];
    const blocked = f.prompt.ask();
    find(dialog, 'discard-guard-confirm').dispatchEvent(new Event('click'));
    assert.equal(dialog.open, true, 'a blocked host leaves the question open');
    dialog.dispatchEvent(new Event('cancel', { cancelable: true }));
    assert.equal(await blocked, false, 'Escape still answers no while the host is blocked');
    assert.equal(dialog.open, false);
    const escaped = f.prompt.ask();
    find(dialog, 'discard-guard-cancel').dispatchEvent(new Event('click'));
    assert.equal(await escaped, false, '«Seguir editando» is never gated');
    enabled = true;
    const answer = f.prompt.ask();
    find(dialog, 'discard-guard-confirm').dispatchEvent(new Event('click'));
    assert.equal(await answer, true);
    assert.equal(dialog.open, false);
  } finally { f.restore(); }
});
