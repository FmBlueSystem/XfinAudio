import assert from 'node:assert/strict';
import test from 'node:test';
import {
  chooseIds, chosenMessage, chipRemoveLabel, clearedMessage, emptyChoiceLabel, pickerChoice, pickerChoices,
  removeId, removedMessage,
} from '../.out/renderer/track-picker.js';

const tracks = [
  { id: 'a'.repeat(64), title: 'Brújula', artist: 'Björk', bpm: 124, key: '8A', genre: 'Deep House' },
  { id: 'b'.repeat(64), title: 'Midnight', artist: 'Other', bpm: 126, key: '9B', genre: 'Techno' },
];
const gone = 'f'.repeat(64);

test('the closing picker holds one track and every choice replaces the previous one', () => {
  assert.deepEqual(chooseIds([], tracks[0].id, false), [tracks[0].id]);
  assert.deepEqual(chooseIds([tracks[0].id], tracks[1].id, false), [tracks[1].id]);
  assert.deepEqual(chooseIds([tracks[0].id], tracks[0].id, false), [tracks[0].id]);
});

test('required and excluded pickers hold several tracks once each, in the order the user chose them', () => {
  assert.deepEqual(chooseIds([], tracks[1].id, true), [tracks[1].id]);
  assert.deepEqual(chooseIds([tracks[1].id], tracks[0].id, true), [tracks[1].id, tracks[0].id]);
  assert.deepEqual(chooseIds([tracks[1].id], tracks[1].id, true), [tracks[1].id]);
  const current = [tracks[0].id];
  const next = chooseIds(current, tracks[1].id, true);
  assert.deepEqual(current, [tracks[0].id], 'choosing never mutates the list it was given');
  assert.notEqual(next, current);
});

test('Quitar removes exactly one choice and leaves the others in order', () => {
  assert.deepEqual(removeId([tracks[0].id, tracks[1].id], tracks[0].id), [tracks[1].id]);
  assert.deepEqual(removeId([tracks[1].id, tracks[0].id], tracks[0].id), [tracks[1].id]);
  assert.deepEqual(removeId([tracks[0].id], tracks[1].id), [tracks[0].id]);
  assert.deepEqual(removeId([], tracks[0].id), []);
});

test('chips reuse the shared track labels and mark a track that left the library as unavailable', () => {
  assert.deepEqual(pickerChoice(tracks[0].id, tracks), { id: tracks[0].id, label: 'Brújula · Björk', meta: '124 BPM · 8A', available: true });
  assert.deepEqual(pickerChoice(gone, tracks), { id: gone, label: 'No disponible: ffffffff', meta: 'Ya no está en la biblioteca.', available: false });
  assert.deepEqual(pickerChoices(['', tracks[1].id], tracks).map((choice) => choice.label), ['Midnight · Other'], 'an empty id is never a choice');
  assert.deepEqual(pickerChoices([], tracks), []);
});

test('each picker announces its choice, its clearing and its empty state in Spanish', () => {
  assert.equal(chosenMessage('end', 'Brújula · Björk'), 'Pista de cierre: Brújula · Björk.');
  assert.equal(chosenMessage('required', 'Brújula · Björk'), 'Pista obligatoria: Brújula · Björk.');
  assert.equal(chosenMessage('excluded', 'Brújula · Björk'), 'Pista excluida: Brújula · Björk.');
  assert.equal(clearedMessage('end'), 'Sin preferencia de cierre.');
  assert.equal(clearedMessage('required'), 'Sin pistas obligatorias.');
  assert.equal(clearedMessage('excluded'), 'Sin pistas excluidas.');
  assert.equal(emptyChoiceLabel('end'), 'Sin preferencia');
  assert.equal(emptyChoiceLabel('required'), 'Sin pistas obligatorias');
  assert.equal(emptyChoiceLabel('excluded'), 'Sin pistas excluidas');
  assert.equal(removedMessage('Brújula · Björk'), 'Quitada: Brújula · Björk.');
  assert.equal(chipRemoveLabel('Brújula · Björk'), 'Quitar Brújula · Björk');
});
