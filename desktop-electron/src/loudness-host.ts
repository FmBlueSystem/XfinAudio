interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  confirm:(summary:any)=>Promise<boolean>;
  cancel:()=>Promise<unknown>;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Local loudness unavailable`),{code});
/** Main owns the native grant and drains metadata commits before generic core shutdown. */
export class LoudnessHost {
  private readonly previews=new Set<string>();
  private active:Promise<any>|null=null;
  private cancelRequested=false;
  busy=false;
  constructor(private readonly dependencies:Dependencies) {}
  private assertOpen():void {if(this.dependencies.isClosing())throw failure('core_stopped');}
  private async exclusive<T>(task:()=>Promise<T>):Promise<T> {
    this.assertOpen();if(this.busy)throw failure('busy');this.busy=true;
    try{return await task();}finally{this.busy=false;}
  }
  preview(params:Record<string,unknown>):Promise<any> {
    return this.exclusive(async()=>{
      const result=await this.dependencies.request('loudness.preview',params);
      this.previews.clear();this.previews.add(result.previewId);return result;
    });
  }
  run(previewId:string):Promise<any> {
    return this.exclusive(async()=>{
      if(!this.previews.has(previewId))throw failure('stale_loudness');
      this.cancelRequested=false;
      const summary=await this.dependencies.request('loudness.confirmation',{previewId});
      const confirmed=await this.dependencies.confirm(summary);this.assertOpen();
      if(!confirmed||this.cancelRequested)return {cancelled:true,changedCount:0,unchangedCount:0,failureCount:0,backupCount:0,warning:null,status:await this.dependencies.request('loudness.status',{})};
      this.previews.delete(previewId);
      const active=this.dependencies.request('loudness.run',{previewId,confirmed:true});this.active=active;
      try{return await active;}finally{if(this.active===active)this.active=null;}
    });
  }
  async cancel():Promise<{cancelled:boolean}> {
    if(!this.busy)return {cancelled:false};
    this.cancelRequested=true;if(this.active)await this.dependencies.cancel();return {cancelled:true};
  }
  async shutdown():Promise<void> {
    this.cancelRequested=true;
    if(this.active){try{await this.dependencies.cancel();}catch{/* Core may already have stopped. */}}
    try{await this.active;}catch{/* Any backup/commit outcome was finalized before response or exit. */}
  }
}
