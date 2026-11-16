import assert from 'node:assert/strict';
import test from 'node:test';
import { BotWindowController, BOT_BUTTON_LABEL, BOT_MINIMIZE, BOT_WINDOW_TITLE } from '../.out/renderer/bot-window.js';
import { createBotWindowView } from '../.out/renderer/bot-window-view.js';
/** S1: a round bot button with a badge and a non-modal floating window that holds the chat. */
class Element extends EventTarget {
  constructor(tag = 'div', namespaceURI = null) { super(); this.tagName = tag; this.namespaceURI = namespaceURI; }
  children = []; attrs = {}; textContent = ''; hidden = false; disabled = false; id = ''; className = ''; type = ''; tabIndex = -1; focused = false;
  setAttribute(key, value) { this.attrs[key] = String(value); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  focus() { this.focused = true; }
  set innerHTML(_) { throw new Error('Unsafe HTML'); }
}
const SVG_NS = 'http://www.w3.org/2000/svg';
const all = (node) => [node, ...node.children.flatMap(all)];
const text = (node) => [node.textContent, ...node.children.map(text)].join(' ');
function installDocument() {
  const previous = globalThis.document; const listeners = [];
  globalThis.document = {
    createElement: (tag) => new Element(tag),
    createElementNS: (namespace, tag) => new Element(tag, namespace),
    addEventListener: (type, handler) => { listeners.push([type, handler]); },
  };
  return {
    restore: () => { globalThis.document = previous; },
    key: (key) => { for (const [type, handler] of listeners) if (type === 'keydown') handler({ key, preventDefault() {} }); },
    listeners,
  };
}
function controllerFixture(pending = 0) {
  let count = pending; const renders = []; let allowed = true;
  const controller = new BotWindowController({
    canAct: () => allowed,
    changed: () => { renders.push(controller.open); },
    pending: () => count,
  });
  return { controller, renders, setPending: (value) => { count = value; }, block: () => { allowed = false; } };
}
function viewFixture(pending = 0) {
  const doc = installDocument(); const root = new Element(); const chat = new Element('p'); chat.textContent = 'Chat montado';
  let mounts = 0; let container = null;
  const { controller } = controllerFixture(pending);
  const render = createBotWindowView(root, controller, { mount: (target) => { mounts++; container = target; target.append(chat); } });
  return { root, controller, render, doc, chat, mounts: () => mounts, container: () => container, get: (id) => all(root).find((node) => node.id === id) };
}
test('the bot button carries the exact label and draws its icon as inline SVG built by DOM calls', () => {
  const f = viewFixture();
  try {
    f.controller.setAvailable(true); f.render();
    const button = f.get('bot-window-toggle');
    assert.ok(button);
    assert.equal(button.attrs['aria-label'], 'Abrir asistente de lista');
    assert.equal(BOT_BUTTON_LABEL, 'Abrir asistente de lista');
    assert.equal(button.type, 'button');
    const icon = all(button).find((node) => node.tagName === 'svg');
    assert.ok(icon, 'the icon is an inline svg');
    assert.equal(icon.namespaceURI, SVG_NS);
    assert.equal(icon.attrs['aria-hidden'], 'true');
    assert.ok(all(icon).some((node) => node.tagName === 'rect'), 'the bot head is drawn with shapes');
    assert.ok(all(icon).some((node) => node.tagName === 'circle'));
    assert.ok(!all(f.root).some((node) => node.tagName === 'img'), 'no image file is used');
  } finally { f.doc.restore(); }
});
test('the button is hidden outside the review screen and the window stays out of the page', () => {
  const f = viewFixture();
  try {
    f.controller.setAvailable(false); f.render();
    assert.equal(f.root.hidden, true);
    f.controller.setAvailable(true); f.render();
    assert.equal(f.root.hidden, false);
    assert.equal(f.get('bot-window').hidden, true);
    assert.equal(f.get('bot-window-toggle').hidden, false);
    assert.equal(f.get('bot-window-toggle').attrs['aria-expanded'], 'false');
  } finally { f.doc.restore(); }
});
test('the badge shows how many proposed changes are pending and is hidden at zero', () => {
  const f = viewFixture(3);
  try {
    f.controller.setAvailable(true); f.render();
    const badge = f.get('bot-window-badge');
    assert.equal(badge.hidden, false);
    assert.equal(badge.textContent, '3');
    assert.equal(f.get('bot-window-toggle').attrs['aria-label'], 'Abrir asistente de lista');
    f.controller.host.pending = () => 0;
    f.render();
    assert.equal(badge.hidden, true);
    assert.equal(badge.textContent, '');
  } finally { f.doc.restore(); }
});
test('the window opens from the button as a non-modal dialog with the exact title and Minimizar', () => {
  const f = viewFixture();
  try {
    f.controller.setAvailable(true); f.render();
    f.get('bot-window-toggle').dispatchEvent(new Event('click'));
    assert.equal(f.controller.open, true);
    f.render();
    const panel = f.get('bot-window');
    assert.equal(panel.hidden, false);
    assert.equal(panel.attrs.role, 'dialog');
    assert.equal(panel.attrs['aria-modal'], undefined, 'the list behind stays usable');
    assert.equal(f.get('bot-window-heading').textContent, 'Asistente de lista');
    assert.equal(BOT_WINDOW_TITLE, 'Asistente de lista');
    assert.equal(f.get('bot-window-minimize').textContent, 'Minimizar');
    assert.equal(BOT_MINIMIZE, 'Minimizar');
    assert.equal(f.get('bot-window-toggle').attrs['aria-expanded'], 'true');
    assert.equal(panel.focused, true);
    assert.match(text(f.get('list-chat-container')), /Chat montado/);
  } finally { f.doc.restore(); }
});
test('Minimizar hides the window, keeps the conversation mounted and the button reopens it', () => {
  const f = viewFixture();
  try {
    f.controller.setAvailable(true); f.render();
    f.get('bot-window-toggle').dispatchEvent(new Event('click')); f.render();
    assert.equal(f.mounts(), 1, 'the chat is mounted once, never rebuilt');
    const chat = f.chat;
    f.get('bot-window-minimize').dispatchEvent(new Event('click'));
    f.render();
    assert.equal(f.controller.open, false);
    assert.equal(f.get('bot-window').hidden, true);
    assert.equal(f.get('list-chat-container').children[0], chat, 'the conversation survives');
    f.get('bot-window-toggle').dispatchEvent(new Event('click')); f.render();
    assert.equal(f.get('bot-window').hidden, false);
    assert.equal(f.get('list-chat-container').children[0], chat);
    assert.equal(f.mounts(), 1);
  } finally { f.doc.restore(); }
});
test('Escape minimizes only while the window is open', () => {
  const f = viewFixture();
  try {
    f.controller.setAvailable(true); f.render();
    f.doc.key('Escape'); f.render();
    assert.equal(f.controller.open, false);
    f.get('bot-window-toggle').dispatchEvent(new Event('click')); f.render();
    assert.equal(f.controller.open, true);
    f.doc.key('Escape'); f.render();
    assert.equal(f.controller.open, false);
    assert.equal(f.get('bot-window').hidden, true);
    assert.equal(f.get('list-chat-container').children.length, 1, 'the conversation is kept');
  } finally { f.doc.restore(); }
});
test('the controller opens and minimizes only on the review screen and reports every change', () => {
  const f = controllerFixture();
  assert.equal(f.controller.badge, 0);
  f.controller.show();
  assert.equal(f.controller.open, false, 'nothing opens before the chat is available');
  f.controller.setAvailable(true);
  assert.deepEqual(f.renders, [false]);
  f.controller.show();
  assert.equal(f.controller.open, true);
  assert.equal(f.controller.canOpen, true);
  f.controller.toggle();
  assert.equal(f.controller.open, false);
  assert.deepEqual(f.renders, [false, true, false]);
  f.controller.show(); f.controller.setAvailable(false);
  assert.equal(f.controller.open, false, 'leaving the review screen closes the window');
  assert.equal(f.controller.available, false);
  assert.deepEqual(f.renders, [false, true, false, true, false]);
  f.controller.setAvailable(true);
  f.block();
  f.controller.setAvailable(true);
  assert.equal(f.controller.canOpen, false, 'a busy app keeps the button from claiming it can open');
});
