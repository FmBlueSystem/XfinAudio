import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PreviewOutput, SYSTEM_OUTPUT, TONE_SECONDS, outputOptions, pairChannels, stereoPairs,
} from '../.out/renderer/preview-output.js';
import { createPreviewOutputView } from '../.out/renderer/preview-output-view.js';
import { createPlayer } from '../.out/renderer/player.js';

const STORAGE = 'xfin.preview-output';
const ABSENT_LINE = 'Rane FOUR no está conectado. La preescucha está deshabilitada.';
const tick = () => new Promise((resolve) => setImmediate(resolve));

class MediaNode {
  constructor(name) { this.name = name; this.connections = []; this.disconnects = 0; }
  connect(target, output, input) { this.connections.push({ target, output, input }); return target; }
  disconnect() { this.disconnects += 1; this.connections = []; }
}
class Destination extends MediaNode {
  constructor() { super('destination'); this.channelCount = 2; this.maxChannelCount = 14; this.channelCountMode = 'max'; this.channelInterpretation = 'speakers'; }
}
class Oscillator extends MediaNode {
  constructor() { super('oscillator'); this.frequency = { value: 0 }; this.started = []; this.stopped = []; this.onended = null; }
  start(when) { this.started.push(when); }
  stop(when) { this.stopped.push(when); }
}
class AudioContextFake {
  constructor(options) { this.options = options; this.destination = new Destination(); this.nodes = []; this.closes = 0; this.sinks = []; this.currentTime = 0; }
  record(node) { this.nodes.push(node); return node; }
  createMediaElementSource(element) { const node = new MediaNode('source'); node.element = element; return this.record(node); }
  createChannelSplitter(count) { const node = new MediaNode('splitter'); node.count = count; return this.record(node); }
  createChannelMerger(count) { const node = new MediaNode('merger'); node.count = count; return this.record(node); }
  createGain() { const node = new MediaNode('gain'); node.gain = { value: 0 }; return this.record(node); }
  createOscillator() { return this.record(new Oscillator()); }
  async close() { this.closes += 1; }
  async setSinkId(deviceId) { this.sinks.push(deviceId); this.destination.maxChannelCount = deviceId === 'rane' ? 14 : 2; }
}
const device = (deviceId, label, kind = 'audiooutput') => ({ deviceId, label, kind });
const DEFAULT_DEVICE = device('default', 'Predeterminado');
const RANE = device('rane', 'Rane FOUR');
const HEADPHONES = device('hp', 'Auriculares');

function harness(options = {}) {
  const contexts = []; const changes = []; const listeners = [];
  const saved = new Map(Object.entries(options.saved ?? {}));
  let devices = options.devices ?? [DEFAULT_DEVICE, HEADPHONES, RANE, device('mic', 'Micrófono', 'audioinput')];
  const storage = { getItem: (key) => saved.get(key) ?? null, setItem: (key, value) => { saved.set(key, value); } };
  const controller = new PreviewOutput({
    enumerateDevices: () => Promise.resolve(devices),
    createAudioContext: (createOptions) => { const context = new AudioContextFake(createOptions); contexts.push(context); return context; },
    storage,
    listenDeviceChange: (listener) => { listeners.push(listener); return () => { listeners.splice(listeners.indexOf(listener), 1); }; },
    changed: () => changes.push(controller.label),
  });
  return {
    controller, contexts, changes, listeners, saved, storage,
    setDevices: (next) => { devices = next; },
    restore: () => { controller.dispose(); },
  };
}
const remembered = (label, pair) => ({ [STORAGE]: JSON.stringify({ label, pair }) });
const mergedInputs = (splitter) => splitter.connections.map((entry) => [entry.output, entry.input]);

test('the outputs are listed with their labels and never the default entry', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    assert.deepEqual(h.controller.outputs.map((entry) => entry.label), ['Auriculares', 'Rane FOUR']);
    assert.deepEqual(h.controller.outputs.map((entry) => entry.deviceId), ['hp', 'rane']);
  } finally { h.restore(); }
  assert.deepEqual(outputOptions([RANE, device('default', 'Predeterminado'), device('mic', 'Micrófono', 'audioinput')]), [{ label: 'Rane FOUR', deviceId: 'rane' }]);
  assert.deepEqual(outputOptions([device('', 'Sin etiqueta')]), []);
  assert.deepEqual(outputOptions([RANE, { ...RANE }]), [{ label: 'Rane FOUR', deviceId: 'rane' }]);
});

