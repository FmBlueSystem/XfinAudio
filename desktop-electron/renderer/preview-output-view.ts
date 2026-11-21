/** S11 (c): the «Salida de preescucha» setting, under «Seguir a Serato»; S12 adds the mixer channel. */
import { DESTINATION_LABEL, SYSTEM_OUTPUT, PHONES_HINT, channelHint, channelNotice } from './preview-output.js';
import type { PreviewOutputController, PreviewPlaying } from './preview-output.js';

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
  section.append(heading, outputField, pairField, channelMessage, tone, hint, message);

  outputSelect.addEventListener('change', () => { controller.select(outputSelect.value || null); });
  pairSelect.addEventListener('change', () => {
    // S13 (b): the option's value is the pair in all three cases, so the stored value stays
    // `{label, pair}` and a calibrated channel is only another way to choose it.
    controller.selectPair(pairSelect.value);
  });
  tone.addEventListener('click', () => { controller.tone(); });

  return {
    node: section,
    render(playing?: readonly PreviewPlaying[] | null): void {
      const system = controller.label === null;
      const answer = playing ?? null;
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
    },
  };
}
