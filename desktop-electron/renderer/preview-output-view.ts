/** S11 (c): the «Salida de preescucha» setting, under «Seguir a Serato»; S12 adds the mixer channel. */
import { SYSTEM_OUTPUT, channelHint, channelNotice, channelOptions, channelOfPair } from './preview-output.js';
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
    const channels = controller.channels;
    // S12 (c): the option's value is the pair, so one select can show either.
    const channel = channelOfPair(channels, pairSelect.value);
    if (channel === null) { controller.selectPair(pairSelect.value); return; }
    controller.selectChannel(channel);
  });
  tone.addEventListener('click', () => { controller.tone(); });

  return {
    node: section,
    render(playing?: readonly PreviewPlaying[] | null): void {
      const system = controller.label === null;
      const answer = playing ?? null;
      const channels = controller.channels;
      const mixer = channels.length > 0;
      const channel = controller.channel;
      outputSelect.replaceChildren(option(SYSTEM_OUTPUT, ''), ...controller.outputs.map((output) => option(output.label, output.label)));
      outputSelect.value = controller.label ?? '';
      pairField.hidden = system;
      pairCaption.textContent = mixer ? MIXER_CHANNEL_LABEL : PAIRS_LABEL;
      pairSelect.setAttribute('aria-label', mixer ? MIXER_CHANNEL_LABEL : PAIRS_ARIA_LABEL);
      if (mixer) {
        const choices = channelOptions(channels, answer);
        pairSelect.replaceChildren(...choices.map((entry) => option(entry.caption, entry.pair)));
        // The pair stays the stored value: the select only shows it as its channel.
        pairSelect.value = choices.find((entry) => entry.number === channel)?.pair ?? '';
      } else {
        pairSelect.replaceChildren(...controller.pairs.map((pair) => option(pair, pair)));
        pairSelect.value = controller.pair;
      }
      tone.disabled = !controller.available;
      const notice = mixer ? channelNotice(channels, channel, answer) : '';
      channelMessage.hidden = !notice;
      channelMessage.textContent = notice;
      // S12 (e): the Rane FOUR names the channel instead of the generic line of S11 (c).
      hint.textContent = mixer && channel !== null ? channelHint(channel) : MIXER_HINT;
      message.hidden = !controller.message;
      message.textContent = controller.message;
    },
  };
}
