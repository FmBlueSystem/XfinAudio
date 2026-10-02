import {errorCode,userErrorMessage} from './errors.js';
export interface ProfileSettings {revision:string;spectralCohesion:number;}
export interface ProfileSettingsApi {getProfileSettings():Promise<ProfileSettings>;saveProfileSettings(input:ProfileSettings):Promise<ProfileSettings>;}
interface Host {canAct():boolean;changed():void;dirtyChanged(dirty:boolean):void;applied():void;perform(label:string,task:()=>Promise<ProfileSettings>,apply:(value:ProfileSettings)=>void,failure:(error:unknown)=>void):Promise<void>;}
const bounded=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=1;
function copy(value:ProfileSettings):ProfileSettings {if(!value||!/^[a-f0-9]{64}$/.test(value.revision)||!bounded(value.spectralCohesion))throw Object.assign(new Error('Invalid profile settings'),{code:'settings_unavailable'});return {revision:value.revision,spectralCohesion:value.spectralCohesion};}
export class ProfileSettingsController {
  private base:ProfileSettings|null=null;
  snapshot:ProfileSettings|null=null;
  private conflict=false;
  pending=false;error='';
  constructor(private readonly api:ProfileSettingsApi,private readonly host:Host){}
  get dirty():boolean{return Boolean(this.base&&this.snapshot&&this.base.spectralCohesion!==this.snapshot.spectralCohesion);}
  get canSave():boolean{return this.dirty&&!this.pending&&!this.conflict;}
  private notify():void{this.host.dirtyChanged(this.dirty);this.host.changed();}
  private fail=(error:unknown):void=>{if(errorCode(error)==='stale_settings')this.conflict=true;this.error=userErrorMessage(error);this.notify();};
  private async run(save:boolean):Promise<void>{
    if(this.pending||!this.host.canAct())return;
    this.pending=true;this.error='';this.host.changed();
    try{await this.host.perform(save?'Guardando cohesión espectral…':'Cargando cohesión espectral…',()=>save?this.api.saveProfileSettings(copy(this.snapshot!)):this.api.getProfileSettings(),value=>{this.base=copy(value);this.snapshot=copy(value);this.conflict=false;if(save)this.host.applied();this.notify();},this.fail);}
    catch(error){this.fail(error);}finally{this.pending=false;this.notify();}
  }
  async load():Promise<void>{if(this.dirty){this.error='Guarda o descarta los cambios antes de actualizar.';this.notify();return;}await this.run(false);}
  setCohesion(value:number):void{if(!this.snapshot||this.pending||!this.host.canAct())return;if(!bounded(value)){this.error='La cohesión debe estar entre 0 y 100 %.';this.notify();return;}this.snapshot={...this.snapshot,spectralCohesion:value};if(!this.conflict)this.error='';this.notify();}
  async save():Promise<void>{if(this.canSave)await this.run(true);}
  discard():void{if(!this.base||this.pending||!this.host.canAct())return;this.snapshot=copy(this.base);this.error=this.conflict?'Borrador descartado. Pulsa Actualizar para cargar los ajustes vigentes.':'';this.notify();}
}
export function createProfileSettingsView(root:HTMLElement,controller:ProfileSettingsController,host:{canAct():boolean}):()=>void {
  const make=<K extends keyof HTMLElementTagNameMap>(tag:K,id:string,text=''):HTMLElementTagNameMap[K]=>{const node=document.createElement(tag);node.id=`profile-settings-${id}`;node.textContent=text;return node;};
  const section=make('section','section');section.className='surface prep-form';section.setAttribute('aria-labelledby','profile-settings-heading');
  const label=make('label','label','Cohesión espectral');label.setAttribute('for','profile-settings-cohesion');
  const input=make('input','cohesion');input.type='range';input.min='0';input.max='1';input.step='.01';input.setAttribute('aria-describedby','profile-settings-hint profile-settings-level');
  const level=make('output','level');level.setAttribute('for',input.id);
  const hint=make('p','hint','Ajusta el peso original de la cohesión espectral al preparar y recomendar pistas. Solo Guardar aplica el cambio; no analiza ni modifica el audio.');hint.className='field-hint';
  const error=make('p','error');error.setAttribute('role','alert');const dirty=make('p','dirty');dirty.setAttribute('aria-live','polite');
  input.addEventListener('input',()=>controller.setCohesion(Number(input.value)));
  const button=(id:string,text:string,action:()=>void)=>{const node=make('button',id,text);node.type='button';node.className='button subtle';node.addEventListener('click',()=>{if(!node.disabled&&host.canAct())action();});return node;};
  const save=button('save','Guardar cohesión',()=>{void controller.save();}),discard=button('discard','Descartar cohesión',()=>controller.discard()),refresh=button('refresh','Actualizar cohesión',()=>{void controller.load();});
  section.append(make('h3','heading','Perfiles y cohesión'),label,input,level,hint,error,dirty,save,discard,refresh);root.replaceChildren(section);
  return()=>{const blocked=!host.canAct()||controller.pending;input.disabled=blocked||!controller.snapshot;save.disabled=blocked||!controller.canSave;discard.disabled=blocked||!controller.dirty;refresh.disabled=blocked;error.textContent=controller.error;error.hidden=!controller.error;dirty.textContent=controller.dirty?'Cambios de cohesión sin guardar. Se conservan al cambiar de pantalla.':'Sin cambios de cohesión pendientes.';input.value=controller.snapshot?String(controller.snapshot.spectralCohesion):'';level.textContent=controller.snapshot?`${Math.round(controller.snapshot.spectralCohesion*100)} %`:'Sin cargar';input.setAttribute('aria-valuetext',level.textContent);};
}
