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
  async setSinkId(deviceId) { this.sinks.push(deviceId); this.destination.maxChannelCount = ['rane', 'wide'].includes(deviceId) ? 14 : 2; }
}
const device = (deviceId, label, kind = 'audiooutput') => ({ deviceId, label, kind });
const DEFAULT_DEVICE = device('default', 'Predeterminado');
const RANE = device('rane', 'Rane FOUR');
const HEADPHONES = device('hp', 'Auriculares');
/** S12: the label the real Rane FOUR reports, and a wide output that is not the mixer. */
const RANE_OUTPUT = 'Rane FOUR (1cc5:0024)';
const RANE_FOUR_DEVICE = device('rane', RANE_OUTPUT);
const WIDE = device('wide', 'Interfaz USB');

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
    // S12 (c): the Rane FOUR starts on «Canal 3», whose pair is 5-6.
    assert.equal(h.controller.pair, '5-6');
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
  const h = harness({ devices: [DEFAULT_DEVICE, HEADPHONES, RANE, WIDE] });
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
    assert.deepEqual(select.children.map((option) => option.textContent), [SYSTEM_OUTPUT, 'Auriculares', 'Rane FOUR', 'Interfaz USB']);
    assert.deepEqual(select.children.map((option) => option.value), ['', 'Auriculares', 'Rane FOUR', 'Interfaz USB']);
    assert.equal(select.value, '');
    assert.equal(byId(f.node, 'preview-output-pair-field').hidden, true);
    // S12 (a): an output that is not the mixer keeps the select of pairs.
    select.value = 'Interfaz USB';
    select.dispatchEvent(new Event('change'));
    assert.equal(h.controller.label, 'Interfaz USB');
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

// ---- S12: the mixer channel of the Rane FOUR ----

/** The four captions of the channel select, marks included. */
const channelCaptions = (root) => byId(root, 'preview-output-pair').children.map((option) => option.textContent);
const pickOutput = (f, label) => {
  const select = byId(f.node, 'preview-output-select');
  select.value = label;
  select.dispatchEvent(new Event('change'));
  f.view.render();
};
const pickPair = (f, value) => {
  const select = byId(f.node, 'preview-output-pair');
  select.value = value;
  select.dispatchEvent(new Event('change'));
  f.view.render();
};

async function raneSetting(saved = {}) {
  const h = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE], saved });
  const f = viewFixture(h.controller);
  await h.controller.refresh();
  f.view.render();
  return { h, f, restore: () => { f.restore(); h.restore(); } };
}

test('S12 (a): the Rane FOUR offers «Canal del mezclador» with its four channels in physical order', async () => {
  const { h, f, restore } = await raneSetting();
  try {
    // S11 (c) keeps the pairs select for every other output.
    const field = byId(f.node, 'preview-output-pair-field');
    assert.equal(field.hidden, true);
    assert.equal(byId(f.node, 'preview-output-pair').attrs['aria-label'], 'Canales de la salida de preescucha');
    pickOutput(f, RANE_OUTPUT);
    assert.equal(h.controller.label, RANE_OUTPUT);
    assert.equal(field.hidden, false);
    assert.equal(field.children[0].textContent, 'Canal del mezclador');
    assert.equal(byId(f.node, 'preview-output-pair').attrs['aria-label'], 'Canal del mezclador');
    // S12 (b): without a Serato answer the options carry no mark.
    assert.deepEqual(channelCaptions(f.node), ['Canal 3', 'Canal 1', 'Canal 2', 'Canal 4']);
    const pairs = byId(f.node, 'preview-output-pair').children.map((option) => option.value);
    assert.deepEqual(pairs, ['5-6', '1-2', '3-4', '7-8']);
    assert.ok(pairs.every((pair) => pairChannels(pair) && pairChannels(pair)[1] <= 7), 'no pair above 7-8');
    // S12 (c): the Rane FOUR preselects «Canal 3» when the user picks it.
    assert.equal(byId(f.node, 'preview-output-pair').value, '5-6');
    assert.equal(h.controller.channel, 3);
    assert.equal(h.controller.pair, '5-6');
  } finally { restore(); }
});

