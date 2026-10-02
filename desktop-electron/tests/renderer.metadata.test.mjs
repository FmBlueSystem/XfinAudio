import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { renderMetadataPanel } from '../renderer/metadata.ts';

class Element extends EventTarget {
  constructor(tagName = 'div') { super(); this.tagName = tagName; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; disabled = false; hidden = false;
  setAttribute(name, value) { this.attrs[name] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Metadata must never be parsed as HTML'); }
}
const descendants = (node) => [node, ...node.children.flatMap(descendants)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const track = (index, patch = {}) => ({ id: index.toString(16).padStart(64, '0'), title: `Pista ${index}`, artist: 'Artista', releaseYear: null, missingFields: ['bpm'], explanation: `Explicación existente ${index}\nNo se infieren valores.`, locked: false, priority: index + 1, ...patch });
const report = (tracks = [track(0), track(1, { missingFields: ['camelot_key'], locked: true, priority: 1 }), track(2, { missingFields: ['energy_level'], priority: 2 })]) => ({ totalTracks: tracks.length + 2, completeCount: 2, incompleteCount: tracks.length, gaps: { bpm: 1, camelot_key: 1, energy_level: 1 }, yearCoverage: { withReleaseYear: 1, withoutReleaseYear: tracks.length + 1 }, tracks, repairPlan: 'Plan existente · solo lectura\n1. Comprobar fuentes verificadas', readOnly: true });
function fixture(data = report(), preview, onExport) {
  const oldDocument = globalThis.document;
  globalThis.document = { createElement: (tag) => new Element(tag) };
  const root = new Element();
  renderMetadataPanel(root, data, preview, onExport);
  return {
    root, nodes: () => descendants(root),
    get: (suffix) => descendants(root).find((node) => node.id === `metadata-worklist-${suffix}`),
    rows: () => descendants(root).filter((node) => node.dataset.metadataTrackId),
    change: (suffix, value, type = 'change') => { const node = descendants(root).find((item) => item.id === `metadata-worklist-${suffix}`); node.value = value; node.dispatchEvent(new Event(type)); },
    restore: () => { globalThis.document = oldDocument; },
  };
}
function click(node) { assert.ok(node); node.dispatchEvent(new Event('click')); }

test('reports domain counts, informational year coverage and labeled controls in Spanish', () => {
  const f = fixture();
  try {
    for (const expected of ['Total de pistas', 'Completas', 'Pendientes', 'Con año', 'Sin año: 4', 'BPM: 1', 'Tonalidad: 1', 'Energía: 1', 'solo lectura']) assert.ok(text(f.root).includes(expected), expected);
    assert.equal(f.get('total').textContent, '5');
    assert.equal(f.get('complete').textContent, '2');
    assert.equal(f.get('incomplete').textContent, '3');
    assert.equal(f.get('field').tagName, 'select');
    assert.deepEqual(f.get('field').children.map((option) => option.value), ['all', 'bpm', 'camelot_key', 'energy_level']);
    for (const suffix of ['field', 'search']) assert.ok(f.nodes().some((node) => node.tagName === 'label' && node.attrs.for === f.get(suffix).id));
    assert.ok(f.nodes().filter((node) => node.tagName === 'th').every((node) => node.scope === 'col'));
    assert.equal(f.get('count').attrs['aria-live'], 'polite');
    const ids = f.nodes().map((node) => node.id).filter(Boolean);
    assert.equal(new Set(ids).size, ids.length);
    assert.ok(ids.every((id) => id.startsWith('metadata-worklist-')));
  } finally { f.restore(); }
});

test('priorities and locks are supplied values, rows are sorted without mutating the report', () => {
  const data = report([track(0, { priority: 3 }), track(1, { locked: true, priority: 1 }), track(2, { priority: 2, releaseYear: 1999 })]);
  const before = JSON.stringify(data); const f = fixture(data);
  try {
    assert.deepEqual(f.rows().map((row) => row.dataset.metadataTrackId), [data.tracks[1].id, data.tracks[2].id, data.tracks[0].id]);
    assert.ok(text(f.root).includes('Bloqueada')); assert.ok(text(f.root).includes('Sin bloqueo')); assert.ok(text(f.root).includes('1999'));
    assert.equal(JSON.stringify(data), before);
  } finally { f.restore(); }
});

test('native row buttons select existing explanations; preview only passes the opaque identity', () => {
  const calls = []; const data = report(); const f = fixture(data, (id) => calls.push(id));
  try {
    const row = f.rows()[1]; const select = descendants(row).find((node) => node.attrs['aria-controls'] === 'metadata-worklist-explanation');
    assert.equal(select.tagName, 'button'); assert.equal(select.type, 'button');
    click(select);
    assert.equal(select.attrs['aria-pressed'], 'true');
    assert.equal(f.get('explanation').textContent, data.tracks.find((item) => item.id === row.dataset.metadataTrackId).explanation);
    assert.equal(f.get('plan').textContent, data.repairPlan);
    const preview = descendants(row).find((node) => node.attrs['aria-label']?.startsWith('Escuchar:'));
    click(preview); assert.deepEqual(calls, [row.dataset.metadataTrackId]);
    const next = descendants(f.rows()[0]).find((node) => node.attrs['aria-controls']); click(next);
    assert.equal(select.attrs['aria-pressed'], 'false'); assert.equal(next.attrs['aria-pressed'], 'true');
  } finally { f.restore(); }
  const noPreview = fixture();
  try { assert.ok(!noPreview.nodes().some((node) => node.attrs['aria-label']?.startsWith('Escuchar:'))); } finally { noPreview.restore(); }
});

test('filters use domain field names and compose with Unicode title/artist search', () => {
  const f = fixture(report([track(0, { title: 'Canción <img src=x onerror=alert(1)>', artist: 'Björk', missingFields: ['bpm', 'energy_level'] }), track(1, { missingFields: ['camelot_key'] })]));
  try {
    f.change('field', 'energy_level'); assert.equal(f.rows().length, 1);
    f.change('search', 'BJÖRK', 'input'); assert.equal(f.rows().length, 1);
    assert.ok(text(f.root).includes('Canción <img src=x onerror=alert(1)>'));
    assert.ok(!f.nodes().some((node) => ['img', 'script'].includes(node.tagName)));
    f.change('field', 'camelot_key'); assert.equal(f.rows().length, 0);
    assert.ok(text(f.root).includes('Ninguna pista coincide con los filtros'));
    f.change('search', '', 'input'); assert.equal(f.rows().length, 1);
    f.change('field', 'all'); assert.equal(f.rows().length, 2);
  } finally { f.restore(); }
});

test('large reports page at 100 rows and search/filter cover tracks beyond the page', () => {
  const tracks = Array.from({ length: 205 }, (_, index) => track(index, { missingFields: index === 204 ? ['energy_level'] : ['bpm'] }));
  const f = fixture(report(tracks));
  try {
    assert.equal(f.rows().length, 100); assert.equal(f.get('previous').disabled, true);
    click(f.get('next')); assert.equal(f.rows()[0].dataset.metadataTrackId, tracks[100].id);
    click(f.get('next')); assert.equal(f.rows().length, 5); assert.equal(f.get('next').disabled, true);
    assert.equal(f.get('count').textContent, '201–205 de 205 pistas');
    f.change('field', 'energy_level'); assert.equal(f.rows().length, 1); assert.equal(f.rows()[0].dataset.metadataTrackId, tracks[204].id);
    assert.equal(f.get('previous').disabled, true); assert.equal(f.get('next').disabled, true);
    f.change('field', 'all'); f.change('search', 'Pista 204', 'input'); assert.equal(f.rows().length, 1);
    f.change('search', '', 'input'); assert.equal(f.rows().length, 100);
    assert.ok(f.nodes().length < 1700);
  } finally { f.restore(); }
});

test('changing the visible worklist clears stale selection and replacement removes prior content', () => {
  const f = fixture();
  try {
    click(descendants(f.rows()[0]).find((node) => node.attrs['aria-controls']));
    f.change('field', 'energy_level');
    assert.equal(f.get('explanation').textContent, 'Selecciona una pista para consultar su explicación.');
    const fresh = report([track(9)]); renderMetadataPanel(f.root, fresh);
    assert.equal(f.rows().length, 1); assert.equal(f.get('field').value, 'all');
    assert.equal(f.get('plan').textContent, fresh.repairPlan);
  } finally { f.restore(); }
});

test('empty library and complete library have distinct honest states without invented repairs', () => {
  for (const [totalTracks, expected] of [[0, 'No hay pistas en la biblioteca'], [2, 'No hay datos obligatorios pendientes']]) {
    const data = { ...report([]), totalTracks, completeCount: totalTracks, yearCoverage: { withReleaseYear: 0, withoutReleaseYear: totalTracks } };
    const f = fixture(data);
    try {
      assert.ok(text(f.root).includes(expected)); assert.equal(f.rows().length, 0);
      assert.equal(f.get('count').textContent, '0 pistas');
      assert.equal(f.get('previous').disabled, true); assert.equal(f.get('next').disabled, true);
      assert.equal(f.get('plan').textContent, data.repairPlan);
    } finally { f.restore(); }
  }
});

test('metadata rendering does not fetch, write tags, parse HTML or install its own busy state', async () => {
  const source = await readFile(new URL('../renderer/metadata.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /innerHTML|insertAdjacentHTML|\bfetch\s*\(|window\.xfin|setBusy\s*\(|createElement\(['"](?:script|iframe)['"]\)/);
});


test('metadata Serato callback receives exact filtered worklist across pages with no paths',()=>{
  const rows=Array.from({length:205},(_,i)=>track(i)), calls=[];
  const f=fixture(report(rows),undefined,source=>calls.push(source));
  try { click(f.get('export-serato')); assert.deepEqual(calls[0],{kind:'metadata',status:'incomplete',missingField:null,trackIds:rows.map(t=>t.id)});
    f.change('field','bpm');f.change('search','Pista 20','input'); click(f.get('export-serato'));
    assert.deepEqual(calls[1].trackIds,[20,200,201,202,203,204].map(i=>track(i).id));assert.equal(calls[1].missingField,'bpm');
    f.change('search','nothing','input');assert.equal(f.get('export-serato').disabled,true);click(f.get('export-serato'));assert.equal(calls.length,2);
  }finally{f.restore();}
});
test('metadata worklist export refuses more than500 without silently truncating',()=>{
 const calls=[], f=fixture(report(Array.from({length:501},(_,i)=>track(i))),undefined,source=>calls.push(source));
 try{assert.equal(f.get('export-serato').disabled,true);assert.match(text(f.root),/500/);click(f.get('export-serato'));assert.equal(calls.length,0);}finally{f.restore();}
});
