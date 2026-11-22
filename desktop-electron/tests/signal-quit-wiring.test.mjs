import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
test('small fixes S4: SIGTERM and SIGINT run the orderly close without the unsaved-changes dialog',async()=>{
  const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8');
  for(const signal of ['SIGTERM','SIGINT'])assert.match(main,new RegExp(`process\\.on\\('${signal}'`),`${signal} has a handler`);
  assert.match(main,/const quitOnSignal=\(signal:NodeJS\.Signals\):void=>\{[\s\S]{0,200}closeFlow\.request\(true\)/,'a signal forces the orderly close');
});
