import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
const read=(file)=>readFile(new URL(`../src/${file}`,import.meta.url),'utf8');
const block=(source,start,length=900)=>{const from=source.indexOf(start);assert.notEqual(from,-1,`${start} must exist`);return source.slice(from,from+length);};
test('main supervises the core with bounded retries and re-arms what waits on it',async()=>{
  const main=await read('main.ts');
  assert.match(main,/import \{CoreSupervisor\} from '\.\/core-supervisor';/,'the bounded restart supervisor owns the core lifecycle');
  assert.match(main,/new CoreSupervisor<PythonBridge>\(\{/,'main builds the supervisor around the bridge');
  assert.match(main,/onStarted:[\s\S]{0,300}libraryHost\.initialize\(\)/,'a restarted core re-arms the library watch that waited on the old one');
  assert.match(main,/onExhausted:/,'the retry cap has a reporting path');
  const stopped=block(main,'function onCoreStopped');
  assert.match(stopped,/current=null/,'a stopped core releases the single-job slot instead of leaving the host busy forever');
  assert.match(stopped,/libraryHost\.close\(\)/,'a stopped core stops the watcher it owned');
  assert.match(stopped,/phase:'error'/,'the renderer still receives the restart-the-app message');
  const shutdown=block(main,'async()=>{supervisor?.shutdown();',400);
  assert.match(shutdown,/core\?\.close\(\)/,'shutdown closes the live core after supervision stops');
});
test('main writes core stderr, stops, rests, timeouts and uncaught errors to the rotating log',async()=>{
  const main=await read('main.ts');
  assert.match(main,/import \{RotatingLog,revealLogFolder\} from '\.\/log-file';/,'the support log lives in its own module');
  assert.match(main,/new RotatingLog\(path\.join\(dataDir,'logs'\)\)/,'the log file lives under the app data directory');
  assert.match(main,/new PythonBridge\(executable,args,env,\{log:/,'core stderr reaches the log file');
  assert.match(main,/onStopped:message=>log\.write/,'core stops are recorded');
  assert.match(main,/onRestart:\(attempt,delayMs\)=>log\.write/,'scheduled restarts are recorded');
  assert.match(main,/process\.on\('uncaughtException'/,'uncaught main-process errors are recorded');
  assert.match(main,/process\.on\('unhandledRejection'/,'unhandled main-process rejections are recorded');
  const describe=block(main,'const describeFailure');
  assert.match(describe,/instanceof Error\?/,'only an error name and message are recorded, never a payload');
  assert.doesNotMatch(describe,/JSON\.stringify/,'a rejection value is never serialized into the log');
});
test('the show-logs action is allowlisted, dispatched and exposed like the backups reveal',async()=>{
  const [main,security,preload]=await Promise.all([read('main.ts'),read('security.ts'),read('preload.ts')]);
  assert.match(main,/case 'revealLogs':return revealLogFolder\(dataDir,filename=>shell\.showItemInFolder\(filename\)\);/,'the action reveals the fixed app-owned folder');
  assert.match(security,/revealLogs:\[\]/,'the allowlist admits the action with no parameters');
  assert.match(preload,/revealLogs:\(\)=>invoke\('revealLogs'\),/,'the renderer reaches it through the sandboxed bridge');
});
test('a stopped or replaced core makes main forget every Serato id it holds',async()=>{
  const main=await read('main.ts');
  const stopped=block(main,'function onCoreStopped');
  assert.match(stopped,/serato\.reset\(\)/,'a stopped core voids its destination, preview and receipt ids');
  const wire=block(main,'const wireCore=',400);
  assert.match(wire,/core=next;/,'every restarted core is wired in one place');
  assert.match(wire,/serato\.reset\(\)/,'a restarted core starts with no Serato ids from the previous one');
});
test('the renderer reacts to a core stop by forgetting the Serato ids it was holding',async()=>{
  const app=await readFile(new URL('../renderer/app.ts',import.meta.url),'utf8');
  const failure=app.slice(app.indexOf('if (isCoreFailure(event))'));
  assert.match(failure.slice(0,600),/serato\.forgetCore\(\)/,'the page drops its destination so detection runs again');
  assert.match(failure.slice(0,600),/seratoQuick\.forgetCore\(\)/,'the quick notice never keeps a receipt from the dead core');
});
test('a restarted core is announced once it is ready so the window leaves the stopped state',async()=>{
  const main=await read('main.ts');
  const started=block(main,'onStarted:',700);
  assert.match(started,/attempt>0/,'the first core is not a restart');
  assert.match(started,/libraryHost\.initialize\(\)/,'the watcher is re-armed on the fresh core');
  assert.match(started,/notifyCoreRestarted/,'the announcement happens once the fresh core is armed');
  const notify=block(main,'function notifyCoreRestarted',400);
  assert.match(notify,/window\.isDestroyed\(\)/,'a closed window is never told anything');
  assert.match(notify,/xfin:progress/,'the recovery travels on the existing, fail-closed progress channel');
  assert.match(notify,/phase:'restarted'/,'the renderer learns that a supervised restart succeeded');
  assert.match(notify,/operation:'core'/,'the same core operation carries the stop and the recovery');
});
test('restart exhaustion keeps the existing restart message instead of a recovery signal',async()=>{
  const main=await read('main.ts');
  const exhausted=block(main,'onExhausted:',400);
  assert.match(exhausted,/log\.write/,'the limit is recorded');
  assert.match(exhausted,/phase:'error'/,'the renderer keeps the restart-the-app message');
  assert.doesNotMatch(exhausted,/restarted/,'an exhausted supervisor never claims a healthy core');
});
test('the renderer leaves the stopped state only on the restart signal',async()=>{
  const app=await readFile(new URL('../renderer/app.ts',import.meta.url),'utf8');
  const restored=block(app,'if (isCoreRestored(event))',400);
  assert.match(restored,/coreAvailable = true/,'a supervised restart returns the app to its normal state');
  assert.match(restored,/restartRequired/,'a pending manual restart is never cleared by an automatic one');
  const failure=block(app,'if (isCoreFailure(event))',200);
  assert.doesNotMatch(failure,/coreAvailable = true/,'a stop never reports the core as available');
});
