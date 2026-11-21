import assert from 'node:assert/strict';
import test from 'node:test';
import { LIVE_FOLLOW_INTERVAL_MS, LiveFollowController, followKey } from '../.out/renderer/live-follow.js';
import { createLiveFollowView } from '../.out/renderer/live-follow-view.js';

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; checked = false; disabled = false; hidden = false; id = ''; className = '';
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const tick = () => new Promise((resolve) => setImmediate(resolve));
const node = (root, id) => all(root).find((item) => item.id === id);
/** The suggestion rows, in order: every `tr` that carries the suggestion's id. */
const rows = (root) => all(root).filter((item) => item.tagName === 'tr' && item.dataset.liveFollowSuggestion !== undefined);
const cellText = (cell) => text(cell).trim();
/** The button of one «Sonando en Serato» line, by the deck it asks for. */
const deckButton = (root, deck) => all(root).find((item) => item.dataset.liveFollowDeck === deck);
const playingLines = (root) => node(root, 'live-follow-playing').children.map(text);

const track = (id, extra = {}) => ({ id, title: `Título ${id}`, artist: `Artista ${id}`, bpm: 124, key: '8A', energy: 5, duration: 200, ...extra });
const answer = (over = {}) => ({
  available: true, reason: null, sessionStartedAt: '2026-10-01T22:00:00Z',
  playing: [
    { deck: 1, startedAt: '2026-10-01T22:00:00Z', inLibrary: true, ...track('a') },
    { deck: 2, startedAt: '2026-10-01T22:03:00Z', inLibrary: false, title: 'Ajena', artist: 'Otro', bpm: 126, key: '9A' },
  ],
  current: track('a'),
  suggestions: [{ ...track('b'), score: 0.81 }],
  playedCount: 0, ...over,
});

/** The injected clock: every timer is recorded so a test ticks it instead of waiting. */
function harness(options = {}) {
  const calls = []; const changes = []; const timers = [];
  let blocked = false; let next = options.next ?? answer();
  const clock = { every: (intervalMs, callback) => { const entry = { intervalMs, callback, cancelled: false }; timers.push(entry); return () => { entry.cancelled = true; }; } };
  const api = options.api ?? { liveFollow: (input) => { calls.push(input); return options.respond ? options.respond() : Promise.resolve(next); } };
  const controller = new LiveFollowController(api, { canAct: () => !blocked, changed: () => changes.push(controller.key) }, clock);
  return {
    controller, calls, changes, timers,
    setAnswer: (value) => { next = value; },
    block: () => { blocked = true; }, allow: () => { blocked = false; },
  };
}

test('asks the core every three seconds, never two requests at once, and stops with the screen', async () => {
  assert.equal(LIVE_FOLLOW_INTERVAL_MS, 3000);
  const release = []; const h = harness({ respond: () => new Promise((resolve) => release.push(resolve)) });
  h.controller.start();
  assert.equal(h.timers.length, 1); assert.equal(h.timers[0].intervalMs, 3000); assert.equal(h.controller.polling, true);
  await tick();
  assert.deepEqual(h.calls, [{}]);
  h.timers[0].callback(); h.timers[0].callback(); await tick();
  assert.equal(h.calls.length, 1);
  release.shift()(answer()); await tick();
  h.timers[0].callback(); await tick();
  assert.equal(h.calls.length, 2);
  release.shift()(answer()); await tick();
  h.controller.stop();
  assert.equal(h.timers[0].cancelled, true); assert.equal(h.controller.polling, false);
  h.timers[0].callback(); await tick();
  assert.equal(h.calls.length, 2);
});

test('the switch is on by default, stops the polling when off and resumes when on', async () => {
  const h = harness();
  assert.equal(h.controller.following, true);
  h.controller.start(); await tick();
  assert.deepEqual(h.calls, [{}]);
  h.controller.setFollowing(false);
  assert.equal(h.controller.following, false); assert.equal(h.timers[0].cancelled, true);
  h.timers[0].callback(); await tick();
  assert.equal(h.calls.length, 1);
  h.controller.setFollowing(true);
  assert.equal(h.timers.length, 2); await tick();
  assert.equal(h.calls.length, 2);
  h.timers[1].callback(); await tick();
  assert.equal(h.calls.length, 3);
});

