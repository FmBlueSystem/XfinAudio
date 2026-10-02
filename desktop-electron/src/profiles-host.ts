interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  cancel:()=>Promise<unknown>;
  isClosing:()=>boolean;
}
/** Read-only work still drains before exit: a cancelled decoder may be finishing. */
export class ProfilesHost {
  private active:Promise<any>|null=null;
  get busy():boolean{return this.active!==null;}
  constructor(private readonly dependencies:Dependencies){}
  async complete():Promise<any>{
    if(this.dependencies.isClosing())throw new Error('[core_stopped]');
    if(this.busy)throw new Error('[busy]');
    const active=this.dependencies.request('profiles.complete',{});this.active=active;
    try{return await active;}finally{if(this.active===active)this.active=null;}
  }
  async cancel():Promise<{cancelled:boolean}>{if(!this.active)return {cancelled:false};await this.dependencies.cancel();return {cancelled:true};}
  async shutdown():Promise<void>{
    const active=this.active;if(!active)return;
    try{await this.dependencies.cancel();}catch{/* A stopped core has nothing left to cancel. */}
    try{await active;}catch{/* The bridge has already settled the terminal error. */}
  }
}
export function profileProgress(value:unknown):{phase:'profiles';stage:string;processedCount:number;totalCount:number;readyCount:number;failedCount:number}|null{
  if(!value||typeof value!=='object')return null;
  const data=value as Record<string,unknown>;
  if(data.phase!=='profiles'||!['spectral','danceability','edge'].includes(String(data.stage)))return null;
  for(const key of ['processedCount','totalCount','readyCount','failedCount'])if(!Number.isSafeInteger(data[key])||Number(data[key])<0||Number(data[key])>100000)return null;
  if(Number(data.processedCount)>Number(data.totalCount)||Number(data.readyCount)+Number(data.failedCount)!==Number(data.processedCount))return null;
  return {phase:'profiles',stage:String(data.stage),processedCount:Number(data.processedCount),totalCount:Number(data.totalCount),readyCount:Number(data.readyCount),failedCount:Number(data.failedCount)};
}
