import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
const require=createRequire(import.meta.url);
const {validateRequest}=require('../.out/main/security.js');
test('metadata report is a parameter-free allowlisted read',()=>{
 assert.deepEqual(validateRequest('getMetadataReport',{}),{});
 assert.throws(()=>validateRequest('getMetadataReport',{path:'/tmp/library'}));
});
test('metadata route is accessible and uses the shared operation lifecycle',async()=>{
 const html=await readFile(new URL('../renderer/index.html',import.meta.url),'utf8');
 const app=await readFile(new URL('../renderer/app.ts',import.meta.url),'utf8');
 assert.match(html,/data-route="metadata"/);assert.match(html,/id="page-metadata"/);assert.match(html,/id="metadata-report-container"/);
 assert.match(app,/perform\('metadata'/);assert.match(app,/renderMetadataPanel/);assert.match(app,/route === 'metadata'/);
});
