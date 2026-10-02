import {parentPort,workerData} from 'node:worker_threads';
import {lstatSync,readdirSync,realpathSync,watch,type FSWatcher,type Stats} from 'node:fs';
import path from 'node:path';
const {roots,ignoreRoot}=workerData as {roots:string[];ignoreRoot:string};
const contains=(root:string,value:string)=>value===root||value.startsWith(root+path.sep);
const ignored=(value:string)=>contains(ignoreRoot,value);
const suppressions=new Map<string,number>();
parentPort?.on('message',(message:unknown)=>{
  if(!message||typeof message!=='object')return;
  const value=message as {type?:string;paths?:unknown;durationMs?:unknown};
  if(value.type!=='suppress'||!Array.isArray(value.paths)||value.paths.length>500||typeof value.durationMs!=='number'||!Number.isFinite(value.durationMs)||value.durationMs<0||value.durationMs>5000)return;
  const now=Date.now();for(const [filename,until] of suppressions)if(until<=now)suppressions.delete(filename);
  for(const filename of value.paths)if(typeof filename==='string'&&filename.length<=4096&&!filename.includes('\0')&&roots.some(root=>contains(root,filename)))suppressions.set(filename,now+value.durationMs);
  while(suppressions.size>500)suppressions.delete(suppressions.keys().next().value!);
});
const send=(type:string,index:number)=>parentPort?.postMessage({type,index});
const same=(a:Stats,b:Stats)=>a.dev===b.dev&&a.ino===b.ino;
interface RootWatch {root:string;index:number;identity:Stats;handles:Map<string,{watcher:FSWatcher;identity:Stats}>;timer:ReturnType<typeof setTimeout>|null;changed:Set<string>|null;failed:boolean;}
function directory(filename:string):Stats {
  const stat=lstatSync(filename);if(!stat.isDirectory()||stat.isSymbolicLink()||realpathSync(filename)!==filename)throw new Error('Unavailable canonical watch directory');return stat;
}
function tree(root:string):Map<string,Stats> {
  const result=new Map<string,Stats>(),pending=[root];let entries=0;
  while(pending.length){
    const current=pending.pop()!;if(ignored(current))continue;
    if(result.size>=4096)throw new Error('Directory watch budget exceeded');
    result.set(current,directory(current));
    for(const item of readdirSync(current,{withFileTypes:true})){
      if(++entries>50000)throw new Error('Tree watch budget exceeded');
      const filename=path.join(current,item.name);if(ignored(filename))continue;
      if(item.isSymbolicLink())throw new Error('Linked trees require manual rescan');
      if(item.isDirectory())pending.push(filename);
    }
  }
  return result;
}
function fail(state:RootWatch):void {
  if(state.failed)return;state.failed=true;
  if(state.timer)clearTimeout(state.timer);state.timer=null;
  for(const handle of state.handles.values())handle.watcher.close();state.handles.clear();send('failed',state.index);
}
function refresh(state:RootWatch):void {
  if(!same(directory(state.root),state.identity))throw new Error('Watch root changed');
  const directories=tree(state.root);
  for(const [filename,handle] of state.handles)if(!directories.has(filename)||!same(directories.get(filename)!,handle.identity)){handle.watcher.close();state.handles.delete(filename);}
  for(const [filename,identity] of directories){
    if(state.handles.has(filename))continue;
    const handle=watch(filename,{persistent:true},(_event,name)=>{
      if(state.failed)return;
      if(name!==null){const target=path.resolve(filename,String(name));if(!contains(state.root,target)){fail(state);return;}if(ignored(target))return;if(state.changed){state.changed.add(target);if(state.changed.size>256)state.changed=null;}}else state.changed=null;
      if(state.timer)return;
      state.timer=setTimeout(()=>{
        state.timer=null;if(state.failed)return;
        const changed=state.changed;state.changed=new Set();
        try{refresh(state);const now=Date.now();if(changed===null||[...changed].some(filename=>(suppressions.get(filename)??0)<=now))send('change',state.index);}catch{fail(state);send('change',state.index);}
      },75);
    });
    handle.on('error',()=>fail(state));state.handles.set(filename,{watcher:handle,identity});
    if(!same(directory(filename),identity))throw new Error('Watch directory changed');
  }
  if(!same(directory(state.root),state.identity))throw new Error('Watch root changed');
}
const active:number[]=[];
for(let index=0;index<roots.length;index++){
  const root=roots[index];let state:RootWatch|undefined;
  try{
    if(index>=64||!path.isAbsolute(root)||root.includes('\0')||root.length>4096||ignored(root))throw new Error('Watch root unavailable');
    state={root,index,identity:directory(root),handles:new Map(),timer:null,changed:new Set(),failed:false};refresh(state);active.push(index);
  }catch{if(state)fail(state);else send('failed',index);}
}
parentPort?.postMessage({type:'ready',indices:active});
