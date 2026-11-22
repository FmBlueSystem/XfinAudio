import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {validateRequest}=require('../.out/main/security.js');
const id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
test('Serato actions accept only scoped sources and opaque destination/preview/receipt tokens',()=>{
 for(const source of [{kind:'review',reviewId:id},{kind:'saved',playlistId:'1'}]){const p={source,destinationId:id,name:'Sesión 1'};assert.equal(validateRequest('previewSeratoExport',p),p);}
 assert.deepEqual(validateRequest('chooseSeratoDestination',{}),{});assert.deepEqual(validateRequest('commitSeratoExport',{previewId:id}),{previewId:id});assert.deepEqual(validateRequest('revealSeratoExport',{receiptId:id}),{receiptId:id});
});
test('Serato boundary rejects supplied paths, confirmation, readiness, bytes and ambiguous source',()=>{
 const valid={source:{kind:'review',reviewId:id},destinationId:id,name:'Set'};
 for(const p of [{...valid,path:'/tmp/live'},{...valid,confirmed:true},{...valid,readiness:'ready'},{...valid,bytes:'abc'},{...valid,source:{kind:'review',reviewId:id,path:'/tmp/x'}},{...valid,source:{kind:'saved',playlistId:1}},{...valid,source:{kind:'review',reviewId:id,playlistId:'1'}},{...valid,source:{kind:'path',path:'/tmp/a'}},{...valid,destinationId:'/tmp/_Serato_'},...['../Set','a/b','a\\b','A\nB',' ', 'x'.repeat(201)].map(name=>({...valid,name}))])assert.throws(()=>validateRequest('previewSeratoExport',p));
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
 for(const name of ['  ','.','..','../Set','a/b','a\\b','A\nB','x'.repeat(201)])assert.throws(()=>validateRequest('quickSeratoExport',{...valid,name}));
 for(const params of [{},{name:'Set'},{source:valid.source,name:'Set',seratoRoot:'/tmp'}])assert.throws(()=>validateRequest('quickSeratoExport',params));
});
test('a refused export source names its code so the screen can explain it in Spanish (S2)',()=>{
 const saved={kind:'saved',playlistId:1};
 assert.throws(()=>validateRequest('quickSeratoExport',{source:saved,name:'Set'}),/\[invalid_source\] Invalid export source/);
 assert.throws(()=>validateRequest('previewSeratoExport',{source:saved,destinationId:id,name:'Set'}),/\[invalid_source\] Invalid export source/);
 for(const source of [{kind:'review',reviewId:id,path:'/tmp/x'},{kind:'path',path:'/tmp/a'},{kind:'review'}])assert.throws(()=>validateRequest('quickSeratoExport',{source,name:'Set'}),/\[invalid_source\]/);
 assert.throws(()=>validateRequest('quickSeratoExport',{name:'Set'}),/\[invalid_source\]/);
});
test('a generated set may leave the crate name to the core and nothing else may',()=>{
 const review={kind:'review',reviewId:id};
 assert.deepEqual(validateRequest('previewSeratoExport',{source:review,destinationId:id}),{source:review,destinationId:id});
 assert.deepEqual(validateRequest('previewSeratoExport',{source:review,destinationId:id,name:''}),{source:review,destinationId:id,name:''});
 assert.deepEqual(validateRequest('quickSeratoExport',{source:review}),{source:review});
 assert.deepEqual(validateRequest('quickSeratoExport',{source:review,name:''}),{source:review,name:''});
 const saved={kind:'saved',playlistId:'1'};
 const metadata={kind:'metadata',status:'incomplete',missingField:'bpm',trackIds:['a'.repeat(64)]};
 for(const source of [saved,metadata]){
  assert.throws(()=>validateRequest('previewSeratoExport',{source,destinationId:id}),/Invalid crate name/);
  assert.throws(()=>validateRequest('previewSeratoExport',{source,destinationId:id,name:''}),/Invalid crate name/);
  assert.throws(()=>validateRequest('quickSeratoExport',{source}),/Invalid crate name/);
  assert.throws(()=>validateRequest('quickSeratoExport',{source,name:''}),/Invalid crate name/);
 }
});
test('an automatic crate name never relaxes the generated-set boundary',()=>{
 const review={kind:'review',reviewId:id};
 for(const extra of [{path:'/tmp/live'},{confirmed:true},{readiness:'ready'},{bytes:'abc'},{seratoRoot:'/Volumes/dd/_Serato_'}])assert.throws(()=>validateRequest('previewSeratoExport',{source:review,destinationId:id,...extra}));
 assert.throws(()=>validateRequest('previewSeratoExport',{source:review}),/Invalid Serato destination/);
 assert.throws(()=>validateRequest('previewSeratoExport',{source:review,destinationId:'/tmp/_Serato_'}));
 for(const extra of [{path:'/tmp/live'},{confirmed:true},{destinationId:id},{receiptId:id}])assert.throws(()=>validateRequest('quickSeratoExport',{source:review,...extra}));
 for(const name of ['  ','.','..','../Set','a/b','a\\b','A\nB','x'.repeat(201)])assert.throws(()=>validateRequest('previewSeratoExport',{source:review,destinationId:id,name}));
 for(const name of ['  ','.','..','../Set','a/b','a\\b','A\nB','x'.repeat(201)])assert.throws(()=>validateRequest('quickSeratoExport',{source:review,name}));
 for(const source of [{kind:'review',reviewId:id,path:'/tmp/x'},{kind:'path',path:'/tmp/a'},{kind:'review'}])assert.throws(()=>validateRequest('quickSeratoExport',{source}));
});

