import assert from 'node:assert/strict';
import test from 'node:test';
import {EventEmitter} from 'node:events';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {CoreSupervisor,MAX_CORE_RESTARTS,RESTART_DELAYS_MS}=require('../.out/main/core-supervisor.js');
const wait=(ms)=>new Promise((resolve)=>setTimeout(resolve,ms));
class FakeCore extends EventEmitter {closed=false;}
const fixture=(options={})=>{
  const created=[],events=[];
  const supervisor=new CoreSupervisor({
    create:()=>{const core=new FakeCore();created.push(core);return core;},
    delays:[20,40],
    stabilityMs:0,
    onStarted:(_core,attempt)=>events.push(['started',attempt]),
    onStopped:(message)=>events.push(['stopped',message]),
    onRestart:(attempt,delay)=>events.push(['restart',attempt,delay]),
    onExhausted:(restarts,message)=>events.push(['exhausted',restarts,message]),
    ...options,
  });
  return {supervisor,created,events};
};
test('the restart budget is bounded and the retry cap keeps the existing restart message',{timeout:15000},async()=>{
  assert.equal(MAX_CORE_RESTARTS,RESTART_DELAYS_MS.length);
  assert.deepEqual([...RESTART_DELAYS_MS],[1000,3000,9000]);
  const f=fixture();
  const first=f.supervisor.start();
  assert.equal(f.created.length,1);
  assert.equal(f.supervisor.core,first);
  first.emit('stopped','The audio core stopped. Restart the app to reconnect.');
  await wait(60);
  assert.equal(f.created.length,2,'a stopped core is restarted once the delay elapses');
  assert.equal(f.supervisor.core,f.created[1],'the supervisor exposes the live core');
  f.created[1].emit('stopped','The audio core stopped. Restart the app to reconnect.');
  await wait(80);
  assert.equal(f.created.length,3);
  f.created[2].emit('stopped','The audio core stopped. Restart the app to reconnect.');
  await wait(80);
  assert.equal(f.created.length,3,'retries are capped, never unbounded');
  assert.deepEqual(f.events.filter((event)=>event[0]==='exhausted'),[['exhausted',2,'The audio core stopped. Restart the app to reconnect.']]);
  assert.deepEqual(f.events.filter((event)=>event[0]==='restart'),[['restart',1,20],['restart',2,40]]);
  f.supervisor.shutdown();
});
test('a stale core cannot trigger a restart and shutdown stops supervising',{timeout:15000},async()=>{
  const f=fixture({delays:[20,40,60]});
  const first=f.supervisor.start();
  first.emit('stopped','boom');
  await wait(60);
  assert.equal(f.created.length,2);
  first.emit('stopped','late exit of the replaced core');
  await wait(60);
  assert.equal(f.created.length,2,'events from a replaced core are ignored');
  for(const label of ['first stop','second stop','third stop'])f.created[1].emit('stopped',label);
  await wait(80);
  assert.equal(f.created.length,3,'one stop schedules exactly one restart');
  assert.equal(f.supervisor.restartCount,2,'repeated stops of the same core consume one retry');
  f.supervisor.shutdown();
  f.created[2].emit('stopped','closing');
  await wait(60);
  assert.equal(f.created.length,3,'nothing is created after shutdown');
});
test('a core that stays up long enough restores the retry budget',{timeout:15000},async()=>{
  const f=fixture({delays:[10],stabilityMs:30});
  f.supervisor.start().emit('stopped','boom');
  await wait(90);
  assert.equal(f.created.length,2,'the first retry is used');
  f.created[1].emit('stopped','boom again');
  await wait(60);
  assert.equal(f.created.length,3,'a stable core restores the budget');
  f.supervisor.shutdown();
});
