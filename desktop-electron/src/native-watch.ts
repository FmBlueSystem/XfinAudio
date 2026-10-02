import path from 'node:path';
import {Worker} from 'node:worker_threads';
import type {WatchFactory} from './library-watch';
/** Read-only native observation runs off the Electron main thread. */
export function createNativeWatchFactory(ignoreRoot:string):WatchFactory {
  return (roots,events)=>{
    const known=[...roots],failed=new Set<number>();let closed=false;let stopping:Promise<void>|null=null;
    const worker=new Worker(path.join(__dirname,'watch-worker.js'),{workerData:{roots:known,ignoreRoot},resourceLimits:{maxOldGenerationSizeMb:128}});
    const valid=(index:unknown):index is number=>Number.isInteger(index)&&Number(index)>=0&&Number(index)<known.length;
    worker.on('message',(value:unknown)=>{
      if(closed||!value||typeof value!=='object')return;
      const message=value as {type?:string;index?:unknown;indices?:unknown};
      if(message.type==='ready'&&Array.isArray(message.indices))events.ready(message.indices.filter(valid).map(index=>known[index]));
      else if(valid(message.index)&&message.type==='change')events.change(known[message.index]);
      else if(valid(message.index)&&message.type==='failed'){failed.add(message.index);events.failed(known[message.index]);}
    });
    worker.on('error',error=>{console.error('Native library observer failed',error);});
    worker.on('exit',()=>{if(!closed){closed=true;for(let i=0;i<known.length;i++)if(!failed.has(i))events.failed(known[i]);}});
    return {suppress:(paths,durationMs)=>{if(!closed)worker.postMessage({type:'suppress',paths,durationMs});},close:()=>{if(stopping)return stopping;closed=true;stopping=worker.terminate().then(()=>{});return stopping;}};
  };
}