test('the preview accepts a tramo size as a whole number of 2 to 50 tracks and nothing else (S1)',()=>{
 const valid={source:{kind:'review',reviewId:id},destinationId:id,name:'Set'};
 for(const segmentSize of [2,3,5,50]){const p={...valid,segmentSize};assert.deepEqual(validateRequest('previewSeratoExport',p),p);}
 assert.deepEqual(validateRequest('previewSeratoExport',valid),valid,'no split sends no segment size at all');
 for(const segmentSize of [1,51,0,-5,2.5,'5',true,[5],{tracks:5},null,Number.NaN,Number.MAX_SAFE_INTEGER])assert.throws(()=>validateRequest('previewSeratoExport',{...valid,segmentSize}),/Segment size/);
});
test('a one-click quick export accepts no tramo size, so it keeps today\'s single crate (S1)',()=>{
 const p={source:{kind:'review',reviewId:id},name:'Set'};
 assert.deepEqual(validateRequest('quickSeratoExport',p),p);
 assert.throws(()=>validateRequest('quickSeratoExport',{...p,segmentSize:5}));
});

test('the typed-name cap counts the XfinAudio parent crate the core writes, so an over-long file is refused at the boundary (S1)',()=>{
 const review={kind:'review',reviewId:id},saved={kind:'saved',playlistId:'1'};
 // 'ñ' is two UTF-8 bytes, so the character cap leaves the 240-byte file cap in charge.
 const entries=[{method:'previewSeratoExport',params:{source:review,destinationId:id}},{method:'quickSeratoExport',params:{source:saved}}];
 for(const {method,params} of entries){
  // Nested as `XfinAudio%%<name>.crate`: 11 + 222 + 6 = 239 bytes fit, one more character does not.
  assert.deepEqual(validateRequest(method,{...params,name:'ñ'.repeat(111)}),{...params,name:'ñ'.repeat(111)});
  assert.throws(()=>validateRequest(method,{...params,name:'ñ'.repeat(112)}),/Invalid crate name/);
  // The prefix is really counted: this name fits a bare `<name>.crate` but not the file the core writes.
  assert.equal(Buffer.byteLength('ñ'.repeat(115)+'.crate','utf8')<=240,true,'it used to fit without the parent crate');
  assert.throws(()=>validateRequest(method,{...params,name:'ñ'.repeat(115)}),/Invalid crate name/);
  // A name that already carries the prefix is not doubled, so it keeps the whole budget.
  const nested=`XfinAudio%%${'ñ'.repeat(111)}`;
  assert.deepEqual(validateRequest(method,{...params,name:nested}),{...params,name:nested});
  assert.throws(()=>validateRequest(method,{...params,name:`${nested}ñ`}),/Invalid crate name/);
 }
});
