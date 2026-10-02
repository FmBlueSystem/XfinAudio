import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {PythonBridge}=require('../.out/main/bridge.js');
test('bridge preserves split UTF8 and correlates responses, progress, shutdown',async()=>{
 const code=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const m=JSON.parse(b.slice(0,i));b=b.slice(i+1);if(m.method==='shutdown'){process.stdout.write(JSON.stringify({id:m.id,ok:true,result:{shutdown:true}})+'\\n');process.exit(0);}process.stdout.write(JSON.stringify({event:'progress',jobId:m.id,data:{phase:'scan'}})+'\\n');const out=Buffer.from(JSON.stringify({id:m.id,ok:true,result:{title:'Música'}})+'\\n');const n=out.indexOf(Buffer.from('ú'))+1;process.stdout.write(out.subarray(0,n));setTimeout(()=>process.stdout.write(out.subarray(n)),10);}});`;
 const core=new PythonBridge(process.execPath,['-e',code],process.env);let progress=0;core.on('progress',()=>progress++);
 assert.deepEqual(await core.request('test'),{title:'Música'});assert.equal(progress,1);await core.close();
});
test('malformed response rejects outstanding work and close drains process',async()=>{
 const core=new PythonBridge(process.execPath,['-e',`process.stdin.on('data',()=>process.stdout.write('not JSON\\n'))`],process.env);
 await assert.rejects(core.request('test'));await core.close();
});
test('shutdown waits for actual process exit even when the request queue is full',{timeout:10000},async()=>{
 const core=new PythonBridge(process.execPath,['-e',`process.on('SIGTERM',()=>{});process.stdin.resume();process.stdout.write('\\n');setInterval(()=>{},1000);`],process.env);
 await new Promise(resolve=>core.child.stdout.once('data',resolve));
 const pending=Array.from({length:16},()=>core.request('test').catch(()=>undefined));
 await core.close();
 assert.equal(core.child.signalCode,'SIGKILL');await Promise.all(pending);
});
test('closed core input is a handled transport failure',{timeout:10000},async()=>{
 const core=new PythonBridge(process.execPath,['-e',`require('node:fs').closeSync(0);process.stdout.write('\\n');setInterval(()=>{},1000);`],process.env);
 await new Promise(resolve=>core.child.stdout.once('data',resolve));
 await assert.rejects(core.request('test'));await core.close();
});
test('safe backend error codes survive the bridge for stale-draft recovery',async()=>{
 const script=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const m=JSON.parse(b.slice(0,i));b=b.slice(i+1);if(m.method==='shutdown'){process.stdout.write(JSON.stringify({id:m.id,ok:true,result:{shutdown:true}})+'\\n');process.exit(0);}process.stdout.write(JSON.stringify({id:m.id,ok:false,error:{code:'stale_edit',message:'Saved playlist changed'}})+'\\n');}});`;
 const core=new PythonBridge(process.execPath,['-e',script],process.env);
 try{await assert.rejects(core.request('test'),error=>error.code==='stale_edit'&&error.message==='[stale_edit] Saved playlist changed');}
 finally{await core.close();}
});
