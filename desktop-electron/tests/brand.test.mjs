import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const read=(path)=>readFile(new URL(path,import.meta.url),'utf8');

test('the sidebar signs the app «by BlueSystemAudio» next to its name',async()=>{
  const html=await read('../renderer/index.html');
  assert.match(html,/Xfin<span class="brand-light">Audio<\/span>/,'the app keeps its name');
  assert.match(html,/<small class="brand-by">by <b class="brand-owner"><span class="brand-owner-blue">Blue<\/span>System<span class="brand-owner-light">Audio<\/span><\/b><\/small>/);
  const css=await read('../renderer/styles.css');
  assert.match(css,/\.brand-owner-blue \{ color: #3b8cff; \}/);
});

test('the About panel and the package carry the brand',async()=>{
  const main=await read('../src/main.ts');
  assert.match(main,/setAboutPanelOptions\(\{applicationName:'XfinAudio',applicationVersion:app\.getVersion\(\),copyright:'by BlueSystemAudio'\}\)/);
  assert.equal(JSON.parse(await read('../package.json')).author,'BlueSystemAudio');
});
