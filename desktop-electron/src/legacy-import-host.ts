export interface LegacyPreview {
  previewId:string;mode:'fresh-profile-only';trackCount:number;cachedTrackCount:number;playlistCount:number;referenceCount:number;
  playlistNames:string[];safePreferences:{previewVolume:number;spectralCohesion:number};requiresRootAuthorization:true;sourceUnchanged:true;
}
export interface LegacyResult {imported:true;restartRequired:true;backupRetained:true;requiresRootAuthorization:true;trackCount:number;playlistCount:number;}
interface Dependencies {
  chooseDirectory:()=>Promise<string|null>;request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  confirm:(summary:LegacyPreview&{sourceDirectory:string})=>Promise<boolean>;canStart:()=>boolean;isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Legacy import unavailable`),{code});
const token=(value:unknown):value is string=>typeof value==='string'&&/^[a-f0-9]{32}$/.test(value);
function summary(value:any):LegacyPreview {
  if(!value||!token(value.previewId)||value.mode!=='fresh-profile-only'||value.requiresRootAuthorization!==true||value.sourceUnchanged!==true)throw failure('legacy_invalid');
  for(const [key,max] of Object.entries({trackCount:100000,cachedTrackCount:100000,playlistCount:5000,referenceCount:250000}))if(!Number.isSafeInteger(value[key])||value[key]<0||value[key]>max)throw failure('legacy_invalid');
  if(value.cachedTrackCount>value.trackCount||!Array.isArray(value.playlistNames)||value.playlistNames.length>Math.min(20,value.playlistCount)||value.playlistNames.some((name:unknown)=>typeof name!=='string'||name.length>200))throw failure('legacy_invalid');
  for(const key of ['previewVolume','spectralCohesion'])if(typeof value.safePreferences?.[key]!=='number'||!Number.isFinite(value.safePreferences[key])||value.safePreferences[key]<0||value.safePreferences[key]>1)throw failure('legacy_invalid');
  return {previewId:value.previewId,mode:'fresh-profile-only',trackCount:value.trackCount,cachedTrackCount:value.cachedTrackCount,playlistCount:value.playlistCount,referenceCount:value.referenceCount,playlistNames:[...value.playlistNames],safePreferences:{previewVolume:value.safePreferences.previewVolume,spectralCohesion:value.safePreferences.spectralCohesion},requiresRootAuthorization:true,sourceUnchanged:true};
}
/** Native selection and dialog are the sole authority; committing work drains at close. */
export class LegacyImportHost {
  private pending:{source:string;preview:LegacyPreview}|null=null;
  private active:Promise<any>|null=null;
  restartRequired=false;
  get busy():boolean{return this.active!==null;}
  constructor(private readonly dependencies:Dependencies){}
  private assertOpen():void{if(this.dependencies.isClosing())throw failure('core_stopped');if(this.restartRequired)throw failure('legacy_restart_required');}
  private exclusive<T>(task:()=>Promise<T>):Promise<T>{
    try{this.assertOpen();if(this.busy||!this.dependencies.canStart())throw failure('busy');}catch(error){return Promise.reject(error);}
    const active=Promise.resolve().then(task);this.active=active;
    return active.finally(()=>{if(this.active===active)this.active=null;});
  }
  preview():Promise<LegacyPreview|{cancelled:true}>{return this.exclusive(async()=>{
    this.pending=null;
    const source=await this.dependencies.chooseDirectory();this.assertOpen();
    if(source===null)return {cancelled:true};
    const preview=summary(await this.dependencies.request('legacy.preview',{source}));this.assertOpen();
    this.pending={source,preview};return summary(preview);
  });}
  apply(previewId:string):Promise<LegacyResult|{cancelled:true}>{return this.exclusive(async()=>{
    const pending=this.pending;if(!token(previewId)||pending?.preview.previewId!==previewId)throw failure('stale_legacy');
    const confirmed=await this.dependencies.confirm({...summary(pending.preview),sourceDirectory:pending.source});this.assertOpen();
    if(!confirmed)return {cancelled:true};
    this.pending=null;
    let value:any;
    try{value=await this.dependencies.request('legacy.apply',{previewId,confirmed:true});}
    catch(error){const code=typeof (error as any)?.code==='string'?(error as any).code:String((error as any)?.message??'').match(/\[([a-z_]+)\]/)?.[1];
      if(['legacy_import_failed','stale_legacy','legacy_invalid','invalid_params','confirmation_required','legacy_destination_not_empty'].includes(code))throw error;
      this.restartRequired=true;throw failure(code==='legacy_recovery_required'?'legacy_recovery_required':'legacy_restart_required');}
    this.restartRequired=true;
    if(value?.imported!==true||value.restartRequired!==true||value.backupRetained!==true||value.requiresRootAuthorization!==true||value.trackCount!==pending.preview.trackCount||value.playlistCount!==pending.preview.playlistCount)throw failure('legacy_restart_required');
    this.restartRequired=true;
    return {imported:true,restartRequired:true,backupRetained:true,requiresRootAuthorization:true,trackCount:value.trackCount,playlistCount:value.playlistCount};
  });}
  discard(previewId:string):Promise<{discarded:true}>{return this.exclusive(async()=>{
    if(!token(previewId)||this.pending?.preview.previewId!==previewId)throw failure('stale_legacy');
    this.pending=null;await this.dependencies.request('legacy.discard',{previewId});return {discarded:true};
  });}
  async shutdown():Promise<void>{try{await this.active;}catch{/* Backend outcome is settled before teardown. */}this.pending=null;}
}
