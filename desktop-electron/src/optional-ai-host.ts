import path from 'node:path';
import {lstat,realpath} from 'node:fs/promises';
export const AI_RECIPIENT='https://api.nan.builders/v1/chat/completions';
/**
 * S4: what the native dialog answered. The dialog may also offer the persisted approval switch,
 * and the preference it stores runs after the turn it approved, never before it.
 */
export interface OptionalAiConsent {
  confirmed:boolean;
  storePreference?:()=>Promise<void>;
}
interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  choose:()=>Promise<string|null>;
  confirm:(summary:any)=>Promise<boolean|OptionalAiConsent>;
  cancel:()=>Promise<unknown>;
  autoAuthorize:()=>Promise<boolean>;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Optional assistance unavailable`),{code});
/**
 * S3: what the system could not do while it asked for the turn, as fixed codes. The renderer
 * owns the Spanish words, and the answer carries the codes so the chat can show them.
 */
export type OptionalAiNote='dialog_preference_not_saved'|'auto_authorize_unavailable';
const NOTE_CODES:ReadonlySet<string>=new Set<OptionalAiNote>(['dialog_preference_not_saved','auto_authorize_unavailable']);
/** Sensitive authority: native file selection, or persisted automatic authorization granted in Ajustes. */
export class OptionalAiHost {
  /**
   * Owned previews, mapped to whether they continue a conversation the user already
   * authorised. Only the preview itself can say so: the core reports `firstTurn` true
   * while a conversation is empty.
   */
  private previews=new Map<string,boolean>();
  private cancelRequested=false;
  private active=false;
  /** S3: the notes of the ask in flight; they travel with its answer and never postdate it. */
  private notes:OptionalAiNote[]=[];
  busy=false;
  asking=false;
  constructor(private readonly dependencies:Dependencies) {}
  /** S3: records what could not be stored or read. An unknown code is refused, a repeat is kept once. */
  note(code:string):void {
    if(!NOTE_CODES.has(code)||this.notes.includes(code as OptionalAiNote))return;
    this.notes.push(code as OptionalAiNote);
  }
  private answered(value:any):any {return this.notes.length===0?value:{...value,notes:[...this.notes]};}
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
      // Consent is asked once per conversation, not once per message. Only an explicit
      // `chat` preview that reports a non-empty conversation skips the dialog; a missing
      // or unexpected `firstTurn` keeps the dialog, so an older core never loses the ask.
      this.previews.clear();
      this.previews.set(preview.previewId,preview.surface==='chat'&&preview.firstTurn===false);
      return preview;
    });
  }
  ask(previewId:string):Promise<any> {
    return this.exclusive(async()=>{
      if(!this.previews.has(previewId))throw failure('stale_ai');
      const continuesConversation=this.previews.get(previewId)===true;
      this.asking=true;this.cancelRequested=false;this.notes=[];
      try{
        // Persisted automatic authorization (opt-in from Ajustes) replaces the
        // per-query ai.confirmation fetch and native dialog. Anything other
        // than === true keeps the dialog path (fail-closed).
        if(await this.dependencies.autoAuthorize()===true){
          this.previews.delete(previewId);this.active=true;
          try{return this.answered(await this.dependencies.request('ai.run',{previewId,confirmed:true}));}finally{this.active=false;}
        }
        const summary=await this.dependencies.request('ai.confirmation',{previewId});
        if(summary.recipient!==AI_RECIPIENT)throw failure('ai_request_failed');
        // A later turn sends exactly what the first turn disclosed. The request still
        // re-runs ai.confirmation so a stale preview or configuration is caught here.
        const consent=continuesConversation?true:await this.dependencies.confirm(summary);this.assertOpen();
        const confirmed=typeof consent==='boolean'?consent:consent.confirmed===true;
        const storePreference=typeof consent==='boolean'?null:consent.storePreference??null;
        if(!confirmed||this.cancelRequested)return this.answered({cancelled:true,result:null});
        this.previews.delete(previewId);this.active=true;
        let answer:any=null;let failed:unknown=null;
        try{answer=await this.dependencies.request('ai.run',{previewId,confirmed:true});}
        catch(error){failed=error;}
        finally{this.active=false;}
        // S4: the dialog's own preference is stored once the turn it approved has run, so the
        // save can never revoke that turn. S3: the chat says in Spanish when it was not stored.
        if(storePreference){try{await storePreference();}catch{this.note('dialog_preference_not_saved');}}
        if(failed)throw failed;
        return this.answered(answer);
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
