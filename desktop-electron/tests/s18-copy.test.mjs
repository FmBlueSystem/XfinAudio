import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const renderer = (name) => new URL(`../renderer/${name}`, import.meta.url);
const python = (name) => new URL(`../../src/xfinaudio/${name}`, import.meta.url);
const sources = [
  ['renderer/app.ts', renderer('app.ts')],
  ['renderer/list-chat-view.ts', renderer('list-chat-view.ts')],
  ['renderer/optional-ai-view.ts', renderer('optional-ai-view.ts')],
  ['headless/ai_context.py', python('headless/ai_context.py')],
];
const forbidden = [
  'El asistente solo lee la lista: no cambia pistas, orden ni metadatos.',
  'La lista solo se lee: el asistente no la cambia.',
  'la lista solo se lee.',
  'No cambia el orden, las marcas ni la reproducción.',
  'La IA no cambia el orden ni controla Serato.',
  'no cambia pistas, orden ni metadatos',
  'el asistente no la cambia',
  'no cambia el orden',
];
const required = [
  ['renderer/app.ts', renderer('app.ts'), 'El asistente propone cambios y la app los aplica en tu equipo; puedes deshacerlos.'],
  ['renderer/list-chat-view.ts', renderer('list-chat-view.ts'), 'Los cambios se aplican en tu equipo y se pueden deshacer.'],
  ['renderer/optional-ai-view.ts', renderer('optional-ai-view.ts'), 'Los cambios se aplican en tu equipo y se pueden deshacer.'],
  ['renderer/optional-ai-view.ts', renderer('optional-ai-view.ts'), 'Las marcas y la reproducción siguen siendo manuales.'],
  ['headless/ai_context.py', python('headless/ai_context.py'), 'La IA no controla Serato.'],
  ['ai/list_chat.py', python('ai/list_chat.py'), 'Tú nunca cambias la lista'],
];

test('S18(a): no user-facing copy still says the assistant only reads or cannot change the list', () => {
  for (const [name, url] of sources) {
    const source = readFileSync(url, 'utf8');
    for (const phrase of forbidden) assert.equal(source.includes(phrase), false, `${name} still contains ${JSON.stringify(phrase)}`);
  }
  for (const [name, url, phrase] of required) {
    assert.equal(readFileSync(url, 'utf8').includes(phrase), true, `${name} is missing ${JSON.stringify(phrase)}`);
  }
});
