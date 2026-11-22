import path from 'node:path';
import {lstat,realpath} from 'node:fs/promises';
export interface Preview {previewId:string;filename:string;destinationLabel:string;trackCount:number;readiness:string;warnings:string[];blockers:string[];canCommit:boolean;parentsToCreate:string[];backup:{required:boolean};crates?:TreeCrate[];}
export interface TreeCrate {name:string;trackCount:number;action:string;}
export interface Receipt {receiptId:string;filename:string;destinationLabel:string;trackCount:number;validated:true;backupCreated:boolean;parentsCreated:string[];files?:{name:string;trackCount:number}[];}
/** What one quick export answered: a receipt, a block, a missing destination, or a native cancellation. */
export type QuickExportResult={status:'exported';receipt:Receipt}|{status:'cancelled'}|{status:'blocked';filename:string;blockers:string[]}|{status:'needs_destination'};
/** `%%` is how Serato nests crates; the user reads a nested ancestor as «XfinAudio › Metadata». */
export function parentCrateLabel(name:string):string {return name.split('%%').join(' › ');}
/** A crate file name as the DJ reads it: no extension, and nesting shown as «XfinAudio › Set». */
export function crateTreeLabel(name:string):string {return parentCrateLabel(name.replace(/\.crate$/i,''));}
/**
 * One line per crate of a split export, parent first, in the exact wording the export page
 * uses; empty for today's single crate so nothing new is said.
 */