test('switching off drops an answer that is still in flight', async () => {
  let release; const h = harness({ respond: () => new Promise((resolve) => { release = resolve; }) });
  h.controller.start(); await tick();
  h.controller.setFollowing(false);
  release(answer()); await tick();
  assert.equal(h.controller.answer, null);
});

test('redraws only when the playing tracks change', async () => {
  const h = harness();
  h.controller.start(); await tick();
  assert.equal(h.changes.length, 1);
  h.timers[0].callback(); await tick();
  assert.equal(h.changes.length, 1);
  h.setAnswer(answer({ playing: [{ deck: 1, startedAt: '2026-10-01T22:05:00Z', inLibrary: true, ...track('c') }], current: track('c'), suggestions: [{ ...track('d'), score: 0.6 }] }));
  h.timers[0].callback(); await tick();
  assert.equal(h.changes.length, 2);
  assert.notEqual(followKey(answer(), null), followKey(answer({ playing: [] }), null));
});

test('a failed read shows the retry line, never the raw error, and keeps polling', async () => {
  const h = harness({ respond: () => Promise.reject(new Error('/private/serato is locked')) });
  h.controller.start(); await tick();
  assert.equal(h.controller.reason, 'serato_unreadable');
  assert.equal(h.controller.message, 'No se pudo leer el historial de Serato. Se reintenta solo.');
  assert.doesNotMatch(h.controller.message, /private|serato is/i);
  h.timers[0].callback(); await tick();
  assert.equal(h.calls.length, 2);
});

test('an absent bridge method and a busy app never fire a request', async () => {
  const absent = harness({ api: {} });
  absent.controller.start(); await tick();
  assert.equal(absent.calls.length, 0); assert.equal(absent.timers.length, 0); assert.equal(absent.controller.polling, false);
  const busy = harness();
  busy.block(); busy.controller.start();
  assert.equal(busy.timers.length, 1); await tick();
  assert.equal(busy.calls.length, 0);
  busy.allow(); busy.timers[0].callback(); await tick();
  assert.equal(busy.calls.length, 1);
});

function viewFixture(options = {}) {
  const previous = globalThis.document;
  globalThis.document = { createElement: (tag) => new Element(tag) };
  const root = new Element(); const calls = []; const timers = []; const played = [];
  const answers = options.answers ?? [answer()];
  let index = 0;
  const clock = { every: (intervalMs, callback) => { const entry = { intervalMs, callback, cancelled: false }; timers.push(entry); return () => { entry.cancelled = true; }; } };
  const controller = new LiveFollowController({ liveFollow: (input) => { calls.push(input); return Promise.resolve(answers[Math.min(index++, answers.length - 1)]); } }, { canAct: () => true, changed: () => view.render() }, clock);
  const view = createLiveFollowView(root, controller, { play: (track) => played.push(track), ...(options.api ? { api: options.api } : {}) });
  view.render();
  controller.start();
  return {
    root, calls, timers, played, controller, view,
    ready: async () => { await tick(); view.render(); },
    restore: () => { view.dispose(); globalThis.document = previous; },
  };
}

test('the section shows the switch, both Serato lists and the read-only line as text', async () => {
  const f = viewFixture(); try {
    await f.ready();
    const rendered = text(f.root);
    for (const expected of [
      'Seguir a Serato', 'Seguir lo que suena en Serato',
      'Sonando en Serato', 'Deck 1: Título a — Artista a · 124 BPM · 8A · Actual',
      'Deck 2: Ajena — Otro · 126 BPM · 9A',
      'Qué poner después', 'Título b', 'Artista b', '8A', 'Buena · 81 %', 'Preescuchar',
      'Solo lectura: XfinAudio no controla Serato ni modifica su historial.',
    ]) assert.ok(rendered.includes(expected), expected);
    const toggle = all(f.root).find((item) => item.id === 'live-follow-switch');
    assert.equal(toggle.checked, true);
    assert.ok(!all(f.root).some((item) => ['script', 'img', 'audio'].includes(item.tagName)));
  } finally { f.restore(); }
});

