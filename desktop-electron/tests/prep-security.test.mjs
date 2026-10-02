import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {validateRequest}=require('../.out/main/security.js');
const start='a'.repeat(64),end='b'.repeat(64),excluded='c'.repeat(64);
const planId='12345678-1234-1234-1234-123456789abc';
test('catalog and real variant selection expose only bounded plan identities',()=>{
 assert.deepEqual(validateRequest('getPrepCatalog',{}),{});
 assert.deepEqual(validateRequest('selectPrepVariant',{planId,variant:'safe'}),{planId,variant:'safe'});
 for(const params of [{planId:'../path',variant:'safe'},{planId,variant:'custom'},{planId,variant:['safe']},{planId,variant:'safe',path:'/tmp/file'}])assert.throws(()=>validateRequest('selectPrepVariant',params));
});
test('extended Prep accepts bounded domain intent using opaque track IDs',()=>{
 const params={targetTrackCount:20,name:'Session',strategy:'warmup',targetMinutes:30,slotRole:'warmup',genreFocus:'House',startTrackId:start,endTrackId:end,requiredTrackIds:[start],excludedTrackIds:[excluded]};
 assert.deepEqual(validateRequest('generatePrep',params),params);
});
test('extended Prep rejects unsafe numbers, identities, arrays and conflicting controls',()=>{
 const basic={targetTrackCount:20,name:'Session'};
 for(const extra of [{targetMinutes:NaN},{targetMinutes:Infinity},{targetMinutes:0},{targetMinutes:601},{strategy:'../exec'},{slotRole:'unknown'},{slotRole:['warmup']},{genreFocus:'x'.repeat(101)},{startTrackId:'/tmp/music.flac'},{endTrackId:'z'.repeat(64)},{requiredTrackIds:'all'},{requiredTrackIds:[start,start]},{excludedTrackIds:Array(101).fill(start)},{requiredTrackIds:[start],excludedTrackIds:[start]},{startTrackId:start,excludedTrackIds:[start]},{endTrackId:end,excludedTrackIds:[end]},{startTrackId:start,endTrackId:start},{targetTrackCount:2,startTrackId:start,endTrackId:end,requiredTrackIds:[excluded]}])assert.throws(()=>validateRequest('generatePrep',{...basic,...extra}));
});