test('the pairs come from the channel count of the chosen output', async () => {
  assert.deepEqual(stereoPairs(14), ['1-2', '3-4', '5-6', '7-8', '9-10', '11-12', '13-14']);
  assert.deepEqual(stereoPairs(6), ['1-2', '3-4', '5-6']);
  assert.deepEqual(stereoPairs(3), ['1-2']);
  assert.deepEqual(stereoPairs(1), []);
  assert.deepEqual(stereoPairs(0), []);
  assert.deepEqual(pairChannels('5-6'), [4, 5]);
  assert.deepEqual(pairChannels('1-2'), [0, 1]);
  assert.equal(pairChannels('3'), null);
  assert.equal(pairChannels('4-3'), null);
  const h = harness();
  try {
    await h.controller.refresh();
    assert.deepEqual(h.controller.pairs, []);
    h.controller.select('Rane FOUR');
    assert.equal(h.contexts[0].options.sinkId, 'rane');
    assert.equal(h.controller.pairs.length, 7);
    assert.equal(h.controller.pair, '1-2');
  } finally { h.restore(); }
});

test('the graph sends the left and right channels only to the chosen pair', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    h.controller.select('Rane FOUR');
    h.controller.selectPair('3-4');
    const element = { tagName: 'audio' };
    assert.equal(await h.controller.prepare(element), true);
    const [context] = h.contexts;
    assert.deepEqual(context.options, { sinkId: 'rane' });
    assert.equal(context.destination.channelCount, 14);
    assert.equal(context.destination.channelCountMode, 'explicit');
    assert.equal(context.destination.channelInterpretation, 'discrete');
    const [source, splitter, merger] = context.nodes;
    assert.equal(source.name, 'source');
    assert.equal(source.element, element);
    assert.deepEqual(source.connections.map((entry) => entry.target), [splitter]);
    assert.equal(splitter.count, 2);
    assert.equal(merger.count, 14);
    assert.deepEqual(mergedInputs(splitter), [[0, 2], [1, 3]]);
    assert.deepEqual(merger.connections.map((entry) => entry.target), [context.destination]);
    // The same route is reused, never a second source for the same element.
    assert.equal(await h.controller.prepare(element), true);
    assert.equal(h.contexts.length, 1);
    assert.equal(context.nodes.filter((node) => node.name === 'source').length, 1);
  } finally { h.restore(); }
});

test('«Salida del sistema» is the default and builds no graph', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    assert.equal(h.controller.label, null);
    assert.equal(h.controller.available, true);
    assert.equal(h.controller.message, '');
    assert.deepEqual(h.controller.pairs, []);
    assert.equal(await h.controller.prepare({ tagName: 'audio' }), true);
    assert.equal(h.contexts.length, 0);
  } finally { h.restore(); }
});

test('the tone plays on the chosen output and pair and stops after one second', async () => {
  assert.equal(TONE_SECONDS, 1);
  const h = harness();
  try {
    await h.controller.refresh();
    h.controller.select('Rane FOUR');
    h.controller.selectPair('5-6');
    const [context] = h.contexts;
    context.currentTime = 42;
    h.controller.tone();
    const oscillator = context.nodes.find((node) => node.name === 'oscillator');
    const gain = context.nodes.find((node) => node.name === 'gain');
    const merger = context.nodes.find((node) => node.name === 'merger');
    assert.equal(oscillator.frequency.value, 440);
    assert.ok(gain.gain.value > 0 && gain.gain.value <= 0.1);
    // The stop time is on the context's clock, which has been running since it was opened.
    assert.deepEqual(oscillator.started, [42]);
    assert.deepEqual(oscillator.stopped, [43]);
    // Without all the device's channels, discrete, the destination folds every pair into 1-2.
    assert.equal(context.destination.channelCount, 14);
    assert.equal(context.destination.channelCountMode, 'explicit');
    assert.equal(context.destination.channelInterpretation, 'discrete');
    assert.deepEqual(oscillator.connections.map((entry) => entry.target), [gain]);
    assert.equal(merger.count, 14);
    assert.deepEqual(gain.connections.map((entry) => [entry.target, entry.output, entry.input]), [[merger, 0, 4], [merger, 0, 5]]);
    assert.deepEqual(merger.connections.map((entry) => entry.target), [context.destination]);
  } finally { h.restore(); }
});

