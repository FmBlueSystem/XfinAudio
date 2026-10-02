import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{validateRequest}=require('../.out/main/security.js');
const id='11111111-1111-4111-8111-111111111111',track='a'.repeat(64);
test('Live boundary accepts only review/session identities and bounded manual next choices',()=>{
 assert.deepEqual(validateRequest('openLive',{reviewId:id}),{reviewId:id});
 for(const method of ['getLiveStatus','clearLive'])assert.deepEqual(validateRequest(method,{sessionId:id}),{sessionId:id});
 assert.deepEqual(validateRequest('advanceLive',{sessionId:id,revision:0,trackId:track}),{sessionId:id,revision:0,trackId:track});
});
test('Live boundary rejects raw paths, recommendation payloads, scores and stale-shaped input',()=>{
 for(const params of [{reviewId:id,path:'/tmp/a'},{reviewId:id,recommendation:{}},{reviewId:'../a'},{}])assert.throws(()=>validateRequest('openLive',params));
 const good={sessionId:id,revision:1,trackId:track};
 for(const patch of [{revision:NaN},{revision:Infinity},{revision:-1},{revision:501},{revision:1.5},{revision:true},{trackId:'/tmp/a'},{trackId:'z'.repeat(64)},{sessionId:'bad'},{score:1},{ready:true}])assert.throws(()=>validateRequest('advanceLive',{...good,...patch}));
 for(const method of ['getLiveStatus','clearLive']){assert.throws(()=>validateRequest(method,{sessionId:id,path:'/tmp'}));assert.throws(()=>validateRequest(method,{}));}
});
