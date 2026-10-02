import {realpath} from 'node:fs/promises';
import {LibraryWatch} from './library-watch';
type Request=(method:string,params?:Record<string,unknown>)=>Promise<any>;
/** Native host owns paths and watcher lifetime; renderer sees status and preferences only. */
export class LibraryHost {
  private roots:string[]=[];
  busy=false;
  private enabled=false;
  constructor(private readonly watch:LibraryWatch,private readonly request:Request) {}
  get status(){return this.watch.status;}
  async initialize():Promise<void> {
    try{await this.readRoots();const preferences=await this.request('settings.get');this.enabled=preferences.watchLibrary===true;await this.watch.configure(this.roots,this.enabled);}
    catch(error){console.error('Library observation could not initialize',error);this.enabled=false;await this.watch.configure(this.roots,false);}
  }
  private async readRoots():Promise<void> {
    const value=await this.request('library.roots');
    if(!Array.isArray(value.roots)||value.roots.some((root:unknown)=>typeof root!=='string'))throw new Error('Invalid core roots');
    this.roots=value.roots;
  }
  async savePreferences(params:Record<string,unknown>):Promise<unknown> {
    this.busy=true;
    try{const result=await this.request('settings.update',params);const enabled=result.watchLibrary===true;if(enabled!==this.enabled){this.enabled=enabled;await this.watch.configure(this.roots,enabled);}return result;}
    finally{this.busy=false;}
  }
  scan(root:string):Promise<unknown>{return this.scanOwned('library.scan',{root});}
  rescan():Promise<unknown>{return this.scanOwned('library.rescan',{});}
  private async scanOwned(method:string,params:Record<string,unknown>):Promise<unknown> {
    this.busy=true;let result:any=null,completed:string[]|null=null;
    try{
      await this.watch.beginScan();result=await this.request(method,params);
      if(!result.cancelled)completed=method==='library.rescan'?[...this.roots]:[await realpath(String(params.root)).catch(()=>String(params.root))];
      return {...result,count:result.tracks.length};
    }finally{
      try{await this.readRoots();}catch(error){console.error('Cannot refresh authorized library roots',error);completed=null;}
      try{await this.watch.finishScan(this.roots,completed);}finally{this.busy=false;}
    }
  }
  suppressPaths(paths:string[],durationMs:number):void{this.watch.suppressPaths(paths,durationMs);}
  close():Promise<void>{return this.watch.close();}
}
