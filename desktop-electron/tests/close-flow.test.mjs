import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {CloseFlow}=require('../.out/main/close-flow.js');
test('cancelling dirty close preserves the core and permits another close attempt',async()=>{
 let consent=false,prompts=0,shutdown=0,finished=0;
 const flow=new CloseFlow(()=>true,async()=>{prompts++;return consent;},async()=>{shutdown++;},()=>{finished++;});
 await flow.request();assert.equal(prompts,1);assert.equal(shutdown,0);assert.equal(finished,0);assert.equal(flow.readyToQuit,false);assert.equal(flow.isClosing,false);
 consent=true;await flow.request();assert.equal(prompts,2);assert.equal(shutdown,1);assert.equal(finished,1);assert.equal(flow.readyToQuit,true);
});
test('repeated close waits for one confirmation and complete core drainage',async()=>{
 let confirm,drain,prompts=0,shutdown=0,finished=0;
 const flow=new CloseFlow(()=>true,()=>{prompts++;return new Promise(resolve=>{confirm=resolve;});},()=>{shutdown++;return new Promise(resolve=>{drain=resolve;});},()=>{finished++;});
 const first=flow.request(),again=flow.request();assert.equal(first,again);assert.equal(prompts,1);assert.equal(flow.readyToQuit,false);
 confirm(true);await new Promise(resolve=>setImmediate(resolve));assert.equal(shutdown,1);assert.equal(flow.isClosing,true);assert.equal(flow.readyToQuit,false);assert.equal(finished,0);
 assert.equal(flow.request(),first);drain();await first;assert.equal(finished,1);assert.equal(flow.readyToQuit,true);
});
test('clean close skips confirmation and failed confirmation never discards a draft',async()=>{
 let prompts=0,finish=0;
 const clean=new CloseFlow(()=>false,async()=>{prompts++;return true;},async()=>{},()=>{finish++;});await clean.request();assert.equal(prompts,0);assert.equal(finish,1);
 const failed=new CloseFlow(()=>true,async()=>{throw new Error('Dialog unavailable');},async()=>{throw new Error('Must not shutdown');},()=>{throw new Error('Must not quit');});await failed.request();assert.equal(failed.readyToQuit,false);
});
