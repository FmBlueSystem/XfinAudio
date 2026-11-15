import { BOT_BUTTON_LABEL, BOT_MINIMIZE, BOT_WINDOW_TITLE } from './bot-window.js';
import type { BotWindowController } from './bot-window.js';
const SVG_NS = 'http://www.w3.org/2000/svg';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
/**
 * Draws one SVG element through DOM calls. `createElementNS` is the browser path; a test
 * double that only offers `createElement` still gets a node with the same attributes.
 */
const shape = (tag: string): SVGElement => typeof document.createElementNS === 'function'
  ? document.createElementNS(SVG_NS, tag)
  : document.createElement(tag) as unknown as SVGElement;
const set = (node: SVGElement, attrs: Record<string, string>): void => { for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value); };
/** S1's bot icon: a small robot head, inline and built here — never markup, never an image file. */
function botIcon(): SVGElement {
  const icon = shape('svg');
  set(icon, { class: 'bot-icon', viewBox: '0 0 24 24', width: '24', height: '24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false' });
  const antenna = shape('line'); set(antenna, { x1: '12', y1: '2.5', x2: '12', y2: '6' });
  const head = shape('rect'); set(head, { x: '3.5', y: '6', width: '17', height: '13', rx: '4' });
  const leftEye = shape('circle'); set(leftEye, { cx: '9', cy: '12', r: '1.5', fill: 'currentColor', stroke: 'none' });
  const rightEye = shape('circle'); set(rightEye, { cx: '15', cy: '12', r: '1.5', fill: 'currentColor', stroke: 'none' });
  const mouth = shape('line'); set(mouth, { x1: '9', y1: '15.5', x2: '15', y2: '15.5' });
  icon.append(antenna, head, leftEye, rightEye, mouth);
  return icon;
}
/**
 * S1's bot button and floating window. The button is fixed at the bottom right and carries
 * the pending-changes badge; the window floats over the page — not modal, so the list behind
 * stays usable — and holds the whole list chat, mounted once so minimising keeps the
 * conversation. Both are hidden outside the screen that owns the chat.
 */
export function createBotWindowView(root: HTMLElement, controller: BotWindowController, options: { mount: (container: HTMLElement) => void }): () => void {
  const toggle = make('button', '', 'bot-button');
  toggle.id = 'bot-window-toggle'; toggle.type = 'button';
  toggle.setAttribute('aria-label', BOT_BUTTON_LABEL);
  toggle.setAttribute('aria-controls', 'bot-window');
  toggle.setAttribute('aria-expanded', 'false');
  const badge = make('span', '', 'bot-badge');
  badge.id = 'bot-window-badge';
  toggle.append(botIcon(), badge);
  const panel = make('section', '', 'bot-window');
  panel.id = 'bot-window'; panel.tabIndex = -1;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-labelledby', 'bot-window-heading');
  const header = make('header', '', 'bot-window-header');
  const heading = make('h3', BOT_WINDOW_TITLE, 'bot-window-heading');
  heading.id = 'bot-window-heading';
  const minimize = make('button', BOT_MINIMIZE, 'button subtle');
  minimize.id = 'bot-window-minimize'; minimize.type = 'button';
  header.append(heading, minimize);
  // The whole existing list chat lives here, exactly once: the app mounts it into this node.
  const container = make('div', '', 'bot-window-body');
  container.id = 'list-chat-container';
  panel.append(header, container);
  toggle.addEventListener('click', () => controller.toggle());
  minimize.addEventListener('click', () => controller.minimize());
  // Escape minimises while the window is open; it never closes anything else on the screen.
  const onKey = (event: Event): void => {
    if ((event as KeyboardEvent).key !== 'Escape' || !controller.open) return;
    event.preventDefault();
    controller.minimize();
  };
  const keyTarget: EventTarget | null = typeof document.addEventListener === 'function' ? document
    : typeof window !== 'undefined' && typeof window.addEventListener === 'function' ? window : null;
  keyTarget?.addEventListener('keydown', onKey as EventListener);
  root.replaceChildren(toggle, panel);
  options.mount(container);
  let wasOpen = false;
  const render = (): void => {
    const count = controller.badge;
    root.hidden = !controller.available;
    toggle.setAttribute('aria-expanded', String(controller.open));
    badge.hidden = count === 0;
    badge.textContent = count > 0 ? String(count) : '';
    panel.hidden = !controller.open;
    if (controller.open && !wasOpen && typeof panel.focus === 'function') panel.focus();
    wasOpen = controller.open;
  };
  render();
  return render;
}
