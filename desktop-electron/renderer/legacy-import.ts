import {errorCode} from './errors.js';
export interface LegacyPreview {previewId:string;mode:'fresh-profile-only';trackCount:number;cachedTrackCount:number;playlistCount:number;referenceCount:number;playlistNames:string[];safePreferences:{previewVolume:number;spectralCohesion:number};requiresRootAuthorization:true;sourceUnchanged:true;}
export interface LegacyResult {imported:true;restartRequired:true;backupRetained:true;requiresRootAuthorization:true;trackCount:number;playlistCount:number;}
export interface LegacyImportApi {previewLegacyImport():Promise<LegacyPreview|{cancelled:true}>;applyLegacyImport(input:{previewId:string}):Promise<LegacyResult|{cancelled:true}>;discardLegacyImport(input:{previewId:string}):Promise<{discarded:true}>;}
interface Host {canAct():boolean;changed():void;applied():void;perform(label:string,task:()=>Promise<any>,apply:(value:any)=>void,failure:(error:unknown)=>void):Promise<void>;}
const messages:Record<string,string>={
  legacy_invalid:'No se puede importar esta selección. Se admiten bases originales con esquema actual, archivos regulares y tamaños limitados.',
  legacy_source_active:'Cierra la aplicación original y completa su checkpoint de SQLite antes de seleccionar la carpeta. No se importan bases con WAL, SHM o journal pendientes.',
  legacy_destination_not_empty:'La importación exige un perfil nuevo, sin biblioteca, sets guardados, ajustes ni carpetas autorizadas. No se sobrescribirá este perfil.',
  stale_legacy:'Los datos o el perfil cambiaron. Selecciona la carpeta y revisa una vista previa nueva.',
  legacy_import_failed:'No se completó la importación. Se restauró el perfil anterior y se conservaron las copias de seguridad.',
  legacy_recovery_required:'La importación requiere recuperación. Se conservaron los datos y copias; cierra la aplicación y revisa el perfil antes de continuar.',
  legacy_restart_required:'Cierra y vuelve a abrir la aplicación antes de continuar. Las carpetas musicales necesitan autorización y un nuevo escaneo.',
  legacy_storage_full:'Se alcanzó el límite de vistas previas retenidas. Revisa sus copias de seguridad antes de iniciar otra importación.',
};
export class LegacyImportController {
  preview:LegacyPreview|null=null;result:LegacyResult|null=null;pending=false;error='';
  constructor(private readonly api:LegacyImportApi,private readonly host:Host){}
  private fail=(error:unknown):void=>{const code=errorCode(error)??'';this.error=messages[code]??'La importación no está disponible. No continúes hasta comprobar el estado del perfil.';this.preview=null;if(['legacy_recovery_required','legacy_restart_required'].includes(code))this.host.applied();this.host.changed();};
  private async run(label:string,task:()=>Promise<any>,apply:(value:any)=>void):Promise<void>{
    if(this.pending||this.result||!this.host.canAct())return;
    this.pending=true;this.error='';this.host.changed();
    try{await this.host.perform(label,task,apply,this.fail);}catch(error){this.fail(error);}finally{this.pending=false;this.host.changed();}
  }
  async choose():Promise<void>{if(this.pending||this.result||!this.host.canAct())return;this.preview=null;await this.run('Revisando los datos de la aplicación original…',()=>this.api.previewLegacyImport(),value=>{this.preview=value.cancelled?null:value;});}
  async apply():Promise<void>{const preview=this.preview;if(!preview)return;await this.run('Importando datos locales con copia de seguridad…',()=>this.api.applyLegacyImport({previewId:preview.previewId}),value=>{if(value.cancelled)return;this.result=value;this.preview=null;this.host.applied();});}
  async discard():Promise<void>{const preview=this.preview;if(!preview)return;await this.run('Descartando la vista previa…',()=>this.api.discardLegacyImport({previewId:preview.previewId}),()=>{this.preview=null;});}
}