test('preescuchar plays the suggested track through the app player', async () => {
  const f = viewFixture(); try {
    await f.ready();
    const preview = all(f.root).find((item) => item.dataset.liveFollowPreview === 'b');
    assert.ok(preview);
    preview.dispatchEvent(new Event('click'));
    assert.deepEqual(f.played.map((item) => item.id), ['b']);
  } finally { f.restore(); }
});

test('every reason shows its exact line', async () => {
  const lines = [
    ['serato_not_found', 'No se encontró el historial de Serato DJ en este equipo.'],
    ['serato_busy', 'No se pudo leer el historial de Serato. Se reintenta solo.'],
    ['serato_unreadable', 'No se pudo leer el historial de Serato. Se reintenta solo.'],
    ['no_session', 'Carga una pista en Serato para ver sugerencias.'],
    ['nothing_playing', 'Carga una pista en Serato para ver sugerencias.'],
    ['not_in_library', 'La pista que suena no está en tu biblioteca: Ajena — Otro.'],
  ];
  for (const [reason, expected] of lines) {
    const f = viewFixture({ answers: [answer({ available: false, reason, current: null, suggestions: [] })] });
    try {
      await f.ready();
      assert.ok(text(f.root).includes(expected), `${reason}: ${expected}`);
      assert.equal(rows(f.root).length, 0);
    } finally { f.restore(); }
  }
});

test('«Actual» marks the newest playing track that is in the library', async () => {
  const both = viewFixture({ answers: [answer({
    playing: [
      { deck: 1, startedAt: '2026-10-01T22:06:00Z', inLibrary: true, ...track('e') },
      { deck: 2, startedAt: '2026-10-01T22:00:00Z', inLibrary: true, ...track('f') },
    ],
    current: track('e'),
  })] });
  try {
    await both.ready();
    const lines = node(both.root, 'live-follow-playing').children.map(text);
    assert.equal(lines.length, 2);
    assert.ok(lines[0].includes('· Actual'), lines[0]);
    assert.ok(!lines[1].includes('Actual'), lines[1]);
  } finally { both.restore(); }
  const second = viewFixture({ answers: [answer({
    playing: [
      { deck: 1, startedAt: '2026-10-01T22:06:00Z', inLibrary: false, title: 'Ajena', artist: 'Otro' },
      { deck: 2, startedAt: '2026-10-01T22:00:00Z', inLibrary: true, ...track('g') },
    ],
    current: track('g'),
  })] });
  try {
    await second.ready();
    const lines = node(second.root, 'live-follow-playing').children.map(text);
    assert.equal(lines.length, 2);
    assert.ok(!lines[0].includes('Actual'), lines[0]);
    assert.ok(lines[1].includes('· Actual'), lines[1]);
  } finally { second.restore(); }
});

test('the lists are redrawn only when the playing tracks change', async () => {
  const f = viewFixture({ answers: [answer(), answer(), answer({ playing: [{ deck: 1, startedAt: '2026-10-01T22:05:00Z', inLibrary: true, ...track('c') }], current: track('c'), suggestions: [{ ...track('d'), score: 0.42 }] })] });
  try {
    await f.ready();
    const first = rows(f.root)[0];
    f.view.render();
    assert.equal(rows(f.root)[0], first);
    f.timers[0].callback(); await tick();
    assert.equal(rows(f.root)[0], first);
    f.timers[0].callback(); await tick();
    assert.notEqual(rows(f.root)[0], first);
    assert.ok(text(f.root).includes('Débil · 42 %'));
  } finally { f.restore(); }
});

