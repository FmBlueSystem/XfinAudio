import path from 'node:path';
import {lstat,realpath} from 'node:fs/promises';
interface Preview {previewId:string;filename:string;destinationLabel:string;trackCount:number;readiness:string;warnings:string[];blockers:string[];canCommit:boolean;backup:{required:boolean};}
interface Receipt {receiptId:string;filename:string;destinationLabel:string;trackCount:number;validated:true;backupCreated:boolean;}
interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  choose:()=>Promise<string|null>;
  confirm:(summary:Preview&{destinationPath:string})=>Promise<boolean>;
  reveal:(filename:string)=>void;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Local export unavailable`),{code});
/** Native authority stays in main; the renderer sees only scoped opaque handles. */
export class SeratoHost {
  private readonly destinations=new Map<string,string>();
  private readonly previews=new Map<string,string>();
  private readonly receipts=new Map<string,string>();
  private critical:Promise<unknown>|null=null;
  busy=false;
  constructor(private readonly dependencies:Dependencies) {}
  private assertOpen():void {if(this.dependencies.isClosing())throw failure('core_stopped');}
  private async exclusive<T>(task:()=>Promise<T>):Promise<T> {
    this.assertOpen();if(this.busy)throw failure('busy');this.busy=true;
    try{return await task();}finally{this.busy=false;}
  }
  async choose():Promise<{destinationId:string;label:string}|null> {
    return this.exclusive(async()=>{
      const selected=await this.dependencies.choose();if(selected===null)return null;
      this.assertOpen();const root=await realpath(selected);
      const result=await this.dependencies.request('serato.registerDestination',{seratoRoot:root});
      this.destinations.set(result.destinationId,root);return result;
    });
  }
  async preview(params:Record<string,unknown>):Promise<Preview> {
    return this.exclusive(async()=>{
      const destination=this.destinations.get(String(params.destinationId));if(!destination)throw failure('invalid_destination');
      const source=params.source as {kind:string;playlistId?:string;reviewId?:string};
      const resolved=source.kind==='saved'?{kind:'saved',playlistId:Number(source.playlistId)}:source;
      const result:Preview=await this.dependencies.request('serato.preview',{...params,source:resolved});
      this.previews.set(result.previewId,destination);return result;
    });
  }
  async commit(previewId:string):Promise<Receipt|{cancelled:true}> {
    return this.exclusive(async()=>{
      const destinationPath=this.previews.get(previewId);if(!destinationPath)throw failure('invalid_preview');
      const summary:Preview=await this.dependencies.request('serato.confirmation',{previewId});
      if(!summary.canCommit||summary.blockers.length)throw failure('blocked_export');
      if(!await this.dependencies.confirm({...summary,destinationPath}))return {cancelled:true};
      this.assertOpen();
      const publication:Promise<Receipt>=this.dependencies.request('serato.commit',{previewId,confirmed:true});
      this.critical=publication;
      try {const receipt=await publication;this.receipts.set(receipt.receiptId,destinationPath);return receipt;}
      finally {if(this.critical===publication)this.critical=null;}
    });
  }
  async waitForCommit():Promise<void> {try{await this.critical;}catch{/* Writer rollback completes before shutdown. */}}
  async reveal(receiptId:string):Promise<void> {
    return this.exclusive(async()=>{
      const root=this.receipts.get(receiptId);if(!root)throw failure('invalid_preview');
      const result=await this.dependencies.request('serato.receipt.resolve',{receiptId});
      const filename=result.path;
      if(typeof filename!=='string'||path.dirname(filename)!==path.join(root,'Subcrates')||path.extname(filename)!=='.crate')throw failure('invalid_destination');
      const info=await lstat(filename);
      if(!info.isFile()||info.isSymbolicLink()||await realpath(filename)!==filename)throw failure('stale_destination');
      this.assertOpen();this.dependencies.reveal(filename);
    });
  }
}