test('a remembered output that is absent disables the preview, plays nothing and says why', async () => {
  const h = harness({ saved: remembered('Rane FOUR', '3-4'), devices: [DEFAULT_DEVICE, HEADPHONES] });
  let fixture = null;
  try {
    await h.controller.refresh();
    assert.equal(h.controller.label, 'Rane FOUR');
    assert.equal(h.controller.available, false);
    assert.equal(h.controller.message, ABSENT_LINE);
    assert.equal(await h.controller.prepare({ tagName: 'audio' }), false);
    assert.equal(h.contexts.length, 0);
    // The player refuses every «Preescuchar»: no source, no playback, the reason on screen.
    fixture = playerFixture(h.controller);
    const { player, audio, elements } = fixture;
    assert.equal(audio.crossOrigin, 'anonymous');
    await player.select({ id: 'one', title: 'One', artist: 'Artist', duration: 300 });
    assert.equal(audio.src, '');
    assert.equal(audio.plays, 0);
    assert.equal(audio.paused, true);
    assert.equal(elements['player-status'].textContent, ABSENT_LINE);
  } finally { fixture?.restore(); h.restore(); }
});

test('the preview enables itself again when the output comes back', async () => {
  const h = harness({ saved: remembered('Rane FOUR', '1-2'), devices: [DEFAULT_DEVICE] });
  try {
    await h.controller.refresh();
    assert.equal(h.controller.available, false);
    h.setDevices([DEFAULT_DEVICE, RANE]);
    for (const listener of [...h.listeners]) listener();
    await tick();
    assert.equal(h.controller.available, true);
    assert.equal(h.controller.message, '');
    assert.equal(await h.controller.prepare({ tagName: 'audio' }), true);
    assert.equal(h.contexts.length, 1);
  } finally { h.restore(); }
});

test('the choice is restored from storage and remembered after every change', async () => {
  const h = harness({ saved: remembered('Rane FOUR', '3-4') });
  try {
    assert.equal(h.controller.label, 'Rane FOUR');
    assert.equal(h.controller.pair, '3-4');
    assert.deepEqual(JSON.parse(h.saved.get(STORAGE)), { label: 'Rane FOUR', pair: '3-4' });
    await h.controller.refresh();
    assert.equal(h.controller.label, 'Rane FOUR');
    assert.equal(h.controller.pair, '3-4');
    assert.equal(h.controller.pairs.length, 7);
    h.controller.selectPair('5-6');
    assert.deepEqual(JSON.parse(h.saved.get(STORAGE)), { label: 'Rane FOUR', pair: '5-6' });
    h.controller.select(null);
    assert.deepEqual(JSON.parse(h.saved.get(STORAGE)), { label: null, pair: '5-6' });
    assert.equal(h.controller.message, '');
    assert.equal(h.controller.label, null);
  } finally { h.restore(); }
});

test('an unreadable or foreign stored value falls back to the system output', () => {
  for (const value of ['not json', '{"label":3}', '[]', '{"label":"Rane FOUR","pair":"x"}']) {
    const h = harness({ saved: { [STORAGE]: value } });
    try {
      assert.equal(h.controller.label, null);
      assert.equal(h.controller.pair, '1-2');
    } finally { h.restore(); }
  }
});

test('with a chosen output the player prepares the route before it plays', async () => {
  const h = harness();
  const fixture = playerFixture(h.controller);
  try {
    await h.controller.refresh();
    h.controller.select('Rane FOUR');
    await fixture.player.select({ id: 'two', title: 'Two', artist: 'Artist', duration: 300 });
    const [context] = h.contexts;
    assert.equal(context.options.sinkId, 'rane');
    assert.equal(context.nodes[0].element, fixture.audio);
    assert.equal(fixture.audio.src, 'xfin-audio://track/two');
    assert.equal(fixture.audio.plays, 1);
  } finally { fixture.restore(); h.restore(); }
});

