import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {validateRequest}=require('../.out/main/security.js');
const id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
test('Serato actions accept only scoped sources and opaque destination/preview/receipt tokens',()=>{
 for(const source of [{kind:'review',reviewId:id},{kind:'saved',playlistId:'1'}]){const p={source,destinationId:id,name:'Sesión 1'};assert.equal(validateRequest('previewSeratoExport',p),p);}
 assert.deepEqual(validateRequest('chooseSeratoDestination',{}),{});assert.deepEqual(validateRequest('commitSeratoExport',{previewId:id}),{previewId:id});assert.deepEqual(validateRequest('revealSeratoExport',{receiptId:id}),{receiptId:id});
});
test('Serato boundary rejects supplied paths, confirmation, readiness, bytes and ambiguous source',()=>{
 const valid={source:{kind:'review',reviewId:id},destinationId:id,name:'Set'};
 for(const p of [{...valid,path:'/tmp/live'},{...valid,confirmed:true},{...valid,readiness:'ready'},{...valid,bytes:'abc'},{...valid,source:{kind:'review',reviewId:id,path:'/tmp/x'}},{...valid,source:{kind:'saved',playlistId:1}},{...valid,source:{kind:'review',reviewId:id,playlistId:'1'}},{...valid,source:{kind:'path',path:'/tmp/a'}},{...valid,destinationId:'/tmp/_Serato_'},...['../Set','a/b','a\\b','A\nB','', 'x'.repeat(201)].map(name=>({...valid,name}))])assert.throws(()=>validateRequest('previewSeratoExport',p));
 for(const p of [{previewId:id,confirmed:true},{previewId:'/tmp/x'},{}])assert.throws(()=>validateRequest('commitSeratoExport',p));
 assert.throws(()=>validateRequest('chooseSeratoDestination',{root:'/tmp'}));assert.throws(()=>validateRequest('revealSeratoExport',{path:'/tmp/x'}));
});