test('the switch in the section stops and resumes the polling', async () => {
  const f = viewFixture(); try {
    await f.ready();
    assert.equal(f.calls.length, 1);
    const toggle = all(f.root).find((item) => item.id === 'live-follow-switch');
    toggle.checked = false; toggle.dispatchEvent(new Event('change'));
    assert.equal(f.controller.following, false); assert.equal(f.timers[0].cancelled, true);
    f.timers[0].callback(); await tick();
    assert.equal(f.calls.length, 1);
    toggle.checked = true; toggle.dispatchEvent(new Event('change'));
    await tick();
    assert.equal(f.calls.length, 2);
    assert.equal(f.timers.length, 2);
  } finally { f.restore(); }
});

const twoSuggestions = () => answer({ suggestions: [{ ...track('b'), score: 0.81 }, { ...track('c'), score: 0.42 }] });

test('S8: «Qué poner después» is a table with the eight exact columns', async () => {
  const f = viewFixture({ answers: [twoSuggestions()] }); try {
    await f.ready();
    const headers = all(f.root).filter((item) => item.tagName === 'th').map((item) => item.textContent);
    assert.deepEqual(headers, ['#', 'Título', 'Artista', 'BPM', 'Tonalidad', 'Energía', 'Mezcla', 'Escuchar']);
    const table = node(f.root, 'live-follow-suggestions');
    assert.equal(table.tagName, 'table');
    assert.equal(table.children.filter((item) => item.tagName === 'tbody').length, 1);
  } finally { f.restore(); }
});

test('S8: one numbered row per suggestion, with the text and tone of «Mezcla»', async () => {
  const f = viewFixture({ answers: [twoSuggestions()] }); try {
    await f.ready();
    const found = rows(f.root);
    assert.equal(found.length, 2);
    assert.deepEqual(found.map((row) => row.children.map(cellText)), [
      ['1', 'Título b', 'Artista b', '124', '8A', '5', 'Buena · 81 %', 'Preescuchar'],
      ['2', 'Título c', 'Artista c', '124', '8A', '5', 'Débil · 42 %', 'Preescuchar'],
    ]);
    assert.equal(found[0].children[6].className, 'transition-quality good');
    assert.equal(found[1].children[6].className, 'transition-quality weak');
  } finally { f.restore(); }
});

test('S9: a row is draggable and its dragstart cancels the browser drag and asks for that track only', async () => {
  const dragged = [];
  const f = viewFixture({ answers: [twoSuggestions()], api: { dragTrack: (input) => { dragged.push(input); return Promise.resolve({ started: true }); } } });
  try {
    await f.ready();
    const found = rows(f.root);
    assert.deepEqual(found.map((row) => row.draggable), [true, true]);
    for (const [index, id] of [[1, 'c'], [0, 'b']]) {
      const event = new Event('dragstart', { cancelable: true });
      found[index].dispatchEvent(event);
      assert.equal(event.defaultPrevented, true);
      assert.deepEqual(dragged.at(-1), { trackId: id });
      assert.deepEqual(Object.keys(dragged.at(-1)), ['trackId']);
    }
    assert.deepEqual(dragged, [{ trackId: 'c' }, { trackId: 'b' }]);
  } finally { f.restore(); }
});

test('S9: without dragTrack in the bridge no row is draggable and no drag starts', async () => {
  const empty = viewFixture({ answers: [twoSuggestions()], api: {} }); try {
    await empty.ready();
    const found = rows(empty.root);
    assert.deepEqual(found.map((row) => row.draggable), [false, false]);
    const event = new Event('dragstart', { cancelable: true });
    found[0].dispatchEvent(event);
    assert.equal(event.defaultPrevented, false);
  } finally { empty.restore(); }
  const absent = viewFixture({ answers: [twoSuggestions()] }); try {
    await absent.ready();
    assert.deepEqual(rows(absent.root).map((row) => row.draggable), [false, false]);
  } finally { absent.restore(); }
});

test('S9: a line under the table explains the drag', async () => {
  const f = viewFixture(); try {
    await f.ready();
    assert.ok(text(f.root).includes('Arrastra una fila a un deck o a un crate de Serato.'));
  } finally { f.restore(); }
});

