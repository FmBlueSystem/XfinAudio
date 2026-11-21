/** S11 (c): the «Salida de preescucha» setting, under «Seguir a Serato»; S12 adds the mixer channel. */
import { DESTINATION_LABEL, SYSTEM_OUTPUT, PHONES_HINT, channelHint, channelNotice } from './preview-output.js';
import type { CalibrationRole, PreviewOutputController, PreviewPlaying } from './preview-output.js';
import {
  CALIBRATION_ANSWERS, CALIBRATION_BUTTON, CALIBRATION_WARNING, CANCEL_BUTTON, CLEAR_CALIBRATION_BUTTON,
  QUESTION, REPEAT_TONE_BUTTON, START_BUTTON, CalibrationWizard, savedLine,
} from './preview-calibration.js';

export const MIXER_HINT = 'La preescucha suena por el canal del mezclador que recibe esos canales: deja su fader abajo y activa su CUE para oírla solo en los auriculares.';
/** S12 (a): for the Rane FOUR the pairs select becomes the mixer's channel select. */
export const MIXER_CHANNEL_LABEL = 'Canal del mezclador';
export const PAIRS_LABEL = 'Canales';
export const PAIRS_ARIA_LABEL = 'Canales de la salida de preescucha';

const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `preview-output-${suffix}`; return node; };
const option = (caption: string, value: string): HTMLOptionElement => { const node = make('option', caption); node.value = value; return node; };
const button = (caption: string, suffix: string, action: () => void, className = 'button subtle'): HTMLButtonElement => {
  const node = identify(make('button', caption, className), suffix);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
};

export interface PreviewOutputView {
  node: HTMLElement;
  /** S12 (b): the `playing` decks of the last answer; absent or null means no Serato answer. */
  render(playing?: readonly PreviewPlaying[] | null): void;
}