test('S12 (a): choosing «Canal 2» stores the pair 3-4', async () => {
  const { h, f, restore } = await raneSetting();
  try {
    pickOutput(f, RANE_OUTPUT);
    const canal2 = byId(f.node, 'preview-output-pair').children.find((option) => option.textContent === 'Canal 2');
    pickPair(f, canal2.value);
    assert.equal(h.controller.pair, '3-4');
    assert.equal(h.controller.channel, 2);
    // The stored value stays `{label, pair}`: the channel is only another way to choose it.
    assert.deepEqual(JSON.parse(h.saved.get(STORAGE)), { label: RANE_OUTPUT, pair: '3-4' });
    assert.equal(byId(f.node, 'preview-output-pair').value, '3-4');
  } finally { restore(); }
});

test('S12 (b): every channel is marked free or occupied from the playing decks', async () => {
  const { f, restore } = await raneSetting();
  try {
    pickOutput(f, RANE_OUTPUT);
    f.view.render([{ deck: 1, title: 'Uno' }, { deck: '2', title: 'Dos' }]);
    assert.deepEqual(channelCaptions(f.node), [
      'Canal 3 · libre',
      'Canal 1 · ocupado: Uno',
      'Canal 2 · ocupado: Dos',
      'Canal 4 · libre',
    ]);
    // A deck with no track loaded leaves its channel free.
    f.view.render([{ deck: 4, title: 'Cuatro' }]);
    assert.deepEqual(channelCaptions(f.node), [
      'Canal 3 · libre', 'Canal 1 · libre', 'Canal 2 · libre', 'Canal 4 · ocupado: Cuatro',
    ]);
    // With no Serato answer there is no mark at all.
    f.view.render(null);
    assert.deepEqual(channelCaptions(f.node), ['Canal 3', 'Canal 1', 'Canal 2', 'Canal 4']);
  } finally { restore(); }
});

test('S12 (c): a later answer never changes the chosen channel', async () => {
  const { h, f, restore } = await raneSetting();
  try {
    pickOutput(f, RANE_OUTPUT);
    pickPair(f, '7-8');
    assert.equal(h.controller.channel, 4);
    f.view.render([{ deck: 2, title: 'Dos' }]);
    assert.equal(h.controller.pair, '7-8');
    assert.equal(h.controller.channel, 4);
    assert.equal(byId(f.node, 'preview-output-pair').value, '7-8');
    assert.equal(channelCaptions(f.node)[2], 'Canal 2 · ocupado: Dos');
    f.view.render(null);
    assert.equal(h.controller.pair, '7-8');
    assert.equal(byId(f.node, 'preview-output-pair').value, '7-8');
  } finally { restore(); }
});

test('S12 (d): an occupied channel says so and the preview keeps working', async () => {
  const { h, f, restore } = await raneSetting();
  try {
    pickOutput(f, RANE_OUTPUT);
    pickPair(f, '3-4');
    f.view.render([{ deck: 1, title: 'Uno' }, { deck: 2, title: 'Dos' }]);
    const notice = byId(f.node, 'preview-output-channel-notice');
    assert.equal(notice.hidden, false);
    assert.equal(notice.textContent, 'El canal 2 tiene una pista cargada en Serato: al activar su CUE vas a oír las dos.');
    assert.equal(h.controller.available, true);
    assert.equal(byId(f.node, 'preview-output-tone').disabled, false);
    assert.equal(await h.controller.prepare({ tagName: 'audio' }), true);
    // The channel comes free: the notice goes away on the next answer.
    f.view.render([{ deck: 2, title: '' }]);
    assert.equal(notice.hidden, false);
    assert.equal(notice.textContent, 'El canal 2 tiene una pista cargada en Serato: al activar su CUE vas a oír las dos.');
    f.view.render([{ deck: 1, title: 'Uno' }]);
    assert.equal(notice.hidden, true);
    assert.equal(notice.textContent, '');
    f.view.render(null);
    assert.equal(notice.hidden, true);
  } finally { restore(); }
});

