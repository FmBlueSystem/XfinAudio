import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import * as model from '../.out/renderer/model.js';
import {
  GENRE_BUSY, GENRE_LOAD_FAILED, GENRE_UNAVAILABLE_META, REST_HEADING, clearedGenreMessage,
  compatibleHeading, filterGenres, genreFocusCountLabel, genreGroupHeading, genreOptionLabel,
  genreResultMessage, selectedGenreMessage, unavailableGenreLabel, validateGenreCatalog,
} from '../.out/renderer/genre-picker.js';
import { createGenrePickerView } from '../.out/renderer/genre-picker-view.js';

const seedId = 'a'.repeat(64);
const group = (kind, genres) => ({ kind, genres });
const full = {
  groups: [
    group('compatible', [{ name: 'House', count: 3 }, { name: 'Deep House', count: 124 }, { name: 'Ambient', count: 1 }]),
    group('library', [{ name: 'Drum & Bass', count: 2 }, { name: 'Techno', count: 4 }]),
  ],
  totalGenres: 5, seedTitle: 'Brújula', genreAvailable: true,
};
const plain = {
  groups: [group('library', [{ name: 'Deep House', count: 124 }, { name: 'Techno', count: 4 }])],
  totalGenres: 2, seedTitle: null, genreAvailable: true,
};

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  textContent = ''; value = ''; id = ''; className = ''; disabled = false; hidden = false; children = []; attrs = {};
  setAttribute(name, value) { this.attrs[name] = value; }
  removeAttribute(name) { delete this.attrs[name]; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  focus() { document.activeElement = this; }
}
const flatten = (node) => [node, ...node.children.flatMap(flatten)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ').replace(/\s+/g, ' ').trim();
const tick = () => new Promise((resolve) => setImmediate(resolve));
const settle = async () => { for (let index = 0; index < 5; index++) await tick(); };
const keydown = (node, key) => { const event = new Event('keydown', { cancelable: true }); event.key = key; node.dispatchEvent(event); return event; };

function fixture({ catalog = async () => full, canAct = () => true, seed = '', genre = '' } = {}) {
  const previousDocument = globalThis.document;
  const elements = new Map();
  const get = (id) => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  globalThis.document = { getElementById: get, createElement: (tag) => new Element(tag), activeElement: null };
  get('prep-start').value = seed; get('prep-genre').value = genre;
  const calls = [];
  const view = createGenrePickerView({ canAct: () => canAct(), catalog: async (input) => { calls.push(input); return catalog(input); } });
  const list = get('prep-genre-results');
  const search = get('prep-genre-search');
  const hidden = get('prep-genre');
  const queued = [];
  hidden.addEventListener('input', () => queued.push('input'));
  hidden.addEventListener('change', () => queued.push('change'));
  return {
    view, calls, queued, list, search, hidden,
    get,
    options: () => list.children.filter((node) => node.attrs.role === 'option'),
    optionLabels: () => list.children.filter((node) => node.attrs.role === 'option').map(text),
    headings: () => list.children.filter((node) => node.attrs.role === 'presentation').map(text),
    status: () => get('prep-genre-status').textContent,
    label: () => get('prep-genre-selected-label').textContent,
    meta: () => get('prep-genre-selected-meta').textContent,
    state: () => get('prep-genre-selection').attrs['data-state'],
    open: async () => { search.dispatchEvent(new Event('focus')); await settle(); },
    type: async (value) => { search.value = value; search.dispatchEvent(new Event('input')); await settle(); },
    restore: () => { globalThis.document = previousDocument; },
  };
}

test('genre copy keeps the requested Spanish labels verbatim', () => {
  assert.equal(compatibleHeading('Brújula'), 'Compatibles con «Brújula»');
  assert.equal(REST_HEADING, 'Resto de la biblioteca');
  assert.equal(genreGroupHeading(group('compatible', []), 'Brújula'), 'Compatibles con «Brújula»');
  assert.equal(genreGroupHeading(group('library', []), 'Brújula'), 'Resto de la biblioteca');
  assert.equal(genreOptionLabel({ name: 'Deep House', count: 124 }), 'Deep House (124)');
  assert.equal(genreFocusCountLabel(1), '1 pista');
  assert.equal(genreFocusCountLabel(124), '124 pistas');
  assert.equal(selectedGenreMessage('Deep House'), 'Género preferido: Deep House.');
  assert.equal(clearedGenreMessage(), 'Sin género preferido.');
  assert.equal(unavailableGenreLabel('Garage'), 'No disponible: «Garage»');
  assert.equal(genreResultMessage('', 2), '2 géneros. Usa las flechas para moverte y Enter para elegir.');
  assert.equal(genreResultMessage('house', 1), '1 género. Usa las flechas para moverte y Enter para elegir.');
  assert.equal(genreResultMessage('zzz', 0), 'Sin géneros que coincidan con «zzz».');
});

test('filtering keeps the catalog order and accent-insensitive genre matching', () => {
  const groups = [group('compatible', [{ name: 'Deep House', count: 3 }, { name: 'Techno', count: 1 }]), group('library', [{ name: 'Ambient', count: 2 }])];
  assert.deepEqual(filterGenres(groups, ''), groups);
  assert.deepEqual(filterGenres(groups, '  '), groups);
  assert.deepEqual(filterGenres(groups, 'deep'), [group('compatible', [{ name: 'Deep House', count: 3 }])]);
  assert.deepEqual(filterGenres(groups, 'TÉC'), [group('compatible', [{ name: 'Techno', count: 1 }])]);
  assert.deepEqual(filterGenres(groups, 'zzz'), []);
  assert.deepEqual(groups[0].genres.length, 2, 'filtering never mutates the catalog');
});

test('a malformed catalog fails closed instead of rendering invented genres', () => {
  for (const value of [null, 3, [], { groups: 'x' }, { groups: [{ kind: 'invented', genres: [] }] }, { groups: [{ kind: 'library', genres: [{ name: '', count: 1 }] }] }, { groups: [{ kind: 'library', genres: [{ name: 'House', count: -1 }] }] }, { ...plain, totalGenres: 1.5 }, { ...plain, seedTitle: 3 }, { ...plain, genreAvailable: 'yes' }]) {
    assert.throws(() => validateGenreCatalog(value), (error) => error.code === 'genres_unavailable');
  }
  assert.deepEqual(validateGenreCatalog(full), full);
  assert.deepEqual(validateGenreCatalog(plain), plain);
});

test('the picker opens without typing and lists every library genre with its track count', async () => {
  const f = fixture({ catalog: async () => plain });
  try {
    assert.equal(f.list.hidden, true, 'the list stays closed until the field is used');
    await f.open();
    assert.equal(f.list.hidden, false);
    assert.equal(f.search.attrs['aria-expanded'], 'true');
    assert.deepEqual(f.optionLabels(), ['Deep House (124)', 'Techno (4)']);
    assert.deepEqual(f.headings(), [], 'without a seed there is one list and no group heading');
    assert.equal(f.status(), '2 géneros. Usa las flechas para moverte y Enter para elegir.');
    assert.deepEqual(f.calls, [{}], 'no seed and no stored genre send no selector');
  } finally { f.restore(); }
});

test('a seed shows compatible genres first under the seed title, then the rest', async () => {
  const f = fixture({ catalog: async () => full, seed: seedId });
  try {
    await f.open();
    assert.deepEqual(f.headings(), ['Compatibles con «Brújula»', 'Resto de la biblioteca']);
    assert.deepEqual(f.optionLabels(), ['House (3)', 'Deep House (124)', 'Ambient (1)', 'Drum & Bass (2)', 'Techno (4)']);
    assert.deepEqual(f.options().map((node) => node.attrs.role), ['option', 'option', 'option', 'option', 'option']);
    assert.deepEqual(f.calls, [{ startTrackId: seedId }], 'the core owns the ranking and receives the seed');
  } finally { f.restore(); }
});

test('typing filters the visible groups and reports when nothing matches', async () => {
  const f = fixture({ catalog: async () => full, seed: seedId });
  try {
    await f.open();
    assert.equal(f.options()[0].attrs['aria-selected'], 'true', 'the first genre starts highlighted');
    await f.type('deep');
    assert.deepEqual(f.optionLabels(), ['Deep House (124)']);
    assert.deepEqual(f.headings(), ['Compatibles con «Brújula»'], 'the empty group disappears while filtering');
    assert.equal(f.search.attrs['aria-activedescendant'], 'prep-genre-option-0');
    await f.type('zzz');
    assert.deepEqual(f.optionLabels(), []);
    assert.equal(f.list.hidden, true);
    assert.equal(f.status(), 'Sin géneros que coincidan con «zzz».');
  } finally { f.restore(); }
});

test('arrows wrap around the options and Enter selects the highlighted genre', async () => {
  const f = fixture({ catalog: async () => full, seed: seedId });
  try {
    await f.open();
    assert.equal(f.search.attrs['aria-activedescendant'], 'prep-genre-option-0');
    keydown(f.search, 'ArrowDown');
    assert.equal(f.search.attrs['aria-activedescendant'], 'prep-genre-option-1');
    keydown(f.search, 'ArrowUp'); keydown(f.search, 'ArrowUp');
    assert.equal(f.search.attrs['aria-activedescendant'], 'prep-genre-option-4', 'arrows wrap to the last genre');
    keydown(f.search, 'Enter');
    assert.equal(f.hidden.value, 'Techno');
    assert.equal(f.search.value, '');
    assert.equal(f.list.hidden, true);
    assert.equal(f.search.attrs['aria-expanded'], 'false');
    assert.equal(f.label(), 'Techno');
    assert.equal(f.meta(), '4 pistas');
    assert.equal(f.state(), 'chosen');
    assert.equal(f.status(), 'Género preferido: Techno.');
    assert.deepEqual(f.queued, ['input', 'change'], 'the Prep form hears the change so its draft state stays honest');
  } finally { f.restore(); }
});

test('a click selects a genre and Escape closes the list without touching the choice', async () => {
  const f = fixture({ catalog: async () => full, seed: seedId });
  try {
    await f.open();
    assert.equal(keydown(f.search, 'Escape').defaultPrevented, true);
    assert.equal(f.list.hidden, true);
    assert.equal(f.hidden.value, '');
    await f.open();
    f.options()[1].dispatchEvent(new Event('click'));
    assert.equal(f.hidden.value, 'Deep House');
    assert.equal(f.label(), 'Deep House');
    assert.equal(f.meta(), '124 pistas');
    assert.equal(f.list.hidden, true);
  } finally { f.restore(); }
});

test('Quitar clears the choice, announces it and returns focus to the field', async () => {
  const f = fixture({ catalog: async () => full, seed: seedId, genre: 'Techno' });
  try {
    f.view.sync(); await settle();
    assert.equal(f.label(), 'Techno');
    assert.equal(f.get('prep-genre-clear').hidden, false);
    f.get('prep-genre-clear').dispatchEvent(new Event('click'));
    assert.equal(f.hidden.value, '');
    assert.equal(f.label(), 'Sin género preferido');
    assert.equal(f.meta(), '');
    assert.equal(f.state(), 'empty');
    assert.equal(f.get('prep-genre-clear').hidden, true);
    assert.equal(f.status(), 'Sin género preferido.');
    assert.deepEqual(f.queued, ['input', 'change']);
    assert.equal(globalThis.document.activeElement, f.search);
  } finally { f.restore(); }
});

test('the chosen genre stays chosen when the seed changes and the list is recomputed', async () => {
  let catalog = { ...full, genreAvailable: true };
  const f = fixture({ catalog: async () => catalog, genre: 'Deep House' });
  try {
    f.view.sync(); await settle();
    assert.equal(f.label(), 'Deep House');
    assert.deepEqual(f.calls, [{ genre: 'Deep House' }]);
    catalog = {
      groups: [group('compatible', [{ name: 'Techno', count: 4 }])],
      totalGenres: 1, seedTitle: 'Semilla', genreAvailable: true,
    };
    f.get('prep-start').value = 'b'.repeat(64);
    f.view.sync(); await settle();
    assert.equal(f.hidden.value, 'Deep House', 'a new seed never rewrites the chosen genre');
    assert.equal(f.label(), 'Deep House');
    assert.deepEqual(f.calls.at(-1), { startTrackId: 'b'.repeat(64), genre: 'Deep House' });
    await f.open();
    assert.deepEqual(f.headings(), ['Compatibles con «Semilla»']);
    assert.deepEqual(f.optionLabels(), ['Techno (4)']);
  } finally { f.restore(); }
});

test('a restored genre that no longer exists in the library is shown as unavailable', async () => {
  const f = fixture({ catalog: async () => ({ ...plain, genreAvailable: false }), genre: 'Garage' });
  try {
    f.view.sync(); await settle();
    assert.equal(f.state(), 'unavailable');
    assert.equal(f.label(), 'No disponible: «Garage»');
    assert.equal(f.meta(), GENRE_UNAVAILABLE_META);
    assert.equal(f.hidden.value, 'Garage', 'the stored value is preserved, never silently rewritten');
    assert.equal(f.get('prep-genre-clear').hidden, false);
  } finally { f.restore(); }
});

test('a lost or malformed catalog fails closed without inventing genres', async () => {
  const failing = fixture({ catalog: async () => { throw Object.assign(new Error('/private/core'), { code: 'core_unavailable' }); } });
  try {
    await failing.open();
    assert.deepEqual(failing.optionLabels(), []);
    assert.equal(failing.list.hidden, true);
    assert.equal(failing.status(), GENRE_LOAD_FAILED);
    assert.doesNotMatch(failing.status(), /private/);
  } finally { failing.restore(); }
  const malformed = fixture({ catalog: async () => ({ groups: [group('compatible', [{ name: '', count: 1 }])] }) });
  try {
    await malformed.open();
    assert.deepEqual(malformed.optionLabels(), []);
    assert.equal(malformed.list.hidden, true);
  } finally { malformed.restore(); }
});

test('the picker stays inert while another operation owns the host', async () => {
  let editable = false;
  const f = fixture({ canAct: () => editable, catalog: async () => full });
  try {
    await f.open();
    assert.deepEqual(f.calls, [], 'a busy host is never queried');
    assert.equal(f.list.hidden, true);
    assert.equal(f.status(), GENRE_BUSY);
    editable = true;
    await f.open();
    assert.deepEqual(f.optionLabels(), ['House (3)', 'Deep House (124)', 'Ambient (1)', 'Drum & Bass (2)', 'Techno (4)']);
  } finally { f.restore(); }
});

test('the visible genre field sits next to the opening track and outside the advanced options', () => {
  const html = readFileSync(new URL('../renderer/index.html', import.meta.url), 'utf8');
  const at = (id) => html.indexOf(`id="${id}"`);
  for (const id of ['prep-genre-picker', 'prep-genre-search', 'prep-genre-results', 'prep-genre-status', 'prep-genre-selection', 'prep-genre-clear', 'prep-genre']) assert.ok(at(id) > 0, id);
  assert.ok(at('prep-genre-picker') > at('prep-start'), 'the genre picker follows the opening track');
  assert.ok(at('prep-genre-picker') < at('prep-advanced'), 'the genre picker left "Afinar selección"');
  assert.ok(at('prep-genre-picker') < at('generate-prep'), 'the genre field is visible before generating');
  assert.ok(at('prep-genre') > at('generate-prep'), 'the hidden genre value keeps its contracted position');
  assert.match(html, /<label for="prep-genre-search">Género preferido/);
  assert.match(html, /id="prep-genre-search"[^>]*role="combobox"/);
  assert.match(html, /id="prep-genre-search"[^>]*aria-expanded="false"/);
  assert.match(html, /id="prep-genre-search"[^>]*aria-controls="prep-genre-results"/);
  assert.match(html, /id="prep-genre-results"[^>]*role="listbox"/);
  assert.match(html, /id="prep-genre-status"[^>]*aria-live="polite"/);
  assert.match(html, /id="prep-genre-clear"[^>]*>Quitar</);
  assert.match(html, /id="prep-genre" type="hidden"/);
  assert.doesNotMatch(html, /id="prep-genre" maxlength/, 'the free-text genre input is gone');
});

test('the chosen genre still travels as genreFocus with the same validation', () => {
  const tracks = ['a', 'b'].map((letter) => ({ id: letter.repeat(64), title: letter, artist: 'Artist', bpm: 120, key: '8A', energy: 5, duration: 180 }));
  const fields = { count: '2', name: '', strategy: '', minutes: '', role: '', genre: '', start: '', end: '', required: [], excluded: [] };
  assert.deepEqual(model.buildPrepInput({ ...fields, genre: '  Deep House  ' }, tracks, []), { targetTrackCount: 2, name: 'Sesión equilibrada', genreFocus: 'Deep House' });
  assert.equal('genreFocus' in model.buildPrepInput(fields, tracks, []), false, 'no choice sends no genre focus');
  assert.throws(() => model.buildPrepInput({ ...fields, genre: 'x'.repeat(101) }, tracks, []), /100 caracteres/);
});