export function crateTreeLines(crates?:TreeCrate[]):string[] {
  if(!crates?.length)return [];
  return [`Se escribirán ${crates.length} ${crates.length===1?'crate':'crates'}:`,...crates.map(crate=>`· «${crateTreeLabel(crate.name)}» · ${crate.trackCount} ${crate.trackCount===1?'pista':'pistas'} · ${crate.action==='replace'?'se reemplaza':'se crea'}`)];
}
/** One Spanish sentence about the ancestor crates a confirmed commit will create; empty when there are none. */
export function parentCratesLine(names:string[]):string {
  const shown=names.map(parentCrateLabel);if(!shown.length)return '';
  return shown.length===1?`Se creará el crate «${shown[0]}»`:`Se crearán los crates ${shown.map(name=>`«${name}»`).join(', ')}`;
}
/** The exact native confirmation copy, built in one place so the dialog cannot drift from the preview. */
export function confirmationDetail(summary:{destinationPath:string;filename:string;trackCount:number;backup:{required:boolean};warnings:string[];parentsToCreate?:string[];crates?:TreeCrate[]}):string {
  const lines=[`Destino: ${path.join(summary.destinationPath,'Subcrates',summary.filename)}`,`${summary.trackCount} pistas en el orden revisado`,summary.backup.required?'Se reemplazará el crate existente y se conservará una copia de seguridad.':'Se creará un crate nuevo.'];
  const parents=parentCratesLine(summary.parentsToCreate??[]);if(parents)lines.push(parents);
  // S4: a split export names every crate this one confirmation creates or replaces.
  const tree=crateTreeLines(summary.crates);if(tree.length)lines.push(tree.join('\n'));
  lines.push(...summary.warnings);
  return lines.join('\n\n');
}
interface Dependencies {
  request:(method:string,params:Record<string,unknown>)=>Promise<any>;
  choose:()=>Promise<string|null>;
  confirm:(summary:Preview&{destinationPath:string})=>Promise<boolean>;
  reveal:(filename:string)=>void;
  isClosing:()=>boolean;
}
const failure=(code:string)=>Object.assign(new Error(`[${code}] Local export unavailable`),{code});
/** Only the core's "this id is not from this process" answer earns a re-detection; every other failure is surfaced. */
const unknownDestinationId=(error:unknown):boolean=>(error as {code?:unknown}|null)?.code==='unknown_destination';
/** Native authority stays in main; the renderer sees only scoped opaque handles. */
export class SeratoHost {
  private readonly destinations=new Map<string,string>();
  private readonly previews=new Map<string,string>();
  private readonly receipts=new Map<string,string>();
  private lastDestination:string|null=null;
  private critical:Promise<unknown>|null=null;
  busy=false;
  constructor(private readonly dependencies:Dependencies) {}
  /**
   * A stopped or replaced core forgets every id it issued. Nothing bound to the previous
   * process may be reused, and an in-flight commit keeps its own captured destination, so
   * `waitForCommit`/shutdown still drain it while these maps are already clear.
   */
  reset():void {
    this.destinations.clear();this.previews.clear();this.receipts.clear();this.lastDestination=null;
  }
  private assertOpen():void {if(this.dependencies.isClosing())throw failure('core_stopped');}
  private async exclusive<T>(task:()=>Promise<T>):Promise<T> {
    this.assertOpen();if(this.busy)throw failure('busy');this.busy=true;
    try{return await task();}finally{this.busy=false;}
  }
  async choose():Promise<{destinationId:string;label:string}|null> {
    return this.exclusive(async()=>{
      let selected:string|null=null;
      try{
        const suggestion=await this.dependencies.request('serato.suggestDestination',{});
        if(typeof suggestion?.suggestion==='string')selected=suggestion.suggestion;
      }catch{/* Discovery is best-effort; the native picker stays the authority. */}
      if(selected===null){selected=await this.dependencies.choose();if(selected===null)return null;}
      this.assertOpen();return this.register(selected);
    });
  }
  /** The same discovery the picker uses, run on its own so the screen never needs a dialog. */
  async detect():Promise<{destinationId:string;label:string}|null> {
    return this.exclusive(()=>this.detectDestination());
  }
  private async detectDestination():Promise<{destinationId:string;label:string}|null> {
    const suggestion=await this.dependencies.request('serato.suggestDestination',{});
    if(typeof suggestion?.suggestion!=='string')return null;
    this.assertOpen();return this.register(suggestion.suggestion);
  }
  /** Registering keeps the core's canonical check, so only an existing folder reaches it. */
  private async register(selected:string):Promise<{destinationId:string;label:string}> {
    const root=await this.resolveSelection(selected);
    const result=await this.dependencies.request('serato.registerDestination',{seratoRoot:root});
    this.destinations.set(result.destinationId,root);
    // One session keeps one destination: discovery must not accumulate core export sessions.
    this.lastDestination=result.destinationId;
    return result;
  }
  /**
   * A drive root or `~/Music` is a fair choice: use the `_Serato_` folder it directly
   * contains, and nothing else. Both folders must be real directories, so the core's
   * canonical and no-symlink checks still see the exact folder that will be written.
   */
  private async resolveSelection(selected:string):Promise<string> {
    const root=await realpath(selected);
    if(path.basename(root)==='_Serato_')return root;
    const inner=path.join(root,'_Serato_');
    try{
      const folder=await lstat(inner),
        subcrates=await lstat(path.join(inner,'Subcrates'));
      if(folder.isDirectory()&&!folder.isSymbolicLink()&&subcrates.isDirectory()&&!subcrates.isSymbolicLink())return inner;
    }catch{/* Anything else keeps the existing invalid_destination refusal. */}
    return root;
  }
  async preview(params:Record<string,unknown>):Promise<Preview> {
    return this.exclusive(async()=>{
      const preview=await this.previewDetectingOnce(params);
      // Detection found nothing after the id was forgotten: the page shows its not-found notice.
      if(!preview)throw failure('unknown_destination');
      return preview;
    });
  }
  /**
   * The safety net: a destination id the core does not know (a restart) is forgotten and
   * resolved by one detection and one retry. Nothing else is retried, and a commit is
   * never part of this path.
   */
  private async previewDetectingOnce(params:Record<string,unknown>):Promise<Preview|null> {
    try{return await this.previewSource(params);}
    catch(error){
      if(!unknownDestinationId(error))throw error;
      const forgotten=String(params.destinationId);
      this.destinations.delete(forgotten);if(this.lastDestination===forgotten)this.lastDestination=null;
      const detected=await this.detectDestination();
      if(!detected)return null;
      return await this.previewSource({...params,destinationId:detected.destinationId});
    }
  }
  private async previewSource(params:Record<string,unknown>):Promise<Preview> {
    const destination=this.destinations.get(String(params.destinationId));if(!destination)throw failure('unknown_destination');
    const source=params.source as {kind:string;playlistId?:string;reviewId?:string};
    const resolved=source.kind==='saved'?{kind:'saved',playlistId:Number(source.playlistId)}:source;
    const result:Preview=await this.dependencies.request('serato.preview',{...params,source:resolved});
    this.previews.set(result.previewId,destination);return result;
  }
  async commit(previewId:string):Promise<Receipt|{cancelled:true}> {
    return this.exclusive(()=>this.commitPreview(previewId));
  }
  private async commitPreview(previewId:string):Promise<Receipt|{cancelled:true}> {
    const destinationPath=this.previews.get(previewId);if(!destinationPath)throw failure('invalid_preview');
    const summary:Preview=await this.dependencies.request('serato.confirmation',{previewId});
    if(!summary.canCommit||summary.blockers.length)throw failure('blocked_export');
    if(!await this.dependencies.confirm({...summary,destinationPath}))return {cancelled:true};
    this.assertOpen();
    const publication:Promise<Receipt>=this.dependencies.request('serato.commit',{previewId,confirmed:true});
    this.critical=publication;
    try {const receipt=await publication;this.receipts.set(receipt.receiptId,destinationPath);return receipt;}
    finally {if(this.critical===publication)this.critical=null;}
  }
  async waitForCommit():Promise<void> {try{await this.critical;}catch{/* Writer rollback completes before shutdown. */}}
  /**
   * The two-action export: one serialized operation runs the existing discovery, preview,
   * native confirmation and commit in order. Nothing here is a second write path; a block
   * or a missing destination answers before any dialog opens.
   */
  async quickExport(params:Record<string,unknown>):Promise<QuickExportResult> {
    return this.exclusive(async()=>{
      let destinationId=this.lastDestination;
      if(!destinationId){
        const detected=await this.detectDestination();
        if(!detected)return {status:'needs_destination'};
        destinationId=detected.destinationId;
      }
      this.assertOpen();
      const preview=await this.previewDetectingOnce({...params,destinationId});
      if(!preview)return {status:'needs_destination'};
      if(!preview.canCommit||preview.blockers.length)return {status:'blocked',filename:preview.filename,blockers:[...preview.blockers]};
      const committed=await this.commitPreview(preview.previewId);
      return 'cancelled' in committed?{status:'cancelled'}:{status:'exported',receipt:committed};
    });
  }
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
