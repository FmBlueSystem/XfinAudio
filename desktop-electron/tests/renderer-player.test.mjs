import assert from 'node:assert/strict';
import test from 'node:test';
import { createPlayer } from '../.out/renderer/player.js';

class Element extends EventTarget {
  value = '0';
  textContent = '';
  disabled = false;
  attributes = {};
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
}
class AudioElement extends Element {
  paused = true;
  duration = 300;
  currentTime = 0;
  volume = 1;
  src = '';
  pauses = 0;
  loads = 0;
  playResult = null;
  async play() { this.paused = false; this.dispatchEvent(new Event('play')); if (this.playResult) await this.playResult; }
  pause() { this.pauses += 1; this.paused = true; this.dispatchEvent(new Event('pause')); }
  load() { this.loads += 1; this.currentTime = 0; this.dispatchEvent(new Event('loadedmetadata')); }
}
function fixture(onStateChange = () => {}) {
  const elements = Object.fromEntries(['player-toggle', 'player-seek', 'player-current', 'player-duration', 'player-volume', 'player-status', 'player-title', 'player-artist'].map((id) => [id, new Element()]));
  elements['audio-player'] = new AudioElement();
  const previous = globalThis.document;
  globalThis.document = { getElementById: (id) => elements[id] };
  const player = createPlayer(onStateChange);
  return { player, elements, audio: elements['audio-player'], restore: () => { globalThis.document = previous; } };
}
const first = { id: 'one', title: '<script>one</script>', artist: 'Artist', bpm: 120, key: '8A', energy: 5, duration: 300 };
const second = { ...first, id: 'two', title: 'Two' };

test('persistent player toggles, switches original sources, seeks, adjusts volume and stops missing tracks', async () => {
  const { player, audio, elements, restore } = fixture();
  try {
    await player.select(first);
    assert.equal(audio.src, 'xfin-audio://track/one');
    assert.equal(elements['player-title'].textContent, first.title);
    assert.equal(player.isPlaying('one'), true);
    await player.select(first);
    assert.equal(audio.paused, true);
    assert.equal(audio.loads, 1);
    await player.select(second);
    assert.equal(audio.src, 'xfin-audio://track/two');
    assert.equal(audio.loads, 2);
    assert.ok(audio.pauses >= 3);
    elements['player-seek'].value = '125';
    elements['player-seek'].dispatchEvent(new Event('input'));
    assert.equal(audio.currentTime, 125);
    elements['player-volume'].value = '0.35';
    elements['player-volume'].dispatchEvent(new Event('input'));
    assert.equal(audio.volume, 0.35);
    player.stopIfMissing(new Set(['two']));
    assert.equal(player.isPlaying('two'), true);
    player.stopIfMissing(new Set());
    assert.equal(audio.paused, true);
    assert.equal(elements['player-toggle'].disabled, true);
  } finally { restore(); }
});

test('late rejection from a previous source cannot replace the newly selected track status', async () => {
  const { player, audio, elements, restore } = fixture();
  try {
    let reject;
    audio.playResult = new Promise((_, rejectPromise) => { reject = rejectPromise; });
    const pending = player.select(first);
    audio.playResult = null;
    await player.select(second);
    reject(new Error('Old source failed'));
    await pending;
    assert.equal(elements['player-title'].textContent, 'Two');
    assert.equal(elements['player-artist'].textContent, 'Artist');
    assert.equal(player.isPlaying('two'), true);
  } finally { restore(); }
});


test('transport time updates do not traverse every library row', async () => {
  let notifications = 0;
  const { player, audio, elements, restore } = fixture(() => { notifications += 1; });
  try {
    await player.select(first);
    const before = notifications;
    audio.currentTime = 140;
    audio.dispatchEvent(new Event('timeupdate'));
    assert.equal(elements['player-current'].textContent, '2:20');
    assert.equal(notifications, before);
  } finally { restore(); }
});

test('initial preference volume loads once, respects touched footer, and only explicit save overrides the session', () => {
  const f = fixture(); try {
    assert.equal(f.audio.volume, 0.7); assert.equal(f.elements['player-volume'].value, '0.7');
    f.player.applyPreferencesVolume(0.25, 'load'); assert.equal(f.audio.volume, 0.25);
    f.elements['player-volume'].value = '0.6'; f.elements['player-volume'].dispatchEvent(new Event('input'));
    f.player.applyPreferencesVolume(0.3, 'load'); assert.equal(f.audio.volume, 0.6);
    f.player.applyPreferencesVolume(0.4, 'save'); assert.equal(f.audio.volume, 0.4); assert.equal(f.audio.paused, true);
    f.player.applyPreferencesVolume(NaN, 'save'); assert.equal(f.audio.volume, 0.4);
  } finally { f.restore(); }
  const g = fixture(); try { g.elements['player-volume'].value = '0.9'; g.elements['player-volume'].dispatchEvent(new Event('input')); g.player.applyPreferencesVolume(0.2, 'load'); assert.equal(g.audio.volume, 0.9); } finally { g.restore(); }
});