test('S12 (e): under the select the line names the chosen channel', async () => {
  const { f, restore } = await raneSetting();
  try {
    pickOutput(f, RANE_OUTPUT);
    pickPair(f, '7-8');
    assert.equal(byId(f.node, 'preview-output-hint').textContent,
      'Baja el fader del canal 4 y activa su CUE para oír la preescucha solo en los auriculares.');
    pickPair(f, '1-2');
    assert.equal(byId(f.node, 'preview-output-hint').textContent,
      'Baja el fader del canal 1 y activa su CUE para oír la preescucha solo en los auriculares.');
  } finally { restore(); }
});

test('S12 (a): another output still shows the pairs and the S11 line', async () => {
  const h = harness({ devices: [DEFAULT_DEVICE, WIDE] });
  const f = viewFixture(h.controller);
  try {
    await h.controller.refresh();
    f.view.render([{ deck: 1, title: 'Uno' }]);
    pickOutput(f, 'Interfaz USB');
    assert.equal(byId(f.node, 'preview-output-pair-field').children[0].textContent, 'Canales');
    assert.equal(byId(f.node, 'preview-output-pair').attrs['aria-label'], 'Canales de la salida de preescucha');
    assert.deepEqual(byId(f.node, 'preview-output-pair').children.map((option) => option.textContent),
      ['1-2', '3-4', '5-6', '7-8', '9-10', '11-12', '13-14']);
    assert.equal(h.controller.channel, null);
    assert.equal(byId(f.node, 'preview-output-pair').value, '1-2');
    assert.equal(byId(f.node, 'preview-output-hint').textContent,
      'La preescucha suena por el canal del mezclador que recibe esos canales: deja su fader abajo y activa su CUE para oírla solo en los auriculares.');
    assert.equal(byId(f.node, 'preview-output-channel-notice').hidden, true);
  } finally { f.restore(); h.restore(); }
});

// ---- S13: the calibration for any controller ----

const CALIBRATION_KEY = 'xfin.preview-calibration';
const NO_DESTINATION = 'La calibración no encontró ninguna salida para la preescucha. Vuelve a calibrar.';
const PHONES_LINE = 'La preescucha suena directo en los auriculares.';
const calibrated = (label, roles) => ({ [CALIBRATION_KEY]: JSON.stringify({ [label]: roles }) });
/** The list the view renders, as `[pair, text, kind]` triples. */
const destinations = (controller, playing = null) => controller.destinations(playing).map((entry) => [entry.pair, entry.text, entry.kind]);

async function calibratedSetting(saved) {
  const h = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE, WIDE], saved });
  const f = viewFixture(h.controller);
  await h.controller.refresh();
  f.view.render();
  return { h, f, restore: () => { f.restore(); h.restore(); } };
}

test('S13 (a): the stored calibration is read back and a malformed value counts as none', async () => {
  const roles = { '1-2': 'room', '3-4': 'phones', '5-6': 'channel:1' };
  const h = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE], saved: calibrated(RANE_OUTPUT, roles) });
  try {
    await h.controller.refresh();
    h.controller.select(RANE_OUTPUT);
    assert.deepEqual(h.controller.calibration, roles);
    // S13 (b): the saved phones pair is what the output starts on.
    assert.equal(h.controller.pair, '3-4');
  } finally { h.restore(); }
  for (const value of ['not json', '[]', 'null', `{"${RANE_OUTPUT}":3}`, `{"${RANE_OUTPUT}":{"1-2":"loud"}}`]) {
    const other = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE], saved: { [CALIBRATION_KEY]: value } });
    try {
      await other.controller.refresh();
      other.controller.select(RANE_OUTPUT);
      assert.equal(other.controller.calibration, null, value);
      assert.equal(other.saved.get(CALIBRATION_KEY), value, 'reading never rewrites the stored value');
    } finally { other.restore(); }
  }
});

test('S13 (a): a second phones or channel pair clears the earlier one to silent', async () => {
  const stored = { '1-2': 'phones', '3-4': 'channel:1', '5-6': 'phones', '7-8': 'channel:1', '9-10': 'room' };
  const h = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE], saved: calibrated(RANE_OUTPUT, stored) });
  try {
    await h.controller.refresh();
    h.controller.select(RANE_OUTPUT);
    assert.deepEqual(h.controller.calibration, {
      '1-2': 'silent', '3-4': 'silent', '5-6': 'phones', '7-8': 'channel:1', '9-10': 'room',
    });
    assert.deepEqual(destinations(h.controller), [
      ['5-6', 'Auriculares', 'phones'],
      ['7-8', 'Canal 1', 'channel'],
    ]);
  } finally { h.restore(); }
});

