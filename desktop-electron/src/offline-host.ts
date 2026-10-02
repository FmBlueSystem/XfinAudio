export interface DeletePreview { previewId:string; playlistId:number; revision:string; name:string; trackCount:number; }
interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  confirm:(summary:DeletePreview)=>Promise<boolean>;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Saved playlist operation unavailable`),{code});
const summary=(item:any)=>({id:String(item.id),name:item.name,trackCount:item.trackCount,createdAt:item.updatedAt});
/** Native confirmation is bound to a one-use backend snapshot; audio is never deleted. */
export class OfflineHost {
  busy=false;
  private critical:Promise<unknown>|null=null;
  constructor(private readonly dependencies:Dependencies){}
  private assertOpen():void{if(this.dependencies.isClosing())throw failure('core_stopped');}
  private async exclusive<T>(task:()=>Promise<T>):Promise<T>{this.assertOpen();if(this.busy)throw failure('busy');this.busy=true;try{return await task();}finally{this.busy=false;}}
  async query(params:Record<string,unknown>):Promise<any>{return this.exclusive(()=>this.dependencies.request('library.query',params));}
  async search(request:string):Promise<any[]>{return this.exclusive(async()=>(await this.dependencies.request('playlist.search',{request})).playlists.map(summary));}
  async compare(playlistIds:string[]):Promise<{comparison:string}>{return this.exclusive(()=>this.dependencies.request('playlist.compare',{playlistIds:playlistIds.map(Number)}));}
  async deleted():Promise<any[]>{return this.exclusive(async()=>(await this.dependencies.request('playlist.deleted.list',{})).playlists);}
  async restore(deletionId:string):Promise<any>{return this.exclusive(async()=>{const task=this.dependencies.request('playlist.restore',{deletionId});this.critical=task;try{return summary(await task);}finally{if(this.critical===task)this.critical=null;}});}
  async delete(playlistId:string):Promise<{cancelled:true}|{deletionId:string;name:string}>{
    return this.exclusive(async()=>{
      const preview:DeletePreview=await this.dependencies.request('playlist.delete.preview',{playlistId:Number(playlistId)});
      if(!await this.dependencies.confirm(preview))return {cancelled:true};
      this.assertOpen();
      const task=this.dependencies.request('playlist.delete.commit',{previewId:preview.previewId,confirmed:true});this.critical=task;
      try{return await task;}finally{if(this.critical===task)this.critical=null;}
    });
  }
  async waitForCommit():Promise<void>{try{await this.critical;}catch{/* Atomic rollback finishes before database shutdown. */}}
}
