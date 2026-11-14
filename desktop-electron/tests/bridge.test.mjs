import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {CANCELLABLE_JOB_METHODS,PythonBridge,REQUEST_TIMEOUT_MS,requestDeadline}=require('../.out/main/bridge.js');
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
const silentCore=`process.stdin.resume();setInterval(()=>{},1000);`;
test('the deadline is per method and long cancellable jobs never carry one',()=>{
 assert.equal(REQUEST_TIMEOUT_MS,120000);
 assert.deepEqual([...CANCELLABLE_JOB_METHODS].sort(),['ai.run','library.rescan','library.scan','loudness.run','prep.generate','prep.select','profiles.complete']);
 for(const method of CANCELLABLE_JOB_METHODS)assert.equal(requestDeadline(method),null,`${method} owns its lifetime through cancellation`);
 for(const method of ['library.list','review.details','prep.generate.confirm','shutdown'])assert.equal(requestDeadline(method),REQUEST_TIMEOUT_MS,`${method} is bounded by the default deadline`);
 assert.equal(requestDeadline('library.list',0),null,'a disabled budget never kills a method');
});
test('a core that never answers hits its deadline, is killed and releases the slot',{timeout:15000},async()=>{
 const logged=[];
 const core=new PythonBridge(process.execPath,['-e',silentCore],process.env,{requestTimeoutMs:120,log:(line)=>logged.push(line)});
 try{
  const exited=once(core.child,'exit');
  const outcome=await Promise.race([core.request('review.details',{secret:'TOPSECRET'}).then(()=>'resolved',(error)=>error.code),new Promise((resolve)=>setTimeout(()=>resolve('no-deadline'),4000))]);
  assert.equal(outcome,'core_timeout','a hung core must reject with the deadline code');
  await exited;
  assert.equal(core.child.signalCode,'SIGKILL','the deadline must kill the hung process');
  await assert.rejects(core.request('review.details'),/Audio core unavailable/,'the released bridge accepts no new work');
  assert.ok(logged.some((line)=>/timeout/.test(line)&&line.includes('review.details')),'the timeout is recorded for support');
  assert.ok(logged.every((line)=>!line.includes('TOPSECRET')),'request parameters never reach the log');
 }finally{if(core.child.exitCode===null&&core.child.signalCode===null)core.child.kill('SIGKILL');await core.close();}
});
test('long cancellable jobs outlive the short request deadline',{timeout:20000},async()=>{
 const code=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const m=JSON.parse(b.slice(0,i));b=b.slice(i+1);if(m.method==='shutdown')process.exit(0);setTimeout(()=>{process.stdout.write(JSON.stringify({id:m.id,ok:true,result:{cancelled:false}})+'\\n');},120);}});`;
 const core=new PythonBridge(process.execPath,['-e',code],process.env,{requestTimeoutMs:40});
 try{
  for(const method of CANCELLABLE_JOB_METHODS)assert.deepEqual(await core.request(method),{cancelled:false},`${method} must not be killed by a short deadline`);
 }finally{await core.close();}
});
test('an error frame with a null id is logged and ignored while another malformed frame still stops the core',async()=>{
 const script=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const m=JSON.parse(b.slice(0,i));b=b.slice(i+1);if(m.method==='shutdown')process.exit(0);process.stdout.write(JSON.stringify({id:null,ok:false,error:{code:'invalid_params',message:'missing field secret'}})+'\\n');process.stdout.write(JSON.stringify({id:m.id,ok:true,result:{ok:true}})+'\\n');}});`;
 const logged=[];
 const core=new PythonBridge(process.execPath,['-e',script],process.env,{log:(line)=>logged.push(line)});
 try{
  assert.deepEqual(await core.request('library.list'),{ok:true},'an unsolicited error frame does not kill the core');
  assert.ok(logged.some((line)=>/null id/.test(line)&&line.includes('invalid_params')),'the ignored frame records its code');
  assert.ok(logged.every((line)=>!line.includes('missing field secret')),'the ignored frame never records its payload');
 }finally{await core.close();}
});
test('a normal round trip and every other malformed frame keep their current behaviour',{timeout:15000},async()=>{
 const healthy=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const m=JSON.parse(b.slice(0,i));b=b.slice(i+1);if(m.method==='shutdown')process.exit(0);process.stdout.write(JSON.stringify({id:m.id,ok:true,result:{echo:m.method}})+'\\n');}});`;
 const core=new PythonBridge(process.execPath,['-e',healthy],process.env);
 try{assert.deepEqual(await core.request('library.list'),{echo:'library.list'});assert.equal(core.child.exitCode,null,'a healthy round trip leaves the core running');}
 finally{await core.close();}
 const brokenScript=`let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){b=b.slice(i+1);process.stdout.write(JSON.stringify({id:null,ok:true})+'\\n');}});`;
 const broken=new PythonBridge(process.execPath,['-e',brokenScript],process.env);
 const exited=once(broken.child,'exit');
 await assert.rejects(broken.request('library.list'),/Invalid core frame/,'a frame that is not a null-id error stays fatal');
 await exited;
 await broken.close();
});
