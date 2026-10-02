import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {parseRange, assertTrackId, assetPath, isTrustedSender, validateRequest} = require('../.out/main/security.js');

test('ranges support full, suffix and open-ended audio seeking', () => {
  assert.deepEqual(parseRange(null, 100), {start:0,end:99,status:200});
  assert.deepEqual(parseRange('bytes=10-19',100),{start:10,end:19,status:206});
  assert.deepEqual(parseRange('bytes=95-',100),{start:95,end:99,status:206});
  assert.deepEqual(parseRange('bytes=-20',100),{start:80,end:99,status:206});
  assert.deepEqual(parseRange('bytes=50-500',100),{start:50,end:99,status:206});
});
test('reject invalid, multiple, unsafe numeric and unsatisfiable ranges', () => {
  for (const value of ['bytes=100-','bytes=10-2','bytes=-0','bytes=0-1,5-6','items=0-1','bytes=1e2-','bytes=9007199254740992-']) assert.throws(()=>parseRange(value,100));
  assert.throws(()=>parseRange('bytes=0-',0));
});
test('opaque identities and assets cannot expose arbitrary files', () => {
  assertTrackId('a'.repeat(64));
  for(const value of ['../secrets','a'.repeat(63),'file:///tmp/a','A'.repeat(64)]) assert.throws(()=>assertTrackId(value));
  assert.equal(assetPath('xfin-app://ui/index.html','/tmp/ui'),'/tmp/ui/index.html');
  for(const url of ['https://ui/index.html','xfin-app://other/index.html','xfin-app://ui/%2e%2e%2fsecret','xfin-app://ui/a.json','xfin-app://ui/index.html?q=x']) assert.throws(()=>assetPath(url,'/tmp/ui'));
});
test('IPC is origin gated and rejects extra fields, prototypes and malformed input', () => {
  assert.equal(isTrustedSender('xfin-app://ui/index.html'),true);
  assert.equal(isTrustedSender('xfin-app://ui/index.html#main-content'),true);
  assert.equal(isTrustedSender('xfin-app://ui/index.html?remote=1'),false);
  for(const url of ['https://evil.test','xfin-app://ui/other.html','file:///index.html']) assert.equal(isTrustedSender(url),false);
  assert.deepEqual(validateRequest('generatePrep',{targetTrackCount:12,name:'Session'}),{targetTrackCount:12,name:'Session'});
  for(const request of [{targetTrackCount:1},{targetTrackCount:12,path:'/etc/passwd'},{targetTrackCount:NaN},{targetTrackCount:12,name:'x'.repeat(201)}]) assert.throws(()=>validateRequest('generatePrep',request));
  assert.throws(()=>validateRequest('exec',{command:'id'}));
  assert.throws(()=>validateRequest('savePlaylist',{name:'test',reviewId:'../x'}));
});
