import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{LibraryWatch}=require('../.out/main/library-watch.js');
const deferred=()=>{let resolve;return {promise:new Promise(r=>{resolve=r;}),resolve:()=>resolve()};};
function fixture({failure=false}={}) {
 const drivers=[],timers=[],published=[];
 const watch=new LibraryWatch((roots,events)=>{if(failure)throw new Error('Unavailable');const driver={roots,events,closed:0,close:async()=>{driver.closed++;}};drivers.push(driver);return driver;},status=>published.push(status),{set:callback=>{const t={callback,cancelled:false};timers.push(t);return t;},clear:t=>{t.cancelled=true;}});
 return {watch,drivers,timers,published,ready:()=>drivers.at(-1).events.ready(drivers.at(-1).roots),flush:()=>timers.at(-1)?.callback()};
}
test('startup is restored; successful explicit scan publishes clean independently of watcher availability',async()=>{
 const f=fixture();await f.watch.configure(['/music'],true);assert.equal(f.watch.status.changeState,'restored');f.ready();assert.equal(f.watch.status.watchState,'active');await f.watch.beginScan();assert.equal(f.watch.status.watchState,'paused');await f.watch.finishScan(['/music'],['/music']);f.ready();assert.equal(f.watch.status.changeState,'clean');await f.watch.close();
 const g=fixture({failure:true});await g.watch.configure(['/music'],true);await g.watch.beginScan();await g.watch.finishScan(['/music'],['/music']);assert.equal(g.watch.status.changeState,'clean');assert.equal(g.watch.status.watchState,'unavailable');assert.equal(g.watch.status.watchedCount,0);await g.watch.close();
});
test('debounce coalesces raw events and never leaks private root paths',async()=>{
 const f=fixture();await f.watch.configure(['/private/music'],true);f.ready();await f.watch.beginScan();await f.watch.finishScan(['/private/music'],['/private/music']);f.ready();const source=f.drivers.at(-1),before=f.published.length;
 source.events.change('/private/music');source.events.change('/private/music');assert.equal(f.published.length,before);assert.equal(f.timers[0].cancelled,true);f.flush();assert.equal(f.watch.status.changeState,'changed');assert.equal(f.published.length,before+1);assert.equal(JSON.stringify(f.watch.status).includes('/private'),false);await f.watch.close();
});
test('queued old events and timer callbacks cannot revive after pause, root replacement or disposal',async()=>{
 const f=fixture();await f.watch.configure(['/old'],true);f.ready();const old=f.drivers[0];old.events.change('/old');const queued=f.timers[0].callback;await f.watch.beginScan();await f.watch.finishScan(['/new'],['/new']);f.ready();const before=f.published.length;old.events.change('/old');old.events.failed('/old');old.events.ready(['/old']);queued();assert.equal(f.published.length,before);assert.equal(f.watch.status.changeState,'clean');assert.equal(f.watch.status.rootCount,1);
 const current=f.drivers.at(-1);current.events.change('/new');const later=f.timers.at(-1).callback;await f.watch.close();const stopped=f.published.length;current.events.change('/new');later();assert.equal(f.published.length,stopped);
});
test('cancelled scan preserves detected changes and never publishes fully clean unknown data',async()=>{
 const f=fixture();await f.watch.configure(['/music'],true);f.ready();f.drivers.at(-1).events.change('/music');await f.watch.beginScan();await f.watch.finishScan(['/music'],null);f.ready();assert.equal(f.watch.status.changeState,'changed');await f.watch.close();
 const g=fixture();await g.watch.configure(['/music'],true);g.ready();await g.watch.beginScan();await g.watch.finishScan(['/music'],null);g.ready();assert.equal(g.watch.status.changeState,'restored');await g.watch.close();
});
test('disabled watching ignores late callbacks and re-enable starts fresh unverified generation',async()=>{
 const f=fixture();await f.watch.configure(['/music'],true);f.ready();const old=f.drivers.at(-1);await f.watch.configure(['/music'],false);assert.equal(f.watch.status.watchState,'disabled');old.events.change('/music');assert.equal(f.timers.length,0);await f.watch.configure(['/music'],true);f.ready();assert.equal(f.drivers.length,2);assert.equal(f.watch.status.changeState,'restored');await f.watch.close();
});
test('root failures preserve clean scan publication while marking partial observation unavailable',async()=>{
 const f=fixture();await f.watch.configure(['/a','/b'],true);f.ready();await f.watch.beginScan();await f.watch.finishScan(['/a','/b'],['/a','/b']);f.ready();f.drivers.at(-1).events.failed('/a');assert.equal(f.watch.status.changeState,'clean');assert.equal(f.watch.status.watchState,'unavailable');assert.equal(f.watch.status.watchedCount,1);f.drivers.at(-1).events.change('/b');f.flush();assert.equal(f.watch.status.changeState,'changed');await f.watch.close();
});
test('shutdown retains and drains a slow retiring driver; superseded reconfiguration cannot restart it',async()=>{
 const wait=deferred(),f=fixture();await f.watch.configure(['/old'],true);f.drivers[0].close=()=>wait.promise;const first=f.watch.configure(['/middle'],true);const second=f.watch.configure(['/new'],true);const closing=f.watch.close();let done=false;closing.then(()=>{done=true;});await new Promise(r=>setImmediate(r));assert.equal(done,false);assert.equal(f.drivers.length,1);wait.resolve();await Promise.all([first,second,closing]);assert.equal(done,true);assert.equal(f.drivers.length,1);
});
test('explicit observer replacement marks its observation gap unverified until another scan',async()=>{const f=fixture();await f.watch.configure(['/music'],true);f.ready();await f.watch.beginScan();await f.watch.finishScan(['/music'],['/music']);f.ready();assert.equal(f.watch.status.changeState,'clean');await f.watch.configure(['/music'],true);f.ready();assert.equal(f.watch.status.changeState,'restored');await f.watch.close();});
