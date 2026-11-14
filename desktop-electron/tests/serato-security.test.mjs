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
test('automatic destination detection accepts no parameters at all',()=>{
 assert.deepEqual(validateRequest('detectSeratoDestination',{}),{});
 assert.deepEqual(validateRequest('detectSeratoDestination',undefined),{});
 for(const p of [{root:'/tmp'},{path:'/Volumes/dd/_Serato_'},{seratoRoot:'/Volumes/dd/_Serato_'}])assert.throws(()=>validateRequest('detectSeratoDestination',p));
});
test('quick export accepts only the same scoped source and crate name the preview accepts',()=>{
 for(const source of [{kind:'review',reviewId:id},{kind:'saved',playlistId:'1'}]){const p={source,name:'Sesión 1'};assert.deepEqual(validateRequest('quickSeratoExport',p),p);}
 const metadata={kind:'metadata',status:'incomplete',missingField:'bpm',trackIds:['a'.repeat(64)]};
 const p={source:metadata,name:'Reparar BPM'};assert.deepEqual(validateRequest('quickSeratoExport',p),p);
 assert.deepEqual(validateRequest('quickSeratoExport',{source:{kind:'review',reviewId:id},name:'Set'}),{source:{kind:'review',reviewId:id},name:'Set'});
});
test('quick export rejects paths, confirmation, destinations and unknown keys exactly like the preview',()=>{
 const valid={source:{kind:'review',reviewId:id},name:'Set'};
 for(const extra of [{path:'/tmp/live'},{confirmed:true},{destinationId:id},{receiptId:id},{readiness:'ready'},{bytes:'abc'},{previewId:id}])assert.throws(()=>validateRequest('quickSeratoExport',{...valid,...extra}));
 for(const source of [{kind:'review',reviewId:id,path:'/tmp/x'},{kind:'saved',playlistId:1},{kind:'saved',playlistId:'../x'},{kind:'path',path:'/tmp/a'},{kind:'review'},{kind:['review']}])assert.throws(()=>validateRequest('quickSeratoExport',{...valid,source}));
 for(const name of ['','  ','.','..','../Set','a/b','a\\b','A\nB','x'.repeat(201)])assert.throws(()=>validateRequest('quickSeratoExport',{...valid,name}));
 for(const params of [{},{source:valid.source},{name:'Set'},{source:valid.source,name:'Set',seratoRoot:'/tmp'}])assert.throws(()=>validateRequest('quickSeratoExport',params));
});