test('S13 (b): a calibrated output offers «Auriculares» first and its channels ascending, never room or silent', async () => {
  const roles = { '1-2': 'room', '3-4': 'channel:2', '5-6': 'silent', '7-8': 'phones', '9-10': 'channel:1', '11-12': 'room' };
  const { h, f, restore } = await calibratedSetting(calibrated(RANE_OUTPUT, roles));
  try {
    pickOutput(f, RANE_OUTPUT);
    assert.equal(h.controller.destinationLabel, 'Destino de la preescucha');
    assert.equal(byId(f.node, 'preview-output-pair-field').children[0].textContent, 'Destino de la preescucha');
    assert.deepEqual(destinations(h.controller), [
      ['7-8', 'Auriculares', 'phones'],
      ['9-10', 'Canal 1', 'channel'],
      ['3-4', 'Canal 2', 'channel'],
    ]);
    f.view.render([{ deck: 1, title: 'Uno' }, { deck: 2, title: 'Dos' }]);
    assert.deepEqual(channelCaptions(f.node), ['Auriculares', 'Canal 1 · ocupado: Uno', 'Canal 2 · ocupado: Dos']);
    assert.deepEqual(byId(f.node, 'preview-output-pair').children.map((option) => option.value), ['7-8', '9-10', '3-4']);
    assert.equal(byId(f.node, 'preview-output-pair').value, '7-8');
    assert.ok(!byId(f.node, 'preview-output-pair').children.some((option) => ['1-2', '5-6', '11-12'].includes(option.value)));
  } finally { restore(); }
});

test('S13 (b): a calibration wins over the built-in Rane FOUR table', async () => {
  const roles = { '1-2': 'phones', '3-4': 'channel:3', '9-10': 'channel:2', '5-6': 'room' };
  const { h, f, restore } = await calibratedSetting(calibrated(RANE_OUTPUT, roles));
  try {
    pickOutput(f, RANE_OUTPUT);
    // The built-in table maps 5-6 to «Canal 3» and never offers 9-10; the calibration decides.
    assert.deepEqual(destinations(h.controller), [
      ['1-2', 'Auriculares', 'phones'],
      ['9-10', 'Canal 2', 'channel'],
      ['3-4', 'Canal 3', 'channel'],
    ]);
    assert.deepEqual(h.controller.channels, [{ number: 2, pair: '9-10' }, { number: 3, pair: '3-4' }]);
    assert.equal(h.controller.pair, '1-2');
    assert.equal(h.controller.channel, null);
    h.controller.selectChannel(3);
    assert.equal(h.controller.pair, '3-4');
    assert.equal(h.controller.channel, 3);
  } finally { restore(); }
});

test('S13 (b): saving chooses the phones pair, else the lowest channel pair', async () => {
  const h = harness({ devices: [DEFAULT_DEVICE, WIDE] });
  try {
    await h.controller.refresh();
    h.controller.select('Interfaz USB');
    h.controller.saveCalibration({ '1-2': 'room', '3-4': 'phones', '5-6': 'channel:2' });
    assert.equal(h.controller.pair, '3-4');
    assert.deepEqual(JSON.parse(h.saved.get(CALIBRATION_KEY)), {
      'Interfaz USB': { '1-2': 'room', '3-4': 'phones', '5-6': 'channel:2' },
    });
    // The chosen pair is remembered like any other choice.
    assert.deepEqual(JSON.parse(h.saved.get(STORAGE)), { label: 'Interfaz USB', pair: '3-4' });
    // Without phones the lowest channel number wins, not the first pair.
    h.controller.saveCalibration({ '1-2': 'room', '3-4': 'channel:2', '5-6': 'channel:1' });
    assert.equal(h.controller.pair, '5-6');
    assert.deepEqual(destinations(h.controller), [
      ['5-6', 'Canal 1', 'channel'],
      ['3-4', 'Canal 2', 'channel'],
    ]);
  } finally { h.restore(); }
});