export function createPreviewOutputView(controller: PreviewOutputController): PreviewOutputView {
  const section = identify(make('section', '', 'preview-output'), 'section');
  section.setAttribute('aria-labelledby', 'preview-output-heading');
  const heading = identify(make('h4', 'Salida de preescucha'), 'heading');
  const outputField = identify(make('label', '', 'preview-output-field'), 'output-field');
  const outputSelect = identify(make('select'), 'select');
  outputSelect.setAttribute('aria-label', 'Salida de preescucha');
  outputField.append(make('span', 'Salida'), outputSelect);
  // S11 (c): the pair is only meaningful for an output other than the system one.
  // S12 (a): on the Rane FOUR this select shows the mixer channel of each pair instead.
  const pairField = identify(make('label', '', 'preview-output-field'), 'pair-field');
  const pairCaption = make('span', PAIRS_LABEL);
  const pairSelect = identify(make('select'), 'pair');
  pairSelect.setAttribute('aria-label', PAIRS_ARIA_LABEL);
  pairField.append(pairCaption, pairSelect);
  // S12 (d): the chosen channel Serato has a track on is announced, never blocked.
  const channelMessage = identify(make('p', '', 'field-hint'), 'channel-notice');
  channelMessage.setAttribute('role', 'status');
  const tone = identify(make('button', 'Probar', 'button subtle'), 'tone');
  tone.type = 'button';
  tone.setAttribute('aria-label', 'Probar la salida de preescucha');
  const hint = identify(make('p', MIXER_HINT, 'field-hint'), 'hint');
  const message = identify(make('p', '', 'field-hint'), 'message');
  message.setAttribute('role', 'status');
  // S13 (d): the wizard lives inside the setting; S13 (e) removes a calibration.
  const calibrationSaved = identify(make('p', '', 'field-hint'), 'calibration-saved');
  calibrationSaved.setAttribute('role', 'status');
  const wizardNode = identify(make('div', '', 'preview-calibration'), 'wizard');
  const actions = identify(make('div', '', 'preview-calibration-actions'), 'calibration-actions');
  section.append(heading, outputField, pairField, channelMessage, tone, hint, message, actions, calibrationSaved, wizardNode);

  /** S13 (d): the wizard's state; null when it is closed. */
  let wizard: CalibrationWizard | null = null;
  /** The output whose calibration the last wizard saved, so its line names it. */
  let savedFor: string | null = null;
  /** The last Serato answer, kept so a redraw of the wizard keeps the channel marks. */
  let answer: readonly PreviewPlaying[] | null = null;

  const calibrate = button(CALIBRATION_BUTTON, 'calibrate', () => {
    if (controller.label === null) return;
    savedFor = null;
    wizard = new CalibrationWizard(controller.pairs);
    controller.beginCalibration();
    render();
  });
  const clearCalibration = button(CLEAR_CALIBRATION_BUTTON, 'clear-calibration', () => {
    controller.clearCalibration();
    savedFor = null;
    render();
  });
  actions.append(calibrate, clearCalibration);

  const closeWizard = (): void => {
    wizard = null;
    controller.endCalibration();
  };

  /** S13 (d): «Empezar» puts the first pair on screen and sounds it once. */
  const begin = (): void => {
    if (wizard === null) return;
    wizard.start();
    const pair = wizard.pair;
    if (pair !== null) controller.toneOn(pair);
    render();
  };

  /** S13 (d): the answer moves on; the last one saves and closes. */
  const reply = (role: CalibrationRole): void => {
    const state = wizard;
    if (state === null) return;
    const next = state.answer(role);
    if (state.result !== null) {
      controller.saveCalibration(state.result);
      savedFor = controller.label;
      closeWizard();
    } else if (next !== null) controller.toneOn(next);
    render();
  };

  const cancel = (): void => {
    if (wizard === null) return;
    wizard.cancel();
    closeWizard();
    render();
  };

  const drawWizard = (): void => {
    const state = wizard;
    wizardNode.hidden = state === null;
    if (state === null) { wizardNode.replaceChildren(); return; }
    if (!state.started) {
      const warning = identify(make('p', CALIBRATION_WARNING, 'field-hint'), 'wizard-warning');
      wizardNode.replaceChildren(warning,
        button(START_BUTTON, 'wizard-start', begin, 'button'),
        button(CANCEL_BUTTON, 'wizard-cancel', cancel));
      return;
    }
    const answers = identify(make('div', '', 'preview-calibration-answers'), 'wizard-answers');
    answers.replaceChildren(...CALIBRATION_ANSWERS.map((entry) => {
      const control = button(entry.text, `answer-${entry.role.replace(':', '-')}`, () => { reply(entry.role); });
      return control;
    }));
    const repeat = button(REPEAT_TONE_BUTTON, 'wizard-repeat', () => {
      const pair = state.repeat();
      if (pair !== null) controller.toneOn(pair);
    });
    wizardNode.replaceChildren(
      identify(make('p', state.heading, 'preview-calibration-heading'), 'wizard-heading'),
      identify(make('p', QUESTION, 'field-hint'), 'wizard-question'),
      answers,
      repeat,
      button(CANCEL_BUTTON, 'wizard-cancel', cancel),
    );
  };

  function render(playing?: readonly PreviewPlaying[] | null): void {
    answer = playing ?? null;
    const system = controller.label === null;
    const channel = controller.channel;
    // S13 (b): one list for a calibrated output, the Rane FOUR table and the plain pairs.
    const destinations = controller.destinations(answer);
    const label = controller.destinationLabel || (controller.channels.length > 0 ? MIXER_CHANNEL_LABEL : PAIRS_LABEL);
    outputSelect.replaceChildren(option(SYSTEM_OUTPUT, ''), ...controller.outputs.map((output) => option(output.label, output.label)));
    outputSelect.value = controller.label ?? '';
    pairField.hidden = system || destinations.length === 0;
    pairCaption.textContent = label;
    pairSelect.setAttribute('aria-label', controller.destinationLabel ? DESTINATION_LABEL
      : controller.channels.length > 0 ? MIXER_CHANNEL_LABEL : PAIRS_ARIA_LABEL);
    pairSelect.replaceChildren(...destinations.map((entry) => option(entry.text, entry.pair)));
    pairSelect.value = destinations.some((entry) => entry.pair === controller.pair) ? controller.pair : '';
    tone.disabled = !controller.available;
    const notice = channel === null ? '' : channelNotice(controller.channels, channel, answer);
    channelMessage.hidden = !notice;
    channelMessage.textContent = notice;
    // S13 (c): a calibrated phones pair goes straight to the headphones; a channel keeps the
    // lines of S12 (d) and (e); every other output keeps the generic line of S11 (c).
    hint.textContent = controller.pairRole === 'phones'
      ? PHONES_HINT
      : channel !== null ? channelHint(channel) : MIXER_HINT;
    message.hidden = !controller.message;
    message.textContent = controller.message;
    // S13 (d): never for «Salida del sistema», and disabled while the output is not connected.
    calibrate.hidden = system;
    calibrate.disabled = !controller.connected;
    // S13 (e): only an output that has a calibration can lose it.
    clearCalibration.hidden = controller.calibration === null;
    const saved = savedFor !== null && savedFor === controller.label ? savedLine(savedFor) : '';
    calibrationSaved.hidden = !saved;
    calibrationSaved.textContent = saved;
    drawWizard();
  }

  outputSelect.addEventListener('change', () => {
    // The pairs of a wizard belong to one output: changing it abandons the wizard, unsaved.
    if (wizard !== null) closeWizard();
    savedFor = null;
    controller.select(outputSelect.value || null);
    render(answer);
  });
  pairSelect.addEventListener('change', () => {
    // S13 (b): the option's value is the pair in all three cases, so the stored value stays
    // `{label, pair}` and a calibrated channel is only another way to choose it.
    controller.selectPair(pairSelect.value);
    render(answer);
  });
  tone.addEventListener('click', () => { controller.tone(); });

  return { node: section, render };
}
