import assert from 'node:assert/strict';
import test from 'node:test';
// The renderer modules import each other by their built `.js` specifier, so this
// loads the compiled copy like the other controller tests do.
import { createLeftOutNotice, summarizePrepTracks } from '../.out/renderer/left-out-notice.js';

const track = (id, patch = {}) => ({ id, title: id, artist: 'Artist', bpm: 122, key: '8A', energy: 5, duration: 180, status: 'complete', missingFields: [], ...patch });

test('the notice counts the library tracks that do not enter the list and names the missing fields', () => {
  const gate = summarizePrepTracks([
    track('a'), track('b'), track('c'),
    track('d', { status: 'incomplete', missingFields: ['energy_level', 'bpm'], energy: null, bpm: null }),
    track('e', { status: 'incomplete', missingFields: ['camelot_key'], key: null }),
  ]);
  assert.deepEqual(gate, {
    total: 5, complete: 3, leftOut: 2, fields: ['bpm', 'camelot_key', 'energy_level'],
    message: '2 de 5 pistas no entran en la lista porque les falta BPM, key y energía.', canGenerate: true,
  });
});

test('the notice is hidden when every library track has complete metadata', () => {
  assert.deepEqual(summarizePrepTracks([track('a'), track('b'), track('c')]),
    { total: 3, complete: 3, leftOut: 0, fields: [], message: '', canGenerate: true });
});

test('fewer than two complete tracks asks for the minimum metadata and blocks generating', () => {
  const expected = { message: 'Necesitas al menos dos pistas con BPM, key y energía para generar una lista.', canGenerate: false };
  assert.equal(summarizePrepTracks([track('a'), track('b', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]).message, expected.message);
  assert.equal(summarizePrepTracks([track('a'), track('b', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]).canGenerate, expected.canGenerate);
  assert.equal(summarizePrepTracks([track('a', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]).message, expected.message);
  assert.equal(summarizePrepTracks([track('a', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]).canGenerate, expected.canGenerate);
});

test('an empty library shows no notice and blocks generating', () => {
  assert.deepEqual(summarizePrepTracks([]), { total: 0, complete: 0, leftOut: 0, fields: [], message: '', canGenerate: false });
});

test('a left-out track without a field list derives the fields from its values', () => {
  assert.deepEqual(summarizePrepTracks([track('a'), track('b'), track('c'), track('d', { status: 'incomplete', missingFields: undefined, bpm: null })]).fields, ['bpm']);
  assert.deepEqual(summarizePrepTracks([track('a'), track('b'), track('c'), track('d', { status: 'incomplete', missingFields: undefined, bpm: null, key: '', energy: null })]).fields, ['bpm', 'camelot_key', 'energy_level']);
});

test('a left-out track that cannot name a field still says why it stays out', () => {
  assert.equal(summarizePrepTracks([track('a'), track('b'), track('c'), track('d', { status: 'incomplete', missingFields: [] })]).message,
    '1 de 4 pistas no entran en la lista porque no tienen los metadatos completos.');
});

test('a library payload without a status counts completeness by the metadata it carries', () => {
  const gate = summarizePrepTracks([track('a', { status: undefined, missingFields: undefined }), track('b', { status: undefined, missingFields: undefined, bpm: null })]);
  assert.equal(gate.complete, 1);
  assert.equal(gate.leftOut, 1);
  assert.equal(gate.canGenerate, false);
});

class Element extends EventTarget {
  constructor() { super(); this.id = ''; this.className = ''; this.textContent = ''; this.hidden = false; this.disabled = false; this.type = ''; this.attrs = {}; this.children = []; }
  setAttribute(name, value) { this.attrs[name] = value; }
  replaceChildren(...children) { this.children = children; }
}

test('the notice renders the sentence with «Completar metadatos» above the generate button', () => {
  const oldDocument = globalThis.document;
  globalThis.document = { createElement: () => new Element() };
  let allowed = true; let opened = 0;
  try {
    const root = new Element();
    const render = createLeftOutNotice(root, { canAct: () => allowed, openMetadata: () => { opened += 1; } });
    render([track('a'), track('b'), track('c'), track('d', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]);
    const [message, button] = root.children;
    assert.equal(root.hidden, false);
    assert.equal(message.textContent, '1 de 4 pistas no entran en la lista porque les falta BPM.');
    assert.equal(button.textContent, 'Completar metadatos');
    assert.equal(button.hidden, false);
    button.dispatchEvent(new Event('click'));
    assert.equal(opened, 1);

    allowed = false; render([track('a'), track('b'), track('c'), track('d', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]);
    assert.equal(button.disabled, true);
    button.dispatchEvent(new Event('click'));
    assert.equal(opened, 1);

    allowed = true; render([track('a'), track('b')]);
    assert.equal(root.hidden, true);
    assert.equal(message.textContent, '');
  } finally { globalThis.document = oldDocument; }
});

test('the metadata button appears only when some track is actually left out', () => {
  const oldDocument = globalThis.document;
  globalThis.document = { createElement: () => new Element() };
  try {
    const root = new Element();
    const render = createLeftOutNotice(root, { canAct: () => true, openMetadata: () => {} });
    // One incomplete track cannot generate, so the minimum-metadata sentence wins; the way out is
    // still to complete metadata, so the button stays offered.
    render([track('a', { status: 'incomplete', missingFields: ['bpm'], bpm: null })]);
    assert.equal(root.hidden, false);
    assert.equal(root.children[0].textContent, 'Necesitas al menos dos pistas con BPM, key y energía para generar una lista.');
    assert.equal(root.children[1].hidden, false);
    render([track('a'), track('b')]);
    assert.equal(root.hidden, true);
    assert.equal(root.children[1].hidden, true);
  } finally { globalThis.document = oldDocument; }
});