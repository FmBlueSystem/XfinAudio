import path from 'node:path';
export interface LibraryStatus {
  revision:number;changeState:'restored'|'clean'|'changed';watchState:'starting'|'active'|'disabled'|'unavailable'|'paused';rootCount:number;watchedCount:number;
}
export interface WatchEvents {change(root:string):void;ready(roots:string[]):void;failed(root:string):void;}
export interface WatchDriver {close():Promise<void>;suppress?(paths:string[],durationMs:number):void;}
export type WatchFactory=(roots:string[],events:WatchEvents)=>WatchDriver;
interface Timers {set(callback:()=>void,delay:number):unknown;clear(handle:unknown):void;}
const nativeTimers:Timers={set:(callback,delay)=>setTimeout(callback,delay),clear:handle=>clearTimeout(handle as ReturnType<typeof setTimeout>)};
/** One owner for generations, debounce and retiring read-only watch drivers. */
export class LibraryWatch {
  private roots:string[]=[];
  private dirty=new Set<string>();
  private unverified=new Set<string>();
  private pending=new Set<string>();
  private watched=new Set<string>();
  private generation=0;
  private revision=0;
  private enabled=false;
  private paused=false;
  private closed=false;
  private ready=false;
  private driver:WatchDriver|null=null;
  private retiring=new Set<Promise<void>>();
  private timer:unknown|null=null;
  constructor(private readonly factory:WatchFactory,private readonly publish:(status:LibraryStatus)=>void,private readonly timers:Timers=nativeTimers) {}
  get status():LibraryStatus {
    const watchState=this.closed||!this.enabled||!this.roots.length?'disabled':this.paused?'paused':!this.ready?'starting':this.watched.size===this.roots.length?'active':'unavailable';
    return {revision:this.revision,changeState:this.dirty.size?'changed':this.unverified.size?'restored':'clean',watchState,rootCount:this.roots.length,watchedCount:this.watched.size};
  }
  private emit():void {this.revision++;this.publish(this.status);}
  private setRoots(roots:string[]):void {
    if(roots.some(root=>typeof root!=='string'||!path.isAbsolute(root)||root.length>4096||root.includes('\0')))throw new Error('Invalid authorized watch roots');
    const previous=new Set(this.roots);this.roots=[...new Set(roots)];const known=new Set(this.roots);
    this.dirty=new Set([...this.dirty].filter(root=>known.has(root)));
    this.unverified=new Set([...this.unverified].filter(root=>known.has(root)));
    for(const root of this.roots)if(!previous.has(root))this.unverified.add(root);
  }
  private async retire():Promise<void> {
    this.generation++;
    if(this.timer!==null)this.timers.clear(this.timer);this.timer=null;
    for(const root of this.pending)this.dirty.add(root);this.pending.clear();this.watched.clear();this.ready=false;
    const driver=this.driver;this.driver=null;
    if(driver) {
      const closing=Promise.resolve().then(()=>driver.close()).catch(error=>{console.error('Library watcher close failed',error);});
      this.retiring.add(closing);void closing.then(()=>this.retiring.delete(closing));
    }
    await Promise.all(this.retiring);
  }
  private start(generation:number):void {
    if(this.closed||this.paused||!this.enabled||generation!==this.generation||!this.roots.length)return;
    const known=new Set(this.roots);
    const current=()=>!this.closed&&!this.paused&&this.enabled&&generation===this.generation;
    const events:WatchEvents={
      change:root=>{
        if(!current()||!known.has(root))return;
        this.pending.add(root);
        if(this.timer!==null)this.timers.clear(this.timer);
        this.timer=this.timers.set(()=>{
          if(!current())return;
          this.timer=null;
          for(const value of this.pending)this.dirty.add(value);
          this.pending.clear();this.emit();
        },350);
      },
      ready:roots=>{if(current()){this.watched=new Set(roots.filter(root=>known.has(root)));this.ready=true;this.emit();}},
      failed:root=>{if(current()&&known.has(root)){this.watched.delete(root);this.ready=true;this.emit();}},
    };
    try{this.driver=this.factory([...this.roots],events);}catch(error){console.error('Library watch unavailable',error);this.ready=true;this.watched.clear();this.emit();}
  }
  async configure(roots:string[],enabled:boolean):Promise<void> {
    if(this.closed)return;
    this.enabled=enabled;this.paused=false;
    this.setRoots(roots);
    if(enabled)for(const root of this.roots)this.unverified.add(root);
    const stopping=this.retire(),generation=this.generation;this.emit();await stopping;this.start(generation);
  }
  async beginScan():Promise<void> {
    if(this.closed)return;
    this.paused=true;const stopping=this.retire();this.emit();await stopping;
  }
  async finishScan(roots:string[],completedRoots:string[]|null):Promise<void> {
    if(this.closed)return;
    this.setRoots(roots);
    if(completedRoots===null)for(const root of this.roots)this.unverified.add(root);
    else for(const root of completedRoots){this.dirty.delete(root);this.unverified.delete(root);}
    this.paused=false;const stopping=this.retire(),generation=this.generation;this.emit();await stopping;this.start(generation);
  }
  suppressPaths(paths:string[],durationMs:number):void {
    if(this.closed||this.paused||!this.enabled)return;
    if(!Number.isFinite(durationMs)||durationMs<0||durationMs>5000||paths.length>500||paths.some(filename=>!path.isAbsolute(filename)||filename.includes('\0')||filename.length>4096||!this.roots.some(root=>filename.startsWith(root+path.sep))))throw new Error('Invalid owned-write suppression');
    this.driver?.suppress?.(paths,durationMs);
  }
  async close():Promise<void> {
    if(this.closed){await Promise.all(this.retiring);return;}
    this.closed=true;const stopping=this.retire();this.emit();await stopping;
  }
}
