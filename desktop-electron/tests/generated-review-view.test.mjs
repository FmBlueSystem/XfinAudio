import assert from 'node:assert/strict';
import test from 'node:test';
import { createGeneratedReviewView } from '../.out/renderer/generated-review-view.js';

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; textContent = ''; value = ''; disabled = false; hidden = false; open = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  replaceChildren(...children) {
    if (this.children.some(child => all(child).includes(document.activeElement))) document.activeElement = null;
    for (const child of this.children) child.parentElement = null;
    this.children = []; this.append(...children);
  }
  focus() { document.activeElement = this; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = node => [node, ...node.children.flatMap(all)];
const text = node => [node.textContent, ...node.children.map(text)].join(' ');
const visible = node => !node.hidden && (!node.parentElement || (node.parentElement.tagName !== 'details' || node.parentElement.open || node.tagName === 'summary') && visible(node.parentElement));
const tracks = ['a', 'b', 'c'].map(id => ({ id, title: `Track ${id}`, artist: 'DJ' }));
function fixture() {
  const previous = globalThis.document;
  globalThis.document = { createElement: tag => new Element(tag), activeElement: null };
  const calls = []; const root = new Element(); let available = true;
  const controller = {
    editable: true, pending: false, error: '', comparison: null,
    snapshot: { reviewId: 'one', tracks, readiness: 'needs_review', warnings: ['Salto'], blockers: [] },
    details: { engineFacts: '<script>Local evidence</script>', readinessSummary: 'Revisión recomendada', protectedTrackIds: [], transitions: [], readinessChecks: [{ label: 'BPM', status: 'needs_review', detail: 'Revisa este salto' }] },
    load: () => calls.push(['load']), compare: id => calls.push(['compare', id]), remove: id => calls.push(['remove', id]), move: (id, direction) => calls.push(['move', id, direction]),
  };
  const render = createGeneratedReviewView(root, controller, { canAct: () => available }); render();
  const get = id => { const node = all(root).find(item => item.id === id); assert.ok(node, `Missing ${id}`); return node; };
  return { root, controller, calls, render, get, select: id => { get('review-selected-track').value = id; get('review-selected-track').dispatchEvent(new Event('change')); }, block: () => { available = false; render(); }, restore: () => { globalThis.document = previous; } };
}

test('one labeled track selector dispatches only explicit actions for the selected track', () => {
  const f = fixture(); try {
    const select = f.get('review-selected-track');
    assert.equal(all(f.root).filter(node => node.tagName === 'select').length, 1);
    assert.ok(all(f.root).some(node => node.tagName === 'label' && node.attrs.for === select.id && /Ajustar una pista/.test(node.textContent)));
    assert.equal(select.children.length, 3);
    assert.equal(all(f.root).filter(node => node.tagName === 'button' && /^review-(compare|remove|move)-/.test(node.id)).length, 4);
    select.focus(); f.select('b'); assert.equal(document.activeElement, select); assert.deepEqual(f.calls, []);
    for (const id of ['review-compare-1', 'review-remove-1', 'review-move-1--1', 'review-move-1-1']) f.get(id).dispatchEvent(new Event('click'));
    assert.deepEqual(f.calls, [['compare', 'b'], ['remove', 'b'], ['move', 'b', -1], ['move', 'b', 1]]);
  } finally { f.restore(); }
});
test('evidence is disclosed on demand while readiness and errors remain visible', () => {
  const f = fixture(); try {
    const evidence = f.get('review-evidence'); assert.equal(evidence.tagName, 'details'); assert.equal(evidence.open, false);
    assert.match(text(evidence.children[0]), /Por qué esta selección/); assert.equal(visible(f.get('review-engine-facts')), false);
    assert.equal(visible(f.get('review-readiness-summary')), true); assert.match(text(f.get('review-readiness-summary')), /Revisión recomendada/);
    assert.match(text(f.get('review-readiness-notices')), /Revisa este salto/); assert.equal(visible(f.get('review-readiness-notices')), true);
    evidence.open = true; f.controller.error = 'Esta pista está protegida'; f.render();
    assert.equal(f.get('review-evidence'), evidence); assert.equal(evidence.open, true); assert.equal(visible(f.get('review-error')), true);
    assert.match(text(f.get('review-engine-facts')), /<script>/); assert.ok(!all(f.root).some(node => node.tagName === 'script'));
    evidence.open = false; f.render(); assert.equal(evidence.open, false); assert.equal(visible(f.get('review-error')), true);
  } finally { f.restore(); }
});
test('selection and mounted controls survive reorder, pending updates and late completion without taking focus', () => {
  const f = fixture(); try {
    f.select('b'); const select = f.get('review-selected-track'); const compare = f.get('review-compare-1'); compare.focus();
    f.controller.pending = true; f.render(); assert.equal(f.get('review-compare-1'), compare);
    const outside = new Element('button'); outside.focus();
    f.controller.pending = false; f.controller.snapshot = { ...f.controller.snapshot, reviewId: 'two', tracks: [tracks[1], tracks[0], tracks[2]] }; f.render();
    assert.equal(f.get('review-selected-track'), select); assert.equal(select.value, 'b'); assert.equal(f.get('review-compare-0'), compare); assert.equal(document.activeElement, outside);
    f.controller.snapshot = { ...f.controller.snapshot, reviewId: 'three', tracks: [tracks[0], tracks[2]] }; f.render();
    assert.equal(select.value, 'a'); assert.equal(document.activeElement, outside); assert.deepEqual(f.calls, []);
  } finally { f.restore(); }
});
test('protected tracks and protected neighbors retain all action and boundary guards', () => {
  const f = fixture(); try {
    f.controller.details.protectedTrackIds = ['a']; f.render();
    for (const id of ['review-compare-0', 'review-remove-0', 'review-move-0--1', 'review-move-0-1']) { assert.equal(f.get(id).disabled, true); f.get(id).dispatchEvent(new Event('click')); }
    assert.deepEqual(f.calls, []); f.select('b'); assert.equal(f.get('review-move-1--1').disabled, true); assert.equal(f.get('review-move-1-1').disabled, false);
    f.select('c'); assert.equal(f.get('review-move-2-1').disabled, true);
    f.block(); assert.equal(f.get('review-selected-track').disabled, true); f.get('review-remove-2').dispatchEvent(new Event('click')); assert.deepEqual(f.calls, []);
  } finally { f.restore(); }
});
test('a comparison stays associated with its selected track, including a failed later request', () => {
  const f = fixture(); try {
    f.select('b'); f.get('review-compare-1').dispatchEvent(new Event('click'));
    const value = { ...f.controller.details, qualityScore: .8 };
    f.controller.comparison = { replacement: tracks[2], message: 'Solo comparación', original: value, proposed: value };
    f.render(); assert.equal(f.get('review-replacement-comparison').hidden, false);
    f.select('a'); assert.equal(f.get('review-replacement-comparison').hidden, true);
    f.get('review-compare-0').dispatchEvent(new Event('click')); f.controller.error = 'No se pudo comparar'; f.render();
    assert.equal(f.get('review-replacement-comparison').hidden, true);
    f.select('b'); assert.equal(f.get('review-replacement-comparison').hidden, false);
    assert.deepEqual(f.calls, [['compare', 'b'], ['compare', 'a']]);
  } finally { f.restore(); }
});
test('known readiness states use Spanish and raw engine summary stays inside evidence', () => {
  const f = fixture(); try {
    f.controller.details = { ...f.controller.details, readinessSummary: 'Raw engine summary', readinessChecks: [
      { label: 'Metadata', status: 'ready', detail: 'Complete' }, { label: 'BPM', status: 'needs_review', detail: 'Review jump' }, { label: 'Missing', status: 'blocked', detail: 'Unavailable' },
    ] }; f.render();
    assert.match(text(f.get('review-readiness-summary')), /Revisión recomendada.*1 avisos.*0 bloqueos/);
    assert.doesNotMatch(text(f.get('review-readiness-summary')), /Raw engine/);
    assert.match(text(f.get('review-evidence')), /Raw engine summary/);
    for (const label of ['Lista para revisar', 'Revisión recomendada', 'Necesita atención']) assert.ok(text(f.get('review-evidence')).includes(label), label);
    assert.doesNotMatch(text(f.get('review-evidence')), /· (ready|needs_review|blocked):/);
    f.controller.details = null; f.render(); assert.equal(f.get('review-readiness-summary').hidden, false);
  } finally { f.restore(); }
});
