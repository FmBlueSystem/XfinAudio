import assert from 'node:assert/strict';
import test from 'node:test';
import {
  CALIBRATION_ANSWERS, CALIBRATION_WARNING, CANCEL_BUTTON, QUESTION, REPEAT_TONE_BUTTON, START_BUTTON,
  CalibrationWizard, savedLine,
} from '../.out/renderer/preview-calibration.js';

const PAIRS = ['1-2', '3-4', '5-6'];

test('S13 (d): the texts of the wizard, exactly', () => {
  assert.equal(CALIBRATION_WARNING, 'Baja el volumen de la sala antes de empezar: el tono va a sonar por cada salida.');
  assert.equal(START_BUTTON, 'Empezar');
  assert.equal(CANCEL_BUTTON, 'Cancelar');
  assert.equal(REPEAT_TONE_BUTTON, 'Repetir tono');
  assert.equal(QUESTION, '¿Dónde sonó?');
  assert.equal(savedLine('Rane FOUR'), 'Calibración guardada para Rane FOUR.');
  assert.deepEqual(CALIBRATION_ANSWERS.map((entry) => entry.text),
    ['Auriculares', 'Sala', 'Canal 1', 'Canal 2', 'Canal 3', 'Canal 4', 'No sonó']);
  assert.deepEqual(CALIBRATION_ANSWERS.map((entry) => entry.role),
    ['phones', 'room', 'channel:1', 'channel:2', 'channel:3', 'channel:4', 'silent']);
});

test('S13 (d): the wizard opens on the warning and starts on the first pair', () => {
  const wizard = new CalibrationWizard(PAIRS);
  assert.equal(wizard.open, true);
  assert.equal(wizard.started, false);
  assert.equal(wizard.pair, null);
  assert.equal(wizard.heading, '');
  assert.equal(wizard.index, 0);
  assert.equal(wizard.total, 3);
  wizard.start();
  assert.equal(wizard.started, true);
  assert.equal(wizard.index, 1);
  assert.equal(wizard.pair, '1-2');
  assert.equal(wizard.heading, 'Par 1-2 (1 de 3)');
});

test('S13 (d): an answer is kept and the next pair becomes the step', () => {
  const wizard = new CalibrationWizard(PAIRS);
  wizard.start();
  assert.equal(wizard.answer('room'), '3-4');
  assert.equal(wizard.index, 2);
  assert.equal(wizard.pair, '3-4');
  assert.equal(wizard.heading, 'Par 3-4 (2 de 3)');
  assert.deepEqual(wizard.answers, { '1-2': 'room' });
  assert.equal(wizard.result, null);
  assert.equal(wizard.open, true);
});

test('S13 (d): the last answer closes the wizard with the calibration', () => {
  const wizard = new CalibrationWizard(['1-2', '3-4']);
  wizard.start();
  wizard.answer('phones');
  assert.equal(wizard.answer('phones'), null);
  assert.equal(wizard.open, false);
  assert.equal(wizard.started, false);
  assert.equal(wizard.pair, null);
  // S13 (a): a second phones pair clears the earlier one to silent.
  assert.deepEqual(wizard.result, { '1-2': 'silent', '3-4': 'phones' });
});

test('S13 (d): «Repetir tono» names the pair of the step and never advances', () => {
  const wizard = new CalibrationWizard(PAIRS);
  assert.equal(wizard.repeat(), null, 'no tone before «Empezar»');
  wizard.start();
  wizard.answer('channel:1');
  assert.equal(wizard.repeat(), '3-4');
  assert.equal(wizard.index, 2);
  assert.equal(wizard.heading, 'Par 3-4 (2 de 3)');
});

test('S13 (d): «Cancelar» closes with nothing to save and ignores later answers', () => {
  const wizard = new CalibrationWizard(PAIRS);
  wizard.start();
  wizard.answer('room');
  wizard.cancel();
  assert.equal(wizard.open, false);
  assert.equal(wizard.result, null);
  assert.equal(wizard.pair, null);
  assert.equal(wizard.answer('phones'), null);
  assert.equal(wizard.result, null);
  // Before «Empezar» there is no question, so there is no answer either.
  const untouched = new CalibrationWizard(PAIRS);
  assert.equal(untouched.answer('phones'), null);
  assert.deepEqual(untouched.answers, {});
  assert.equal(untouched.open, true);
});
