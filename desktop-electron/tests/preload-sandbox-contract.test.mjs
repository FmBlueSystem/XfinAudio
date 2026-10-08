import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const read = (file) => readFile(new URL(`../src/${file}`, import.meta.url), 'utf8');

const importSpecifiers = (source) => [...source.matchAll(/\bfrom\s+'([^']+)'/g)].map((match) => match[1]);

// The renderer window is created with sandbox: true, and a sandboxed preload's
// require only resolves the electron built-in plus a small builtin allowlist —
// a relative require throws before exposeInMainWorld runs, so the renderer
// boots without the xfin API and shows the disconnected-service banner.
test('the sandboxed preload imports only the electron built-in', async () => {
  const preload = await read('preload.ts');
  const specifiers = importSpecifiers(preload);
  assert.notEqual(specifiers.length, 0, 'preload.ts is expected to import the electron built-in');
  for (const specifier of specifiers) {
    assert.equal(specifier, 'electron', `sandboxed preload cannot require '${specifier}'; import only the electron built-in`);
  }
});

// The unsandboxed main process keeps the launch guard: when the harness leaks
// ELECTRON_RUN_AS_NODE=1, require('electron') resolves to the npm package that
// exports the binary path string, and the shim turns that into an actionable
// error naming the variable and the launch command.
test('the main process wires the electron-shim launch guard', async () => {
  const main = await read('main.ts');
  assert.match(main, /from\s+'\.\/electron-shim'/, 'main.ts must import ./electron-shim');
  const shim = await read('electron-shim.ts');
  assert.match(shim, /ELECTRON_RUN_AS_NODE/, 'the shim must name the leaked variable in its error');
});