test('S11 (f): back to the system output moves the same context to the default device, in stereo', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    h.controller.select('Rane FOUR');
    const element = { tagName: 'audio' };
    assert.equal(await h.controller.prepare(element), true);
    const context = h.contexts.find((item) => item.nodes.some((node) => node.name === 'source'));
    const [source, splitter, merger] = context.nodes;
    h.controller.select(null);
    assert.equal(await h.controller.prepare(element), true);
    assert.deepEqual(context.sinks, ['']);
    assert.deepEqual(source.connections.map((entry) => entry.target), [context.destination]);
    assert.deepEqual(splitter.connections, []);
    assert.deepEqual(merger.connections, []);
    assert.equal(context.destination.channelCount, 2);
    assert.equal(context.destination.channelInterpretation, 'speakers');
    assert.equal(h.contexts.flatMap((item) => item.nodes).filter((node) => node.name === 'source').length, 1);
  } finally { h.restore(); }
});

test('S11 (f): another output reuses the same context and source of the element', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    const element = { tagName: 'audio' };
    assert.equal(await h.controller.prepare(element), true);
    assert.equal(h.contexts.length, 0, 'the system output builds nothing before any route exists');
    h.controller.select('Auriculares');
    assert.equal(await h.controller.prepare(element), true);
    const context = h.contexts.find((item) => item.nodes.some((node) => node.name === 'source'));
    assert.deepEqual(context.options, { sinkId: 'hp' });
    h.controller.select('Rane FOUR');
    h.controller.selectPair('5-6');
    assert.equal(await h.controller.prepare(element), true);
    assert.deepEqual(context.sinks, ['rane']);
    assert.equal(context.destination.channelCount, 14);
    const sources = h.contexts.flatMap((item) => item.nodes).filter((node) => node.name === 'source');
    assert.equal(sources.length, 1);
    const merger = context.nodes.filter((node) => node.name === 'merger').at(-1);
    assert.equal(merger.count, 14);
    const splitter = context.nodes.find((node) => node.name === 'splitter');
    assert.deepEqual(mergedInputs(splitter), [[0, 4], [1, 5]]);
  } finally { h.restore(); }
});

test('S11 (f): the output disappears during a preview: it is silenced and paused at once', async () => {
  const h = harness();
  try {
    await h.controller.refresh();
    h.controller.select('Rane FOUR');
    let pauses = 0;
    const element = { tagName: 'audio', pause: () => { pauses += 1; } };
    assert.equal(await h.controller.prepare(element), true);
    const context = h.contexts.find((item) => item.nodes.some((node) => node.name === 'source'));
    h.setDevices([DEFAULT_DEVICE, HEADPHONES]);
    for (const listener of [...h.listeners]) listener();
    await tick();
    assert.equal(h.controller.available, false);
    assert.equal(pauses, 1);
    assert.deepEqual(context.nodes[0].connections, []);
    assert.equal(await h.controller.prepare(element), false);
  } finally { h.restore(); }
});

// ---- the setting under «Seguir a Serato» ----

class Element extends EventTarget {
  constructor(tag = 'div') { super(); this.tagName = tag; }
  children = []; attrs = {}; dataset = {}; textContent = ''; value = ''; checked = false; disabled = false; hidden = false; id = ''; className = '';
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
}
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
const byId = (root, id) => all(root).find((item) => item.id === id);

function viewFixture(controller) {
  const previous = globalThis.document;
  globalThis.document = { createElement: (tag) => new Element(tag) };
  const view = createPreviewOutputView(controller);
  view.render();
  return { view, node: view.node, restore: () => { globalThis.document = previous; } };
}

