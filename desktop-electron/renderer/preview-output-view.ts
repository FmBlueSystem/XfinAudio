/** S11 (c): the «Salida de preescucha» setting, under «Seguir a Serato». */
import { SYSTEM_OUTPUT } from './preview-output.js';
import type { PreviewOutputController } from './preview-output.js';

export const MIXER_HINT = 'La preescucha suena por el canal del mezclador que recibe esos canales: deja su fader abajo y activa su CUE para oírla solo en los auriculares.';

const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `preview-output-${suffix}`; return node; };
const option = (caption: string, value: string): HTMLOptionElement => { const node = make('option', caption); node.value = value; return node; };

export interface PreviewOutputView { node: HTMLElement; render(): void; }

export function createPreviewOutputView(controller: PreviewOutputController): PreviewOutputView {
  const section = identify(make('section', '', 'preview-output'), 'section');
  section.setAttribute('aria-labelledby', 'preview-output-heading');
  const heading = identify(make('h4', 'Salida de preescucha'), 'heading');
  const outputField = identify(make('label', '', 'preview-output-field'), 'output-field');
  const outputSelect = identify(make('select'), 'select');
  outputSelect.setAttribute('aria-label', 'Salida de preescucha');
  outputField.append(make('span', 'Salida'), outputSelect);
  // S11 (c): the pair is only meaningful for an output other than the system one.
  const pairField = identify(make('label', '', 'preview-output-field'), 'pair-field');
  const pairSelect = identify(make('select'), 'pair');
  pairSelect.setAttribute('aria-label', 'Canales de la salida de preescucha');
  pairField.append(make('span', 'Canales'), pairSelect);
  const tone = identify(make('button', 'Probar', 'button subtle'), 'tone');
  tone.type = 'button';
  tone.setAttribute('aria-label', 'Probar la salida de preescucha');
  const message = identify(make('p', '', 'field-hint'), 'message');
  message.setAttribute('role', 'status');
  section.append(heading, outputField, pairField, tone, identify(make('p', MIXER_HINT, 'field-hint'), 'hint'), message);

  outputSelect.addEventListener('change', () => { controller.select(outputSelect.value || null); });
  pairSelect.addEventListener('change', () => { controller.selectPair(pairSelect.value); });
  tone.addEventListener('click', () => { controller.tone(); });

  return {
    node: section,
    render(): void {
      const system = controller.label === null;
      outputSelect.replaceChildren(option(SYSTEM_OUTPUT, ''), ...controller.outputs.map((output) => option(output.label, output.label)));
      outputSelect.value = controller.label ?? '';
      pairField.hidden = system;
      pairSelect.replaceChildren(...controller.pairs.map((pair) => option(pair, pair)));
      pairSelect.value = controller.pair;
      tone.disabled = !controller.available;
      message.hidden = !controller.message;
      message.textContent = controller.message;
    },
  };
}
