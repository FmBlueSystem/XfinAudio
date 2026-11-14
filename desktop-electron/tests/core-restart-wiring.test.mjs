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
