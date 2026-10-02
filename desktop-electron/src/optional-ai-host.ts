import path from 'node:path';
import {lstat,realpath} from 'node:fs/promises';
export const AI_RECIPIENT='https://api.nan.builders/v1/chat/completions';
interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  choose:()=>Promise<string|null>;
  confirm:(summary:any)=>Promise<boolean>;
  cancel:()=>Promise<unknown>;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Optional assistance unavailable`),{code});
/** Only native file selection and per-request confirmation grant sensitive authority. */
export class OptionalAiHost {
  private previews=new Set<string>();
  private cancelRequested=false;
  private active=false;
  busy=false;
  asking=false;
  constructor(private readonly dependencies:Dependencies) {}
  private assertOpen():void {if(this.dependencies.isClosing())throw failure('core_stopped');}
  private async exclusive<T>(task:()=>Promise<T>):Promise<T> {
    this.assertOpen();if(this.busy)throw failure('busy');this.busy=true;
    try{return await task();}finally{this.busy=false;}
  }
  choose(params:Record<string,unknown>):Promise<any> {
    return this.exclusive(async()=>{
      let selected:string|null;
      try{selected=await this.dependencies.choose();}catch{throw failure('ai_credentials_unavailable');}
      this.assertOpen();
      if(selected===null)return this.dependencies.request('ai.status',{});
      if(!path.isAbsolute(selected)||selected.length>4096||selected.includes('\0'))throw failure('ai_credentials_unavailable');
      let canonical:string;
      try{
        const info=await lstat(selected);
        if(!info.isFile()||info.isSymbolicLink()||info.size>65536)throw failure('ai_credentials_unavailable');
        canonical=await realpath(selected);
      }catch{throw failure('ai_credentials_unavailable');}
      this.previews.clear();
      return this.dependencies.request('ai.credential.set',{revision:params.revision,path:canonical});
    });
  }
  prepare(params:Record<string,unknown>):Promise<any> {
    return this.exclusive(async()=>{
      const preview=await this.dependencies.request('ai.prepare',params);
      if(preview.recipient!==AI_RECIPIENT)throw failure('ai_request_failed');
      this.previews.clear();this.previews.add(preview.previewId);return preview;
    });
  }
  ask(previewId:string):Promise<any> {
    return this.exclusive(async()=>{
      if(!this.previews.has(previewId))throw failure('stale_ai');
      this.asking=true;this.cancelRequested=false;
      try{
        const summary=await this.dependencies.request('ai.confirmation',{previewId});
        if(summary.recipient!==AI_RECIPIENT)throw failure('ai_request_failed');
        const confirmed=await this.dependencies.confirm(summary);this.assertOpen();
        if(!confirmed||this.cancelRequested)return {cancelled:true,result:null};
        this.previews.delete(previewId);this.active=true;
        try{return await this.dependencies.request('ai.run',{previewId,confirmed:true});}finally{this.active=false;}
      }finally{this.asking=false;}
    });
  }
  async cancel():Promise<{cancelled:boolean}> {
    if(!this.asking)return {cancelled:false};
    this.cancelRequested=true;if(this.active)await this.dependencies.cancel();return {cancelled:true};
  }
  async shutdown():Promise<void> {
    this.cancelRequested=true;
    if(this.active){try{await this.dependencies.cancel();}catch{/* A disconnected core cannot publish a response. */}}
  }
}
