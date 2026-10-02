import type {Track,PlaylistSummary} from './model.js';
import { createDraftNotice } from './draft-notice.js';
import type { DraftNoticeHost } from './draft-notice.js';
export const LIBRARY_COLUMNS=[['title','Título'],['artist','Artista'],['genre','Género'],['bpm','BPM'],['key','Tonalidad'],['energy','Energía'],['duration','Duración'],['format','Formato'],['bitrate','Bitrate declarado']] as const;
export interface LibraryQuery {text?:string;genre?:string|null;bpm_min?:number|null;bpm_max?:number|null;key?:string|null;energy_min?:number|null;energy_max?:number|null;}
export interface LibraryBrowseInput {request?:string;query?:LibraryQuery;sortBy?:string;descending?:boolean;hideDuplicates?:boolean;}
export interface LibraryBrowseResult {tracks:Track[];query:LibraryQuery&{interpretation_note?:string};genres:string[];matchedCount:number;totalCount:number;suppressedCount:number;}
export interface DeletedPlaylist {deletionId:string;name:string;trackCount:number;deletedAt:string;}
export interface OfflineBrowseApi {
  queryLibrary(input:LibraryBrowseInput):Promise<LibraryBrowseResult>;
  searchPlaylists(input:{request:string}):Promise<PlaylistSummary[]>;
  comparePlaylists(input:{playlistIds:string[]}):Promise<{comparison:string}>;
  deletePlaylist(input:{playlistId:string}):Promise<{cancelled:true}|{deletionId:string;name:string}>;
  listDeletedPlaylists():Promise<DeletedPlaylist[]>;
  restorePlaylist(input:{deletionId:string}):Promise<PlaylistSummary>;
}
interface ViewHost extends DraftNoticeHost {
  canAct():boolean;canDelete(playlistId:string):boolean;
  perform<T>(label:string,task:()=>Promise<T>,apply:(value:T,currentRoute:boolean)=>void):Promise<void>;
  libraryChanged(tracks:Track[]|null):void;savedChanged():void;deleted(playlistId:string):void;restored(playlist:PlaylistSummary):void;
}
const create=<K extends keyof HTMLElementTagNameMap>(tag:K,text='',id=''):HTMLElementTagNameMap[K]=>{const node=document.createElement(tag);node.textContent=text;if(id)node.id=id;return node;};
/** Provider-independent local tools. Host owns the one-job gate and shared app state. */
export class OfflineBrowseView {
  private cardControls:{select:HTMLInputElement;remove:HTMLButtonElement;id:string}[]=[];
  private recoveryControls:HTMLButtonElement[]=[];
  private controls:(HTMLButtonElement|HTMLInputElement|HTMLSelectElement)[]=[];
  private queryInputs=new Map<string,HTMLInputElement>();
  private request:HTMLInputElement;private sort:HTMLSelectElement;private descending:HTMLInputElement;private duplicates:HTMLInputElement;
  private libraryStatus:HTMLElement;private savedStatus:HTMLElement;private savedRequest:HTMLInputElement;private compareButton:HTMLButtonElement;
  private recovery:HTMLElement;private deletedSets:DeletedPlaylist[]=[];
  private libraryGeneration=0;private savedGeneration=0;private savedFilter:Set<string>|null=null;private selected=new Set<string>();
  private appliedQuery:LibraryQuery={};private appliedSort:string|null=null;private appliedDescending=false;private appliedDuplicates=false;
  get librarySort():{field:string|null;descending:boolean}{return {field:this.appliedSort,descending:this.appliedDescending};}
  private api:OfflineBrowseApi;private host:ViewHost;
  private renderDraftNotice: () => boolean;
  constructor(library:HTMLElement,saved:HTMLElement,api:OfflineBrowseApi,host:ViewHost){
    this.api=api;this.host=host;
    const libraryPanel=create('details');libraryPanel.className='surface prep-form';libraryPanel.append(create('summary','Filtros locales, orden y duplicados'));
    this.request=this.input(libraryPanel,'Describe filtros (sin IA)','offline-library-request');this.request.maxLength=2000;this.request.placeholder='House, BPM 120-128, key 8A, energy 4-7';
    libraryPanel.append(this.button('Interpretar localmente','offline-library-interpret',()=>this.query(true)));
    const grid=create('div');grid.className='stats-grid';
    for(const [field,label] of [['text','Título o artista'],['genre','Género exacto'],['bpm_min','BPM mínimo'],['bpm_max','BPM máximo'],['key','Tonalidad Camelot'],['energy_min','Energía mínima'],['energy_max','Energía máxima']]){
      const holder=create('div');const input=this.input(holder,label,'offline-library-'+field);input.maxLength=200;
      if(field.includes('_')){input.type='number';input.min=field.startsWith('bpm')?'0.01':'1';input.max=field.startsWith('bpm')?'400':'10';input.step=field.startsWith('bpm')?'any':'1';}
      this.queryInputs.set(field,input);grid.append(holder);
    }
    libraryPanel.append(grid);
    const sortLabel=create('label','Ordenar por');sortLabel.setAttribute('for','offline-library-sort');this.sort=create('select','','offline-library-sort');
    for(const [value,label] of [['','Orden del escaneo'],...LIBRARY_COLUMNS]){const option=create('option',label);option.value=value;option.disabled=!value;this.sort.append(option);}this.sort.value='';this.controls.push(this.sort);libraryPanel.append(sortLabel,this.sort);
    this.descending=this.input(libraryPanel,'Orden descendente','offline-library-descending','checkbox');this.duplicates=this.input(libraryPanel,'Ocultar versiones duplicadas','offline-library-duplicates','checkbox');
    libraryPanel.append(this.button('Aplicar filtros','offline-library-apply',()=>this.query(false)),this.button('Quitar filtros locales','offline-library-clear',()=>{this.invalidateLibrary();}));
    this.libraryStatus=create('p','','offline-library-status');this.libraryStatus.setAttribute('aria-live','polite');libraryPanel.append(this.libraryStatus);library.replaceChildren(libraryPanel);
    const savedPanel=create('section');savedPanel.className='surface prep-form';savedPanel.append(create('h3','Buscar y comparar sin conexión'));
    this.savedRequest=this.input(savedPanel,'Nombre, artista, género o límite de pistas/minutos','offline-saved-request');this.savedRequest.maxLength=2000;
    savedPanel.append(this.button('Buscar localmente','offline-saved-search',()=>this.search()),this.button('Mostrar todas','offline-saved-clear',()=>{this.invalidateSaved();}));
    this.compareButton=this.button('Comparar seleccionadas','offline-saved-compare',()=>this.compare());savedPanel.append(this.compareButton);
    this.savedStatus=create('p','','offline-saved-result');this.savedStatus.className='metadata-guidance';this.savedStatus.setAttribute('aria-live','polite');savedPanel.append(this.savedStatus);
    const draftNotice=create('section');this.renderDraftNotice=createDraftNotice(draftNotice,'offline-saved','eliminar una playlist guardada',host);savedPanel.append(draftNotice);
    savedPanel.append(this.button('Ver playlists eliminadas recuperables','offline-saved-recovery',()=>this.loadDeleted()));this.recovery=create('div','','offline-saved-recovery-list');savedPanel.append(this.recovery);saved.replaceChildren(savedPanel);this.sync();
  }
  private input(parent:HTMLElement,label:string,id:string,type='text'):HTMLInputElement{const caption=create('label',label);caption.setAttribute('for',id);const input=create('input','',id);input.type=type;this.controls.push(input);parent.append(caption,input);return input;}
  private button(label:string,id:string,action:()=>void|Promise<void>):HTMLButtonElement{const button=create('button',label,id);button.type='button';button.className='button subtle';button.addEventListener('click',()=>{if(this.host.canAct())void action();});this.controls.push(button);return button;}
  sync():void{this.renderDraftNotice();for(const control of [...this.controls,...this.recoveryControls])control.disabled=!this.host.canAct();for(const item of this.cardControls){item.select.disabled=!this.host.canAct();item.select.checked=this.selected.has(item.id);item.remove.disabled=!this.host.canAct()||!this.host.canDelete(item.id);}this.compareButton.disabled=!this.host.canAct()||this.selected.size<2;}
  beginPlaylistRender(playlists:PlaylistSummary[]):void{this.cardControls=[];const ids=new Set(playlists.map(p=>p.id));for(const id of this.selected)if(!ids.has(id))this.selected.delete(id);} 
  invalidateLibrary():void{this.libraryGeneration++;this.appliedQuery={};this.appliedSort=null;this.appliedDescending=this.appliedDuplicates=false;for(const input of this.queryInputs.values())input.value='';this.request.value='';this.sort.value='';this.descending.checked=this.duplicates.checked=false;this.libraryStatus.textContent='';this.host.libraryChanged(null);}
  invalidateSaved():void{this.savedGeneration++;this.savedFilter=null;this.selected.clear();this.savedRequest.value='';this.savedStatus.textContent='';this.host.savedChanged();this.sync();}
  matches(playlistId:string):boolean{return this.savedFilter===null||this.savedFilter.has(playlistId);}
  async sortLibrary(field:string):Promise<void>{
    if(!this.host.canAct()||!LIBRARY_COLUMNS.some(([key])=>key===field))return;
    const accepted=await this.applyLibraryQuery({query:this.appliedQuery,sortBy:field,descending:this.appliedSort===field?!this.appliedDescending:false,hideDuplicates:this.appliedDuplicates},false);
    if(accepted)document.getElementById?.('library-sort-'+field)?.focus();
  }
  private async query(interpret:boolean):Promise<void>{
    const query:Record<string,string|number>={};for(const [field,input] of this.queryInputs){const value=input.value.trim();if(value)query[field]=field.includes('_')?Number(value):field==='key'?value.toUpperCase():value;}
    await this.applyLibraryQuery({...(interpret?{request:this.request.value.trim()}:{query}),sortBy:this.sort.value||'title',descending:this.descending.checked,hideDuplicates:this.duplicates.checked},true);
  }
  private async applyLibraryQuery(params:LibraryBrowseInput,updateInputs:boolean):Promise<boolean>{
    const generation=++this.libraryGeneration;let accepted=false;
    await this.host.perform('Filtrando biblioteca local…',()=>this.api.queryLibrary(params),(result,current)=>{
      if(!current||generation!==this.libraryGeneration)return;
      accepted=true;this.appliedQuery={};for(const [field,input] of this.queryInputs){const value=result.query[field as keyof LibraryQuery];if(value!==null&&value!==undefined)Object.assign(this.appliedQuery,{[field]:value});if(updateInputs)input.value=String(value??'');}
      this.appliedSort=params.sortBy??'title';this.appliedDescending=params.descending??false;this.appliedDuplicates=params.hideDuplicates??false;
      this.sort.value=this.appliedSort;this.descending.checked=this.appliedDescending;
      this.libraryStatus.textContent=`${result.matchedCount} de ${result.totalCount} pistas · ${result.suppressedCount} duplicados ocultos. ${result.query.interpretation_note??''}`;this.host.libraryChanged(result.tracks);
    });
    this.sort.value=this.appliedSort??'';this.descending.checked=this.appliedDescending;
    return accepted&&generation===this.libraryGeneration;
  }
  private async search():Promise<void>{const generation=++this.savedGeneration;await this.host.perform('Buscando playlists locales…',()=>this.api.searchPlaylists({request:this.savedRequest.value.trim()}),(results,current)=>{if(!current||generation!==this.savedGeneration)return;this.savedFilter=new Set(results.map(p=>p.id));this.savedStatus.textContent=`${results.length} playlists encontradas`;this.host.savedChanged();});}
  private async compare():Promise<void>{if(this.selected.size<2)return;const generation=++this.savedGeneration;await this.host.perform('Comparando evidencia local…',()=>this.api.comparePlaylists({playlistIds:[...this.selected]}),(result,current)=>{if(current&&generation===this.savedGeneration)this.savedStatus.textContent=result.comparison;});}
  addPlaylistActions(card:HTMLElement,playlist:PlaylistSummary):void{
    const holder=create('div');holder.className='playlist-actions';const label=create('label','Seleccionar para comparar');label.setAttribute('for','offline-saved-select-'+playlist.id);const select=create('input','','offline-saved-select-'+playlist.id);select.type='checkbox';select.checked=this.selected.has(playlist.id);select.disabled=!this.host.canAct();select.addEventListener('change',()=>{if(!this.host.canAct())return;if(select.checked&&this.selected.size>=200){select.checked=false;return;}if(select.checked)this.selected.add(playlist.id);else this.selected.delete(playlist.id);this.sync();});
    const remove=create('button','Eliminar con copia recuperable','offline-saved-delete-'+playlist.id);remove.type='button';remove.className='button subtle';remove.disabled=!this.host.canAct()||!this.host.canDelete(playlist.id);remove.setAttribute('aria-label',`Eliminar con copia recuperable: ${playlist.name}`);remove.setAttribute('aria-describedby','offline-saved-draft-message');remove.addEventListener('click',()=>{if(this.host.canAct()&&this.host.canDelete(playlist.id))void this.remove(playlist);});this.cardControls.push({select,remove,id:playlist.id});holder.append(select,label,remove);card.append(holder);
  }
  private async remove(playlist:PlaylistSummary):Promise<void>{await this.host.perform('Confirmando eliminación recuperable…',()=>this.api.deletePlaylist({playlistId:playlist.id}),(result)=>{if('cancelled'in result)return;this.selected.delete(playlist.id);this.savedGeneration++;this.savedStatus.textContent=`${result.name}: eliminada de las playlists activas; disponible para restaurar`;this.deletedSets.unshift({deletionId:result.deletionId,name:result.name,trackCount:playlist.trackCount,deletedAt:''});this.renderDeleted();this.host.deleted(playlist.id);this.sync();});}
  private async loadDeleted():Promise<void>{const generation=++this.savedGeneration;await this.host.perform('Cargando copias recuperables…',()=>this.api.listDeletedPlaylists(),(result,current)=>{if(!current||generation!==this.savedGeneration)return;this.deletedSets=result;this.renderDeleted();});}
  private renderDeleted():void{this.recoveryControls=[];this.recovery.replaceChildren();if(!this.deletedSets.length){this.recovery.append(create('p','No hay playlists eliminadas pendientes de restaurar'));return;}for(const playlist of this.deletedSets){const row=create('div');row.append(create('p',`${playlist.name} · ${playlist.trackCount} pistas`));const restore=create('button','Restaurar','offline-saved-restore-'+playlist.deletionId);restore.type='button';restore.className='button subtle';restore.disabled=!this.host.canAct();restore.addEventListener('click',()=>{if(this.host.canAct())void this.restore(playlist.deletionId);});this.recoveryControls.push(restore);row.append(restore);this.recovery.append(row);}}
  private async restore(deletionId:string):Promise<void>{await this.host.perform('Restaurando playlist local…',()=>this.api.restorePlaylist({deletionId}),(result)=>{this.deletedSets=this.deletedSets.filter(item=>item.deletionId!==deletionId);this.savedGeneration++;this.savedFilter=null;this.renderDeleted();this.savedStatus.textContent=`Playlist restaurada: ${result.name}`;this.host.restored(result);});}
}
