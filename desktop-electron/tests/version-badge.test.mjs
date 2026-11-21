import assert from 'node:assert/strict';
import test from 'node:test';
import { execFileSync } from 'node:child_process';
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = readFileSync(path.join(root, 'renderer/index.html'), 'utf8');
const styles = readFileSync(path.join(root, 'renderer/styles.css'), 'utf8');
const { version } = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'));
const differentVersion = version === '9.9.9' ? '8.8.8' : '9.9.9';
const placeholder = '<span class="version-pill" id="app-version"></span>';
const badge = (value) => `<span class="version-pill" id="app-version">v${value}</span>`;

test('S18(e): the header version is built from package.json, never a literal in the page', () => {
  assert.doesNotMatch(source, /<span class="version-pill"[^>]*>v[^<]*<\/span>/, 'the page must not hard-code a version');
  assert.equal(source.includes(`v${version}`), false);
  assert.equal(source.includes(placeholder), true);
  mkdirSync('/private/tmp', { recursive: true });
  const scratch = mkdtempSync('/private/tmp/xfinaudio-version-');
  try {
    mkdirSync(path.join(scratch, 'scripts'), { recursive: true });
    mkdirSync(path.join(scratch, 'renderer'), { recursive: true });
    copyFileSync(path.join(root, 'scripts/copy-assets.cjs'), path.join(scratch, 'scripts/copy-assets.cjs'));
    copyFileSync(path.join(root, 'renderer/index.html'), path.join(scratch, 'renderer/index.html'));
    copyFileSync(path.join(root, 'renderer/styles.css'), path.join(scratch, 'renderer/styles.css'));
    writeFileSync(path.join(scratch, 'package.json'), JSON.stringify({ version: differentVersion }));
    execFileSync(process.execPath, [path.join(scratch, 'scripts/copy-assets.cjs')], { cwd: scratch });
    const built = readFileSync(path.join(scratch, '.out/renderer/index.html'), 'utf8');
    assert.equal(built.includes(badge(differentVersion)), true, 'a changed package version must change the badge');
    assert.equal(built.includes(`>v${version}<`), false, 'the badge must not keep the old version');
    assert.equal(readFileSync(path.join(scratch, '.out/renderer/styles.css'), 'utf8'), styles, 'styles.css stays byte-for-byte');
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
});

test('S18(e): the built header badge equals the current package version', () => {
  const built = readFileSync(path.join(root, '.out/renderer/index.html'), 'utf8');
  assert.equal(built.includes(badge(version)), true, `badge must be v${version}`);
  assert.equal(built.includes('v2.5.0'), false);
});
