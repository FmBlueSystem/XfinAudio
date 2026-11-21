const { copyFileSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const output = path.join(root, '.out/renderer');
mkdirSync(output, { recursive: true });
const { version } = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'));
if (typeof version !== 'string' || !/^[A-Za-z0-9.+_-]+$/.test(version)) throw new Error('Invalid package version');
const placeholder = '<span class="version-pill" id="app-version"></span>';
const html = readFileSync(path.join(root, 'renderer/index.html'), 'utf8');
if (html.split(placeholder).length !== 2) throw new Error('Version badge placeholder must appear exactly once');
writeFileSync(
  path.join(output, 'index.html'),
  html.replace(placeholder, `<span class="version-pill" id="app-version">v${version}</span>`),
);
copyFileSync(path.join(root, 'renderer/styles.css'), path.join(output, 'styles.css'));
