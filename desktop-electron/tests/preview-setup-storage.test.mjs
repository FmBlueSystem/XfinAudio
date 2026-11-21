import assert from 'node:assert/strict';
import test from 'node:test';
import { PreviewOutput } from '../.out/renderer/preview-output.js';
import { createPreviewSetupStorage } from '../.out/renderer/preview-setup-storage.js';

/** S14 (b): the host keeps the preview setup; the renderer never touches `localStorage`. */

const OUTPUT_KEY = 'xfin.preview-output';
const CALIBRATION_KEY = 'xfin.preview-calibration';
const RANE = 'Rane FOUR';
const DEFAULT_DEVICE = { deviceId: 'default', label: 'Predeterminado', kind: 'audiooutput' };
const RANE_DEVICE = { deviceId: 'rane', label: RANE, kind: 'audiooutput' };
const DEVICES = [DEFAULT_DEVICE, RANE_DEVICE];

class Node {
  connect() { return this; }
  disconnect() {}
}
class ContextFake {
  constructor() {
    this.destination = {
      channelCount: 2, maxChannelCount: 14, channelCountMode: 'max', channelInterpretation: 'speakers',
      connect() { return this; }, disconnect() {},
    };
    this.currentTime = 0;
  }
  createMediaElementSource() { return new Node(); }
  createChannelSplitter() { return new Node(); }
  createChannelMerger() { return new Node(); }
  createGain() { const gain = new Node(); gain.gain = { value: 0 }; return gain; }
  createOscillator() { const osc = new Node(); osc.frequency = { value: 0 }; osc.start = () => {}; osc.stop = () => {}; return osc; }
  async setSinkId() {}
  async close() {}
}

function controllerWith(storage, devices = DEVICES) {
  return new PreviewOutput({
    enumerateDevices: () => Promise.resolve(devices),
    createAudioContext: () => new ContextFake(),
    storage,
    changed: () => {},
  });
}

/** A bridge fake that records every saved value. */
function bridge(options = {}) {
  const calls = [];
  const api = {};
  if (options.answer !== undefined) {
    api.getPreviewSetup = async () => {
      if (options.answer instanceof Error) throw options.answer;
      return typeof options.answer === 'function' ? options.answer() : options.answer;
    };
  }
  if (options.save !== 'absent') {
    // 'throw' refuses synchronously, 'reject' with a rejection: neither may reach the screen.
    api.savePreviewSetup = options.save === 'throw'
      ? () => { throw new Error('el host no guarda'); }
      : async (value) => {
        if (options.save === 'reject') throw new Error('el host no guarda');
        calls.push(value);
      };
  }
  return { api, calls };
}

const SETUP = {
  output: { label: RANE, pair: '3-4' },
  calibration: { [RANE]: { '1-2': 'phones', '3-4': 'channel:1', '5-6': 'room' } },
};
const SHAPE = ['calibration', 'output'];

test('S14 (b): the value the host keeps is what the controller restores', async () => {
  const { api } = bridge({ answer: SETUP });
  const storage = createPreviewSetupStorage(api);
  assert.equal(await storage.load(), true);
  const controller = controllerWith(storage);
  try {
    assert.equal(controller.label, RANE);
    assert.deepEqual(controller.calibration, SETUP.calibration[RANE]);
    // The pair the host kept is the one that comes back, with its calibration.
    assert.equal(controller.pair, '3-4');
  } finally { controller.dispose(); }
});

test('S14 (b): the app asks once at start, then the controller applies the remembered choice', async () => {
  const { api } = bridge({ answer: SETUP });
  const storage = createPreviewSetupStorage(api);
  const controller = controllerWith(storage);
  try {
    // Before the host answers the preview starts on the system output.
    assert.equal(controller.label, null);
    assert.equal(await storage.load(), true);
    controller.reload();
    assert.equal(controller.label, RANE);
    assert.equal(controller.pair, '3-4');
    assert.deepEqual(controller.calibration, SETUP.calibration[RANE]);
    await controller.refresh();
    assert.equal(controller.label, RANE);
    assert.equal(controller.message, '');
  } finally { controller.dispose(); }
});