/** S10: two decks, both in the library, so a chosen deck really changes what is current. */
const twoDecks = (over = {}) => answer({
  currentDeck: '1',
  current: track('a'),
  playing: [
    { deck: 1, startedAt: '2026-10-01T22:00:00Z', inLibrary: true, ...track('a') },
    { deck: 2, startedAt: '2026-10-01T22:03:00Z', inLibrary: true, ...track('f') },
  ],
  ...over,
});

test('S10: clicking a deck line asks at once for that deck and every later poll keeps it', async () => {
  const f = viewFixture({ answers: [twoDecks()] }); try {
    await f.ready();
    assert.deepEqual(f.calls, [{}]);
    const second = deckButton(f.root, '2');
    assert.ok(second, 'each line of «Sonando en Serato» is a button');
    assert.equal(second.tagName, 'button');
    second.dispatchEvent(new Event('click'));
    await tick();
    assert.deepEqual(f.calls, [{}, { deck: '2' }]);
    f.timers[0].callback(); await tick();
    assert.deepEqual(f.calls.at(-1), { deck: '2' });
    assert.equal(f.calls.length, 3);
    assert.equal(f.timers.length, 1);
  } finally { f.restore(); }
});

test('S10: the chosen line is marked «Actual» and the heading names the current track', async () => {
  const f = viewFixture({ answers: [twoDecks(), twoDecks({ currentDeck: 2, current: track('f') })] }); try {
    await f.ready();
    assert.equal(node(f.root, 'live-follow-suggestions-heading').textContent, 'Qué poner después de Título a');
    const before = playingLines(f.root);
    assert.ok(before[0].includes('· Actual'), before[0]);
    assert.ok(!before[1].includes('Actual'), before[1]);
    deckButton(f.root, '2').dispatchEvent(new Event('click'));
    await tick();
    const after = playingLines(f.root);
    assert.ok(!after[0].includes('Actual'), after[0]);
    assert.ok(after[1].includes('· Actual'), after[1]);
    assert.equal(node(f.root, 'live-follow-suggestions-heading').textContent, 'Qué poner después de Título f');
  } finally { f.restore(); }
});

test('S10: «Automático» appears only while a deck is chosen and returns to the polls without deck', async () => {
  const f = viewFixture({ answers: [twoDecks()] }); try {
    await f.ready();
    assert.equal(node(f.root, 'live-follow-automatic').textContent, 'Automático');
    assert.equal(node(f.root, 'live-follow-automatic').hidden, true);
    deckButton(f.root, '2').dispatchEvent(new Event('click'));
    await tick();
    assert.equal(node(f.root, 'live-follow-automatic').hidden, false);
    node(f.root, 'live-follow-automatic').dispatchEvent(new Event('click'));
    await tick();
    assert.deepEqual(f.calls.at(-1), {});
    assert.equal(node(f.root, 'live-follow-automatic').hidden, true);
    f.timers[0].callback(); await tick();
    assert.deepEqual(f.calls.at(-1), {});
    assert.ok(playingLines(f.root)[0].includes('· Actual'), playingLines(f.root)[0]);
  } finally { f.restore(); }
});

test('S10: the lines are redrawn when the playing tracks or the chosen deck change', async () => {
  const f = viewFixture({ answers: [twoDecks()] }); try {
    await f.ready();
    const first = node(f.root, 'live-follow-playing').children[0];
    f.timers[0].callback(); await tick();
    assert.equal(node(f.root, 'live-follow-playing').children[0], first);
    deckButton(f.root, '2').dispatchEvent(new Event('click'));
    await tick();
    const redrawn = node(f.root, 'live-follow-playing').children[0];
    assert.notEqual(redrawn, first);
    f.timers[0].callback(); await tick();
    assert.equal(node(f.root, 'live-follow-playing').children[0], redrawn);
    assert.notEqual(followKey(twoDecks(), null, '2'), followKey(twoDecks(), null, null));
    assert.notEqual(followKey(null, null, '2'), followKey(null, null, null));
  } finally { f.restore(); }
});
