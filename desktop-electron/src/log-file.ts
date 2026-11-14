import path from 'node:path';
import {appendFile,lstat,mkdir,realpath,rename,rm,stat} from 'node:fs/promises';

export const LOG_FILE_NAME='xfinaudio.log';
/** The current file never grows past this size; rotation keeps one previous generation. */
export const LOG_MAX_BYTES=1024*1024;
export const LOG_MAX_FILES=2;
export const LOG_LINE_MAX=2000;
/** One entry per write: no newlines, no control characters, bounded length. */
function entryLine(line:string):string {
  return String(line??'').replace(/[\r\n\t\x00-\x1f\x7f]+/g,' ').replace(/\s+/g,' ').trim().slice(0,LOG_LINE_MAX);
}
/**
 * Size-bounded rotating support log under the app data directory.
 * A lost log entry is never allowed to break the caller: `write` returns void and
 * `flush` never rejects, so main may log from error paths.
 */
export class RotatingLog {
  private queue:Promise<void>=Promise.resolve();
  private size:number|null=null;
  private readonly directory:string;
  private readonly maxBytes:number;
  private readonly maxFiles:number;
  private readonly now:()=>Date;
  constructor(directory:string,options:{maxBytes?:number;maxFiles?:number;now?:()=>Date}={}) {
    this.directory=directory;
    this.maxBytes=options.maxBytes&&options.maxBytes>0?options.maxBytes:LOG_MAX_BYTES;
    this.maxFiles=Math.max(1,Math.floor(options.maxFiles&&options.maxFiles>0?options.maxFiles:LOG_MAX_FILES));
    this.now=options.now??(()=>new Date());
  }
  get file():string {return path.join(this.directory,LOG_FILE_NAME);}
  write(line:string):void {
    const text=entryLine(line);
    if(!text)return;
    const entry=`${this.now().toISOString()} ${text}\n`;
    this.queue=this.queue.then(()=>this.append(entry)).catch(()=>{this.size=null;});
  }
  /** Resolves once every queued entry reached the disk (tests and teardown). */
  flush():Promise<void> {return this.queue.then(()=>undefined,()=>undefined);}
  private async append(entry:string):Promise<void> {
    try {
      const bytes=Buffer.byteLength(entry);
      if(this.size===null)this.size=await this.currentSize();
      if(this.size>0&&this.size+bytes>this.maxBytes)await this.rotate();
      await mkdir(this.directory,{recursive:true});
      await appendFile(this.file,entry,{encoding:'utf8',mode:0o600});
      this.size=this.size+bytes;
    } catch {this.size=null;}
  }
  private async currentSize():Promise<number> {
    try {
      const info=await stat(this.file);
      return info.isFile()?info.size:0;
    } catch {return 0;}
  }
  private async rotate():Promise<void> {
    this.size=0;
    if(this.maxFiles<=1){await rm(this.file,{force:true});return;}
    for(let index=this.maxFiles-1;index>=1;index-=1) {
      const source=index===1?this.file:`${this.file}.${index-1}`;
      const target=`${this.file}.${index}`;
      try {await rm(target,{force:true});await rename(source,target);} catch { /* a missing generation is not a failure */ }
    }
  }
}
/** Reveal only the fixed app-owned log directory, never a renderer-provided path. */
export async function revealLogFolder(dataDir:string,reveal:(filename:string)=>void):Promise<{found:boolean}> {
  const folder=path.join(dataDir,'logs');
  let info;
  try {info=await lstat(folder);} catch(error) {if((error as NodeJS.ErrnoException).code==='ENOENT')return {found:false};throw error;}
  if(!info.isDirectory()||info.isSymbolicLink()||await realpath(folder)!==folder)throw new Error('[logs_unavailable] Log directory unavailable');
  reveal(folder);return {found:true};
}