test('S14 (b): a change of output, of pair and of calibration saves the whole value', async () => {
  const { api, calls } = bridge({ answer: { output: null, calibration: {} } });
  const storage = createPreviewSetupStorage(api);
  await storage.load();
  const controller = controllerWith(storage);
  try {
    await controller.refresh();
    let seen = calls.length;
    controller.select(RANE);
    assert.ok(calls.length > seen, 'choosing the output saves');
    assert.deepEqual(calls.at(-1), { output: { label: RANE, pair: '5-6' }, calibration: {} });

    seen = calls.length;
    controller.selectPair('7-8');
    assert.ok(calls.length > seen, 'choosing the pair saves');
    assert.deepEqual(calls.at(-1), { output: { label: RANE, pair: '7-8' }, calibration: {} });

    seen = calls.length;
    controller.saveCalibration({ '1-2': 'phones', '3-4': 'channel:2' });
    assert.ok(calls.length > seen, 'saving the calibration saves');
    assert.deepEqual(calls.at(-1), {
      output: { label: RANE, pair: '1-2' },
      calibration: { [RANE]: { '1-2': 'phones', '3-4': 'channel:2' } },
    });

    // Every call carries the whole setup of S14 (a), never one key alone.
    for (const call of calls) {
      assert.deepEqual(Object.keys(call).sort(), SHAPE);
      assert.ok(Object.hasOwn(call, 'output') && Object.hasOwn(call, 'calibration'));
    }
  } finally { controller.dispose(); }
});

test('S14 (b): a failed load starts with the system output and no calibration', async () => {
  const failed = bridge({ answer: new Error('el host no responde') });
  const broken = bridge({ answer: { output: { label: RANE, pair: 'nueve' }, calibration: {} } });
  const garbage = bridge({ answer: { output: null, calibration: 'nada' } });
  for (const { api } of [failed, broken, garbage]) {
    const storage = createPreviewSetupStorage(api);
    assert.equal(await storage.load(), false);
    const controller = controllerWith(storage);
    try {
      assert.equal(controller.label, null);
      assert.equal(controller.pair, '1-2');
      assert.equal(controller.calibration, null);
    } finally { controller.dispose(); }
  }
});

test('S14 (b): a failed save throws nothing and keeps the session choice', async () => {
  for (const save of ['reject', 'throw']) {
    const { api } = bridge({ answer: { output: null, calibration: {} }, save });
    const storage = createPreviewSetupStorage(api);
    await storage.load();
    const controller = controllerWith(storage);
    try {
      await controller.refresh();
      assert.doesNotThrow(() => controller.select(RANE));
      assert.equal(controller.label, RANE);
      assert.doesNotThrow(() => controller.selectPair('7-8'));
      assert.equal(controller.pair, '7-8');
      assert.doesNotThrow(() => controller.saveCalibration({ '1-2': 'phones' }));
      assert.deepEqual(controller.calibration, { '1-2': 'phones' });
      assert.deepEqual(JSON.parse(storage.getItem(OUTPUT_KEY)), { label: RANE, pair: '1-2' });
    } finally { controller.dispose(); }
  }
});

test('S14 (b): without the bridge methods nothing breaks', async () => {
  for (const api of [undefined, {}]) {
    const storage = createPreviewSetupStorage(api);
    assert.equal(await storage.load(), false);
    const controller = controllerWith(storage);
    try {
      await controller.refresh();
      controller.select(RANE);
      controller.selectPair('5-6');
      controller.saveCalibration({ '1-2': 'phones', '3-4': 'room' });
      assert.equal(controller.label, RANE);
      assert.equal(controller.pair, '1-2');
      assert.deepEqual(controller.calibration, { '1-2': 'phones', '3-4': 'room' });
      assert.deepEqual(JSON.parse(storage.getItem(OUTPUT_KEY)), { label: RANE, pair: '1-2' });
      assert.deepEqual(JSON.parse(storage.getItem(CALIBRATION_KEY)), { [RANE]: { '1-2': 'phones', '3-4': 'room' } });
    } finally { controller.dispose(); }
  }
});