test('the setting offers the system output first, the labelled outputs and the pairs', async () => {
  const h = harness();
  const f = viewFixture(h.controller);
  try {
    await h.controller.refresh();
    f.view.render();
    const rendered = text(f.node);
    for (const expected of ['Salida de preescucha', 'Salida', SYSTEM_OUTPUT, 'Auriculares', 'Rane FOUR', 'Probar',
      'La preescucha suena por el canal del mezclador que recibe esos canales: deja su fader abajo y activa su CUE para oírla solo en los auriculares.']) {
      assert.ok(rendered.includes(expected), expected);
    }
    const select = byId(f.node, 'preview-output-select');
    assert.deepEqual(select.children.map((option) => option.textContent), [SYSTEM_OUTPUT, 'Auriculares', 'Rane FOUR']);
    assert.deepEqual(select.children.map((option) => option.value), ['', 'Auriculares', 'Rane FOUR']);
    assert.equal(select.value, '');
    assert.equal(byId(f.node, 'preview-output-pair-field').hidden, true);
    select.value = 'Rane FOUR';
    select.dispatchEvent(new Event('change'));
    assert.equal(h.controller.label, 'Rane FOUR');
    f.view.render();
    assert.deepEqual(byId(f.node, 'preview-output-pair').children.map((option) => option.value).slice(0, 2), ['1-2', '3-4']);
    assert.equal(byId(f.node, 'preview-output-pair-field').hidden, false);
    byId(f.node, 'preview-output-pair').value = '3-4';
    byId(f.node, 'preview-output-pair').dispatchEvent(new Event('change'));
    assert.equal(h.controller.pair, '3-4');
    byId(f.node, 'preview-output-tone').dispatchEvent(new Event('click'));
    assert.equal(h.contexts.length, 1);
    assert.ok(h.contexts[0].nodes.some((node) => node.name === 'oscillator'));
  } finally { f.restore(); h.restore(); }
});

test('an absent output disables «Probar» and shows the exact line in the setting', async () => {
  const h = harness({ saved: remembered('Rane FOUR', '1-2'), devices: [DEFAULT_DEVICE] });
  const f = viewFixture(h.controller);
  try {
    await h.controller.refresh();
    f.view.render();
    const message = byId(f.node, 'preview-output-message');
    assert.equal(message.hidden, false);
    assert.equal(message.textContent, ABSENT_LINE);
    assert.equal(message.attrs.role, 'status');
    assert.equal(byId(f.node, 'preview-output-tone').disabled, true);
    h.setDevices([DEFAULT_DEVICE, RANE]);
    for (const listener of [...h.listeners]) listener();
    await tick();
    f.view.render();
    assert.equal(byId(f.node, 'preview-output-message').hidden, true);
    assert.equal(byId(f.node, 'preview-output-message').textContent, '');
    assert.equal(byId(f.node, 'preview-output-tone').disabled, false);
  } finally { f.restore(); h.restore(); }
});

// ---- the app player ----

class PlayerElement extends EventTarget {
  value = '0'; textContent = ''; disabled = false; max = '100'; attrs = {};
  setAttribute(name, value) { this.attrs[name] = String(value); }
  removeAttribute(name) { delete this.attrs[name]; }
}
class PlayerAudio extends EventTarget {
  paused = true; duration = 300; currentTime = 0; volume = 1; src = ''; crossOrigin = null; loads = 0; plays = 0;
  async play() { this.plays += 1; this.paused = false; this.dispatchEvent(new Event('play')); }
  pause() { this.paused = true; this.dispatchEvent(new Event('pause')); }
  load() { this.loads += 1; this.currentTime = 0; this.dispatchEvent(new Event('loadedmetadata')); }
  removeAttribute(name) { if (name === 'src') this.src = ''; }
}

function playerFixture(preview) {
  const elements = Object.fromEntries(['player-toggle', 'player-seek', 'player-current', 'player-duration', 'player-volume', 'player-status', 'player-title', 'player-artist']
    .map((id) => [id, new PlayerElement()]));
  elements['audio-player'] = new PlayerAudio();
  const previous = globalThis.document;
  globalThis.document = { getElementById: (id) => elements[id] };
  const player = createPlayer(() => {}, preview ?? null);
  return { player, elements, audio: elements['audio-player'], restore: () => { globalThis.document = previous; } };
}