test('S13 (b): a calibration with no usable pair disables the preview with the exact line', async () => {
  const { h, f, restore } = await calibratedSetting({});
  try {
    pickOutput(f, 'Interfaz USB');
    h.controller.saveCalibration({ '1-2': 'room', '3-4': 'silent' });
    f.view.render();
    assert.equal(h.controller.available, false);
    assert.equal(h.controller.message, NO_DESTINATION);
    assert.deepEqual(destinations(h.controller), []);
    const opened = h.contexts.length;
    assert.equal(await h.controller.prepare({ tagName: 'audio' }), false);
    assert.equal(h.contexts.length, opened, 'nothing is opened when no pair is offered');
    assert.equal(byId(f.node, 'preview-output-tone').disabled, true);
    const message = byId(f.node, 'preview-output-message');
    assert.equal(message.hidden, false);
    assert.equal(message.textContent, NO_DESTINATION);
    assert.equal(byId(f.node, 'preview-output-pair-field').hidden, true);
  } finally { restore(); }
});

test('S13 (e): clearing the calibration returns to the pairs, and to S12 on the Rane FOUR', async () => {
  const h = harness({ devices: [DEFAULT_DEVICE, WIDE] });
  try {
    await h.controller.refresh();
    h.controller.select('Interfaz USB');
    h.controller.saveCalibration({ '1-2': 'room', '3-4': 'phones', '5-6': 'channel:1' });
    assert.equal(h.controller.pair, '3-4');
    h.controller.clearCalibration();
    assert.equal(h.controller.calibration, null);
    assert.equal(h.controller.destinationLabel, '');
    assert.deepEqual(destinations(h.controller).map((entry) => entry[0]),
      ['1-2', '3-4', '5-6', '7-8', '9-10', '11-12', '13-14']);
    assert.equal(h.controller.channel, null);
    assert.deepEqual(JSON.parse(h.saved.get(CALIBRATION_KEY)), {});
  } finally { h.restore(); }
  const r = harness({ devices: [DEFAULT_DEVICE, RANE_FOUR_DEVICE] });
  try {
    await r.controller.refresh();
    r.controller.select(RANE_OUTPUT);
    r.controller.saveCalibration({ '1-2': 'phones', '9-10': 'channel:1', '3-4': 'channel:4' });
    assert.equal(r.controller.pair, '1-2');
    r.controller.clearCalibration();
    assert.equal(r.controller.calibration, null);
    assert.deepEqual(destinations(r.controller), [
      ['5-6', 'Canal 3', 'channel'],
      ['1-2', 'Canal 1', 'channel'],
      ['3-4', 'Canal 2', 'channel'],
      ['7-8', 'Canal 4', 'channel'],
    ]);
    assert.equal(r.controller.channel, 1);
    // A pair the built-in table does not use goes back to its first channel.
    r.controller.saveCalibration({ '9-10': 'phones' });
    assert.equal(r.controller.pair, '9-10');
    r.controller.clearCalibration();
    assert.equal(r.controller.pair, '5-6');
    assert.equal(r.controller.channel, 3);
  } finally { r.restore(); }
});

test('S13 (c): a calibrated phones pair says the preview goes straight to the headphones', async () => {
  const roles = { '1-2': 'phones', '3-4': 'channel:2', '5-6': 'room' };
  const { h, f, restore } = await calibratedSetting(calibrated(RANE_OUTPUT, roles));
  try {
    pickOutput(f, RANE_OUTPUT);
    assert.equal(h.controller.pair, '1-2');
    f.view.render([{ deck: 2, title: 'Dos' }]);
    assert.equal(byId(f.node, 'preview-output-hint').textContent, PHONES_LINE);
    assert.equal(byId(f.node, 'preview-output-channel-notice').hidden, true);
    pickPair(f, '3-4');
    f.view.render([{ deck: 2, title: 'Dos' }]);
    assert.equal(h.controller.channel, 2);
    assert.equal(byId(f.node, 'preview-output-hint').textContent,
      'Baja el fader del canal 2 y activa su CUE para oír la preescucha solo en los auriculares.');
    assert.equal(byId(f.node, 'preview-output-channel-notice').textContent,
      'El canal 2 tiene una pista cargada en Serato: al activar su CUE vas a oír las dos.');
  } finally { restore(); }
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
