import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {APP_URL,APP_ORIGIN,permissionCheckAllowed}=require('../.out/main/security.js');

test('S11a: the app page may check media and speaker selection',()=>{
  // The app origin is the origin of the app page, so a check from that page matches it.
  assert.equal(APP_URL,APP_ORIGIN+'/index.html');
  assert.equal(permissionCheckAllowed('media',APP_ORIGIN,APP_ORIGIN,'audio'),true);
  // Electron reports the origin of the app page with a trailing slash.
  assert.equal(permissionCheckAllowed('media',APP_ORIGIN+'/',APP_ORIGIN,'audio'),true);
  assert.equal(permissionCheckAllowed('speaker-selection',APP_ORIGIN+'/',APP_ORIGIN),true);
  // Audio only: camera labels and an unspecified media type stay refused.
  assert.equal(permissionCheckAllowed('media',APP_ORIGIN,APP_ORIGIN,'video'),false);
  assert.equal(permissionCheckAllowed('media',APP_ORIGIN,APP_ORIGIN),false);
  assert.equal(permissionCheckAllowed('speaker-selection',APP_ORIGIN,APP_ORIGIN),true);
});

test('S11a: the same checks from another origin are refused',()=>{
  const origins=['https://evil.test','https://ui','xfin-app://other','xfin-app://ui/index.html',APP_ORIGIN+'//',APP_ORIGIN+'#main','file:///index.html','null','','xfin-app://UI',' xfin-app://ui'];
  for(const origin of origins) for(const permission of ['media','speaker-selection'])
    assert.equal(permissionCheckAllowed(permission,origin,APP_ORIGIN,'audio'),false,`${permission} from ${JSON.stringify(origin)} must be refused`);
});

test('S11a: every other check is refused',()=>{
  const others=['geolocation','notifications','midi','midiSysex','clipboard-read','clipboard-sanitized-write','fullscreen','openExternal','pointerLock','display-capture','mediaKeySystem','idle-detection','storage-access','top-level-storage-access','window-management','hid','serial','usb','bluetooth','fileSystem','unknown','Media',''];
  for(const permission of others)
    assert.equal(permissionCheckAllowed(permission,APP_ORIGIN,APP_ORIGIN,'audio'),false,`${JSON.stringify(permission)} must be refused`);
});

test('S11a: every permission request is refused, media included',async()=>{
  const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8');
  // One request handler, always refusing: no microphone or camera capture can be granted.
  assert.match(main,/setPermissionRequestHandler\(\(_contents,_permission,callback\)=>callback\(false\)\)/,'every permission request stays refused');
  assert.doesNotMatch(main,/callback\(true\)/,'no request may be granted');
  // The check handler is the shared decision, wired with the app origin as the only allowed one.
  assert.match(main,/setPermissionCheckHandler\(\(_contents,permission,requestingOrigin,details\)=>permissionCheckAllowed\(permission,requestingOrigin,APP_ORIGIN,\(details as \{mediaType\?:string\}\)\.mediaType\)\)/,'checks go through the shared decision');
  assert.match(main,/import \{[^}]*\bAPP_ORIGIN\b[^}]*\bpermissionCheckAllowed\b[^}]*\} from '\.\/security'/,'main imports the decision and the app origin');
});
